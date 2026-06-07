import logging

from git import repo
from git.refs import tag

logger = logging.getLogger(__name__)

import shutil
import json
from datetime import datetime
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

        # Prefer processed replay data when available.
        replays = list(self._replay_manager_service.loaded_replays.values())

        oldest_replay_date = None
        if replays:
            processed_replays = [replay for replay in replays if replay.start_time is not None]
            if processed_replays:
                oldest_replay_date = min(replay.start_time for replay in processed_replays if replay.start_time is not None)

        # If there are no processed replays with start time, fall back to raw replay headers.
        if oldest_replay_date is None:
            raw_replay_files = self._replay_manager_service.discover_raw_replay_files(
                self._replay_manager_service._raw_replay_dir_path
            )
            if not raw_replay_files:
                raise ValueError(
                    "Unable to determine game versions because no raw or processed replay files were available. "
                    "Please add .wrpl files to the replay directory and retry."
                )

            for replay_file in raw_replay_files.keys():
                try:
                    start_time = self._replay_manager_service._replay_parser_service.get_replay_start_time_from_replay_file(
                        replay_file
                    )
                    if oldest_replay_date is None or start_time < oldest_replay_date:
                        oldest_replay_date = start_time
                except Exception as e:
                    logger.debug(f"Skipping raw replay file {replay_file} while determining oldest date: {e}")

        if oldest_replay_date is None:
            raise ValueError(
                "Unable to determine game versions because no replay start times were available. "
                "Please add raw .wrpl replay files to the replay directory and retry."
            )

        if not self._git_repository_client.is_cloned:
            self._git_repository_client.clone_partial(
                sparse_paths=self._vehicle_data_processor.get_datamined_file_paths()
            )

        tags = self._git_repository_client.get_tags_between_datetimes(start=oldest_replay_date, end=datetime.now())
        return [tag.name for tag in tags]

    def run_orchestrator(self):
        # Start from a clean slate
        self._clean_working_directory()

        # Keep track of when each game version was released
        game_version_to_datetime_map: dict[str, datetime] = {}
        previous_game_version_to_datetime_map: dict[str, datetime] = {}
        with open(self._game_version_release_datetimes_file_path, "r") as f:
            try:
                loaded_game_version_to_datetime_map = json.load(f)
                # Convert string datetimes back to datetime objects
                for version, dt_str in loaded_game_version_to_datetime_map.items():
                    previous_game_version_to_datetime_map[version] = datetime.fromisoformat(dt_str)
            except Exception as e:
                logger.warning(f"Could not load existing game version release datetimes: {e}")

        # Process each game version, using stored datamine data when available.
        for version in self.get_game_versions():
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
                        logger.warning(
                            f"Stored datamine data for version {version} is incomplete; cloning fresh data."
                        )

            if local_datamine_path is not None:
                repository_path = local_datamine_path
                previous_game_version_datetime = previous_game_version_to_datetime_map.get(version)
                if previous_game_version_datetime:
                    game_version_to_datetime_map[version] = previous_game_version_datetime
                else:
                    # If the version datetime isn't cached, we need git metadata to fill it.
                    if not self._git_repository_client.is_cloned:
                        self._git_repository_client.clone_partial(
                            sparse_paths=self._vehicle_data_processor.get_datamined_file_paths()
                        )
                    try:
                        self._git_repository_client.checkout_branch(version)
                        game_version_to_datetime_map[version] = self._git_repository_client.get_head_date(utc=True)
                    except Exception as e:
                        logger.warning(
                            f"Could not determine release datetime for version {version} from local datamine data: {e}"
                        )
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

                # Update the version to datetime map
                head_datetime = self._git_repository_client.get_head_date(utc=True)
                game_version_to_datetime_map[version] = head_datetime

            # Process the vehicle data for this version
            self._vehicle_data_processor.process_vehicle_data(
                repository_version=version, repository_path=repository_path
            )

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

            # Persist the release datetime map after each successful version.
            self._save_game_version_release_datetimes(game_version_to_datetime_map)

        # Clean up the working directory
        self._clean_working_directory()

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
        with open(self._game_version_release_datetimes_file_path, "w") as f:
            json.dump(game_version_to_datetime_map, f, indent=4, default=str)
