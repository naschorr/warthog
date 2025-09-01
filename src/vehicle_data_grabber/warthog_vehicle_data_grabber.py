import logging

logger = logging.getLogger(__name__)

import traceback

from src.common.services import LoggingService, GitService, VehicleService
from src.common.configuration import get_config
from src.replay_data_grabber.services.replay_manager_service import ReplayManagerService
from src.replay_data_grabber.services.replay_parser_service import ReplayParserService
from src.replay_data_grabber.services.wt_ext_cli_client_service import WtExtCliClientService
from src.vehicle_data_grabber.services import VehicleDataOrchestrator, VehicleDataProcessor


class WarthogVehicleDataGrabber:
    """Main class for vehicle data operations."""

    def __init__(self):
        # Bootstrapping
        root_config = get_config()
        self._config = root_config.vehicle_data_grabber_config
        LoggingService(root_config.logging_config)

        # Initialize services
        vehicle_service = VehicleService(root_config.vehicle_service_config)
        wt_ext_cli_client = WtExtCliClientService(
            root_config.replay_data_grabber_config.wt_ext_cli_service_config.wt_ext_cli_path
        )
        replay_parser_service = ReplayParserService(vehicle_service, wt_ext_cli_client)
        replay_manager_service = ReplayManagerService(
            replay_parser_service,
            raw_replay_directory=root_config.replay_data_grabber_config.war_thunder_config.replay_dir,
            processed_replay_directory=root_config.replay_data_grabber_config.replay_manager_service_config.processed_replay_dir,
            allow_overwrite=False,
        )
        git_service = GitService()
        self._vehicle_data_processor = VehicleDataProcessor(self._config.vehicle_data_processor_config)
        self._vehicle_data_orchestrator = VehicleDataOrchestrator(
            config=self._config.vehicle_data_orchestrator_config,
            vehicle_data_processor=self._vehicle_data_processor,
            replay_manager_service=replay_manager_service,
            git_service=git_service,
        )

    def start_collection(self):
        """Start the vehicle data collection process."""
        self._vehicle_data_orchestrator.run_orchestrator()


def main():
    """
    Main function to run the Warthog Vehicle Data Grabber from command line.
    """

    try:
        logger.info("Starting Warthog Vehicle Data Grabber...")
        vehicle_data_grabber = WarthogVehicleDataGrabber()
        vehicle_data_grabber.start_collection()
        logger.info(f"Processing complete.")
        return 0
    except Exception as e:
        logger.error(f"Error processing vehicle data: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
