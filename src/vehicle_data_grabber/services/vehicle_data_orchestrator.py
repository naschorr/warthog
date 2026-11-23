import logging

from git import repo
from git.refs import tag

logger = logging.getLogger(__name__)

import shutil
import json
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

from src.common.clients import GitRepositoryClient
from src.replay_data_grabber.services.replay_manager_service import ReplayManagerService
from src.vehicle_data_grabber.configuration.configuration_models import VehicleDataOrchestratorConfig
from src.vehicle_data_grabber.services.vehicle_data_processor import VehicleDataProcessor


class VehicleDataOrchestrator:
    """Orchestrates the process of retrieving and processing vehicle data from the datamine source."""

    def __init__(
        self,
        config: VehicleDataOrchestratorConfig,
        *,
        vehicle_data_processor: VehicleDataProcessor,
        replay_manager_service: ReplayManagerService,
    ):
        self._config = config

        self._vehicle_data_processor = vehicle_data_processor
        self._replay_manager_service = replay_manager_service

        self._working_directory = self._config.working_directory_path
        self._repository_url = str(self._config.repository_url)
        self._game_versions = self._config.game_versions
        self._datamine_data_dir = self._config.datamine_data_directory_path
        self._store_datamine_data = self._config.store_datamine_data
        self._skip_stored_datamine_data = self._config.skip_stored_datamine_data
        self._game_version_release_datetimes_file_path = self._config.game_version_release_datetimes_file_path

        self._git_repository_client = GitRepositoryClient(
            repository_url=self._repository_url, repository_dir_path=self._working_directory
        )

    # Methods

    def get_game_versions(self) -> list[str]:
        # Use configured game versions if available
        if len(self._game_versions) > 0:
            return self._game_versions

        loaded_replays = self._replay_manager_service.loaded_replays
        replay_start_times = [
            replay.start_time for replay in loaded_replays.values() if replay.start_time is not None
        ]

        raw_replay_files = self._replay_manager_service.discover_raw_replay_files(
            self._replay_manager_service._raw_replay_dir_path
        )
        if not replay_start_times and not raw_replay_files:
            raise ValueError(
                "Unable to determine game versions because no raw or processed replay files were available. "
                "Please add .wrpl files to the replay directory and retry."
            )

        for replay_file, session_id in raw_replay_files.items():
            if session_id in loaded_replays:
                continue

            try:
                replay_start_times.append(
                    self._replay_manager_service._replay_parser_service.get_start_time_from_replay_file(
                        replay_file
                    )
                )
            except Exception as e:
                logger.debug(f"Skipping raw replay file {replay_file} while determining replay dates: {e}")

        if not replay_start_times:
            raise ValueError(
                "Unable to determine game versions because no replay start times were available. "
                "Please check that replay files contain valid start times and retry."
            )

        if not self._git_repository_client.is_cloned:
            self._git_repository_client.clone_partial(
                sparse_paths=self._vehicle_data_processor.get_datamined_file_paths()
            )

        tags_with_release_datetimes = []
        for tag_ref in self._git_repository_client.get_tags():
            try:
                release_datetime = tag_ref.commit.committed_datetime.astimezone(timezone.utc).replace(tzinfo=None)
                tags_with_release_datetimes.append((release_datetime, tag_ref.name))
            except Exception as e:
                logger.debug(f"Could not get commit date for tag {tag_ref.name}: {e}")

        tags_with_release_datetimes.sort(key=lambda tag: (tag[0], tag[1]))
        if not tags_with_release_datetimes:
            logger.warning("No game-version tags were available to cover the loaded replays")
            return []

        tag_release_datetimes = [release_datetime for release_datetime, _ in tags_with_release_datetimes]
        selected_versions = set()
        for replay_start_time in replay_start_times:
            if replay_start_time.tzinfo is not None:
                replay_start_time = replay_start_time.astimezone(timezone.utc).replace(tzinfo=None)

            tag_index = bisect_right(tag_release_datetimes, replay_start_time) - 1
            if tag_index < 0:
                logger.warning(
                    "No game-version tag was released at or before replay time %s",
                    replay_start_time,
                )
                continue
            selected_versions.add(tags_with_release_datetimes[tag_index][1])

        selected_tags = [
            version for _, version in tags_with_release_datetimes if version in selected_versions
        ]
        logger.info(
            "Selected %d of %d game-version tags to cover %d replay dates",
            len(selected_tags),
            len(tags_with_release_datetimes),
            len(replay_start_times),
        )
        return selected_tags

    def run_orchestrator(self):
        game_version_to_datetime_map = self._load_game_version_release_datetimes()

        # Start from a clean slate
        self._clean_working_directory()

        # Process each game version, using stored datamine data when available.
        for version in self.get_game_versions():
            if version in game_version_to_datetime_map:
                logger.info(f"Skipping already processed game version {version}")
                continue

            local_datamine_path = None
            if self._datamine_data_dir:
                candidate_path = self._datamine_data_dir / version
                if candidate_path.exists() and candidate_path.is_dir():
                    if self._skip_stored_datamine_data:
                        logger.info(
                            f"Skipping stored datamine data for version {version} because skip_stored_datamine_data is enabled"
                        )
                    elif self._has_complete_local_datamine_data(candidate_path):
                        local_datamine_path = candidate_path
                        logger.info(f"Using stored datamine data for version {version} from {local_datamine_path}")
                    else:
                        logger.warning(f"Stored datamine data for version {version} is incomplete; cloning fresh data.")

            if local_datamine_path is not None:
                repository_path = local_datamine_path
                if not self._git_repository_client.is_cloned:
                    self._git_repository_client.clone_partial(
                        sparse_paths=self._vehicle_data_processor.get_datamined_file_paths()
                    )
                try:
                    self._git_repository_client.checkout_branch(version)
                except Exception as e:
                    logger.error(f"Error checking out version {version}: {e}")
                    continue
                release_datetime = self._git_repository_client.get_head_date(utc=True)
            else:
                # Clone the repository (if not already cloned)
                if not self._git_repository_client.is_cloned:
                    self._git_repository_client.clone_partial(
                        sparse_paths=self._vehicle_data_processor.get_datamined_file_paths()
                    )

                repository_path = Path(self._git_repository_client.repository.working_dir)

                # Check out the tagged version
                try:
                    self._git_repository_client.checkout_branch(version)
                except Exception as e:
                    logger.error(f"Error checking out version {version}: {e}")
                    continue

                release_datetime = self._git_repository_client.get_head_date(utc=True)

            # Process the vehicle data for this version
            self._vehicle_data_processor.process_vehicle_data(
                repository_version=version, repository_path=repository_path
            )

            game_version_to_datetime_map[version] = release_datetime
            self._save_game_version_release_datetimes(game_version_to_datetime_map)

            # Store the datamined data, if configured and this version came from a clone
            if (
                self._store_datamine_data
                and self._datamine_data_dir
                and self._datamine_data_dir.exists()
                and local_datamine_path is None
            ):
                for file_path in self._vehicle_data_processor.get_datamined_file_paths():
                    destination_file_path = self._datamine_data_dir / version / file_path
                    destination_file_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(repository_path / file_path, destination_file_path)

        # Clean up the working directory
        self._clean_working_directory()

    def _load_game_version_release_datetimes(self) -> dict[str, datetime]:
        with open(self._game_version_release_datetimes_file_path, "r", encoding="utf-8") as file:
            loaded_game_version_to_datetime_map = json.load(file)

        if not isinstance(loaded_game_version_to_datetime_map, dict):
            raise ValueError(
                f"Expected a JSON object in {self._game_version_release_datetimes_file_path}"
            )

        game_version_to_datetime_map = {}
        for version, datetime_string in loaded_game_version_to_datetime_map.items():
            if not isinstance(version, str) or not isinstance(datetime_string, str):
                raise ValueError(f"Invalid release datetime entry for game version {version!r}")
            try:
                game_version_to_datetime_map[version] = datetime.fromisoformat(datetime_string)
            except ValueError as e:
                raise ValueError(
                    f"Invalid release datetime for game version {version}: {datetime_string!r}"
                ) from e

        return game_version_to_datetime_map

    def _has_complete_local_datamine_data(self, local_path: Path) -> bool:
        for file_path in self._vehicle_data_processor.get_datamined_file_paths():
            if not (local_path / file_path).exists():
                return False
        return True

    def _clean_working_directory(self):
        """Cleans the working directory by removing all its contents."""

        if self._working_directory.exists():
            logger.info(f"Cleaning working directory {self._working_directory}")
            try:
                # First try normal removal
                shutil.rmtree(self._working_directory)
            except PermissionError:
                # Fall back to Windows rmdir command which handles read-only files better
                import subprocess

                try:
                    subprocess.run(
                        ["rmdir", "/S", "/Q", str(self._working_directory)],
                        shell=True,
                        check=True,
                        capture_output=True,
                    )
                    logger.info("Used Windows rmdir command for cleanup")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to clean directory with rmdir: {e}")
                    # Try one more time with attrib command to remove read-only attributes
                    try:
                        subprocess.run(
                            ["attrib", "-R", str(self._working_directory / "*"), "/S"],
                            shell=True,
                            capture_output=True,
                        )
                        shutil.rmtree(self._working_directory)
                    except Exception as final_e:
                        logger.error(f"Final cleanup attempt failed: {final_e}")

        # Recreate the directory
        self._working_directory.mkdir(parents=True, exist_ok=True)

    def _save_game_version_release_datetimes(self, game_version_to_datetime_map: dict[str, datetime]) -> None:
        with open(self._game_version_release_datetimes_file_path, "w", encoding="utf-8") as f:
            json.dump(game_version_to_datetime_map, f, indent=4, default=str)
