import logging

logger = logging.getLogger(__name__)

import shutil
import json
from datetime import datetime

from src.common.services import GitService
from src.vehicle_data_grabber.configuration.configuration_models import VehicleDataOrchestratorConfig
from src.vehicle_data_grabber.services import VehicleDataProcessor


class VehicleDataOrchestrator:
    """Orchestrates the process of retrieving and processing vehicle data from the datamine source."""

    def __init__(
        self,
        *,
        config: VehicleDataOrchestratorConfig,
        vehicle_data_processor: VehicleDataProcessor,
        git_service: GitService,
    ):
        self._config = config
        self._vehicle_data_processor = vehicle_data_processor
        self._git_service = git_service

        self._working_directory = self._config.working_directory_path
        if not self._working_directory.exists():
            self._working_directory.mkdir(parents=True, exist_ok=True)

        self._repository_url = str(self._config.repository_url)
        self._game_versions = self._config.game_versions
        self._datamine_data_dir = self._config.datamine_data_directory_path
        self._store_datamine_data = self._config.store_datamine_data
        self._game_version_release_datetimes_file_path = self._config.game_version_release_datetimes_file_path

    def run_orchestrator(self):
        # Start from a clean slate
        self._clean_working_directory()

        # Keep track of when each game version was released
        game_version_to_datetime_map: dict[str, datetime] = {}

        # Clone the repository and process each game version
        # TODO: Load previously stored datamine data if available/clone or checkout if unavailable
        repository_path = self._git_service.clone_repository_partial(
            self._working_directory,
            self._repository_url,
            sparse_paths=self._vehicle_data_processor.get_datamined_file_paths(),
        )
        for version in self._game_versions:
            try:
                self._git_service.checkout_branch(repository_path, version)
            except Exception as e:
                logger.error(f"Error checking out version {version}: {e}")
                continue

            # Update the version to datetime map
            head_datetime = self._git_service.get_head_date(repository_path, utc=True)
            game_version_to_datetime_map[version] = head_datetime

            # Store the datamined data, if configued
            if self._store_datamine_data and self._datamine_data_dir and self._datamine_data_dir.exists():
                for file_path in self._vehicle_data_processor.get_datamined_file_paths():
                    destination_file_path = self._datamine_data_dir / version / file_path.name
                    destination_file_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(repository_path / file_path, destination_file_path)

            # Process (and store) the vehicle data for this version
            self._vehicle_data_processor.process_vehicle_data(
                repository_version=version, repository_path=repository_path
            )

        # Clean up the working directory
        self._clean_working_directory()

        # Store the version to datetime map
        with open(self._game_version_release_datetimes_file_path, "w") as f:
            json.dump(game_version_to_datetime_map, f, indent=4, default=str)

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
