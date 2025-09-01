import logging

logger = logging.getLogger(__name__)

import traceback

from src.common.services import LoggingService, GitService
from src.common.configuration import get_config
from src.vehicle_data_grabber.services import VehicleDataOrchestrator, VehicleDataProcessor


class WarthogVehicleDataGrabber:
    """Main class for vehicle data operations."""

    def __init__(self):
        # Bootstrapping
        root_config = get_config()
        self._config = root_config.vehicle_data_grabber_config
        LoggingService(root_config.logging_config)

        # Initialize services
        self._git_service = GitService()
        self._vehicle_data_processor = VehicleDataProcessor(self._config.vehicle_data_processor_config)
        self._vehicle_data_orchestrator = VehicleDataOrchestrator(
            config=self._config.vehicle_data_orchestrator_config,
            vehicle_data_processor=self._vehicle_data_processor,
            git_service=self._git_service,
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
