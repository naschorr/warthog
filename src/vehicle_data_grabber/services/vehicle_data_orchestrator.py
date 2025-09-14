import logging

from git import repo
from git.refs import tag

logger = logging.getLogger(__name__)

import shutil
import json
from datetime import datetime
from pathlib import Path

from src.common.clients import GitRepositoryClient
from src.common.configuration import KwargConfiguration
from src.replay_data_grabber.services.replay_manager_service import ReplayManagerService
from src.vehicle_data_grabber.configuration.configuration_models import VehicleDataOrchestratorConfig
from src.vehicle_data_grabber.services.vehicle_data_processor import VehicleDataProcessor


class VehicleDataOrchestrator(KwargConfiguration[VehicleDataOrchestratorConfig]):
    """Orchestrates the process of retrieving and processing vehicle data from the datamine source."""

    def __init__(
        self,
        config: VehicleDataOrchestratorConfig,
        *,
        vehicle_data_processor: VehicleDataProcessor,
        replay_manager_service: ReplayManagerService,
        **kwargs,
    ):
        super().__init__(config, **kwargs)

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

        # Get oldest replay date, to determine which game versions are to be processed
        filtered_replays = filter(
            lambda replay: replay.start_time is not None, self._replay_manager_service.loaded_replays.values()
        )
        sorted_replays = sorted(
            filtered_replays, key=lambda replay: replay.start_time or datetime.min
        )  ## TODO: update after Replay model is improved
        oldest_replay_date = sorted_replays[0].start_time

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

        # Clone the repository and process each game version
        self._git_repository_client.clone_partial(sparse_paths=self._vehicle_data_processor.get_datamined_file_paths())
        # TODO: Load previously stored datamine data if available/clone or checkout if unavailable
        for version in self.get_game_versions():
            # Skip if data is already stored (and configured to skip it)
            if (
                self._skip_stored_datamine_data
                and self._datamine_data_dir
                and (self._datamine_data_dir / version).exists()
            ):
                previous_game_version_datetime = previous_game_version_to_datetime_map.get(version)
                if previous_game_version_datetime:
                    game_version_to_datetime_map[version] = previous_game_version_datetime
                logger.info(f"Skipping version {version} as datamine data is already stored.")
                continue

            # Clone the repository (if not already cloned)
            repository_path: Path
            if not self._git_repository_client.is_cloned:
                repository = self._git_repository_client.clone_partial(
                    sparse_paths=self._vehicle_data_processor.get_datamined_file_paths()
                )
                repository_path = Path(repository.working_dir)
            else:
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

            # Process (and store) the vehicle data for this version
            self._vehicle_data_processor.process_vehicle_data(
                repository_version=version, repository_path=repository_path
            )

            # Store the datamined data, if configured
            if self._store_datamine_data and self._datamine_data_dir and self._datamine_data_dir.exists():
                for file_path in self._vehicle_data_processor.get_datamined_file_paths():
                    destination_file_path = self._datamine_data_dir / version / file_path.name
                    destination_file_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(repository_path / file_path, destination_file_path)

        # Store the version to datetime map
        with open(self._game_version_release_datetimes_file_path, "w") as f:
            json.dump(game_version_to_datetime_map, f, indent=4, default=str)

        # Clean up the working directory
        self._clean_working_directory()

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
