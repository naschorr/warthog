import logging

logger = logging.getLogger(__name__)

import traceback

from src.common.factories import ServiceFactory


class WarthogVehicleDataGrabber:
    """Main class for vehicle data operations."""

    def __init__(self):
        service_factory = ServiceFactory()
        self._vehicle_data_orchestrator = service_factory.get_vehicle_data_orchestrator()

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
