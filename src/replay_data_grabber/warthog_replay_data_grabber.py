import logging

logger = logging.getLogger(__name__)

import traceback
import argparse
from typing import Optional
from pathlib import Path

from src.common.configuration import get_config
from src.common.services import LoggingService, VehicleService
from services import (
    ReplayParserService,
    WtExtCliClientService,
    ReplayManagerService,
)


class WarthogReplayDataGrabber:
    """
    Main class to orchestrate the collection of battle data from War Thunder.
    """

    # Lifecycle

    def __init__(
        self,
        *,
        replay_file_path: Optional[Path] = None,
        replay_dir_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        allow_overwrite=False,
    ):
        # Bootstrapping
        root_config = get_config()
        self._config = root_config.replay_data_grabber_config
        LoggingService(root_config.logging_config)

        # Init the input paths and validate them
        self._replay_file_path = replay_file_path
        self._replay_dir_path = replay_dir_path or self._config.war_thunder_config.replay_dir
        if self._replay_file_path is None and self._replay_dir_path is None:
            raise ValueError(
                f"Neither replay file path: {self._replay_file_path} nor replay directory: {self._replay_dir_path} provided."
            )

        # Init services
        self._vehicle_service = VehicleService(root_config.vehicle_service_config)
        self._wt_ext_cli_client = WtExtCliClientService(self._config.wt_ext_cli_service_config.wt_ext_cli_path)
        self._replay_parser_service = ReplayParserService(self._vehicle_service, self._wt_ext_cli_client)

        self._processed_replay_dir = output_dir or self._config.replay_manager_service_config.processed_replay_dir
        overwrite_existing_replays = allow_overwrite or self._config.overwrite_existing_replays
        self._replay_manager_service = ReplayManagerService(
            self._replay_parser_service,
            raw_replay_directory=self._replay_dir_path,
            processed_replay_directory=self._processed_replay_dir,
            allow_overwrite=overwrite_existing_replays,
        )

    # Methods

    def start_collection(self):
        logger.info(f"Starting Warthog Replay Data Grabber")

        if self._replay_file_path:
            replay = self._replay_manager_service.ingest_raw_replay_file(self._replay_file_path)
            if replay:
                self._replay_manager_service.store_replay(replay)
        elif self._replay_dir_path:
            replay_map = self._replay_manager_service.ingest_raw_replay_files_from_directory(self._replay_dir_path)
            for _, replay in replay_map.items():
                self._replay_manager_service.store_replay(replay)

        logger.info(f"Data collection finished.")

    def stop_collection(self):
        logger.info("Stopping collection process")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="War Thunder Stats Collector")

    parser.add_argument(
        "--replay-file-path",
        "-f",
        type=str,
        help="Path to replay file to be processed (ex: /path/to/replay.wrpl)",
    )

    parser.add_argument(
        "--replay-dir-path",
        "-d",
        type=str,
        help="Path to directory containing replay files to be processed (ex: /path/to/replays/)",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing replay data (default: False)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Path to output directory to store processed replay data",
    )

    return parser.parse_args()


def main():
    """
    Main function to run the Warthog Replay Data Grabber from command line.
    """
    args = parse_arguments()

    # Initialize the main class
    replay_data_grabber = WarthogReplayDataGrabber(
        replay_file_path=Path(args.replay_file_path) if args.replay_file_path else None,
        replay_dir_path=Path(args.replay_dir_path) if args.replay_dir_path else None,
        output_dir=args.output,
        allow_overwrite=args.overwrite,
    )

    try:
        logger.info("Starting Warthog Replay Data Grabber...")
        replay_data_grabber.start_collection()
        logger.info(f"Processing complete.")
        return 0
    except Exception as e:
        logger.error(f"Error processing replay data: {e}")
        logger.error(traceback.format_exc())
        return 1
    finally:
        replay_data_grabber.stop_collection()


if __name__ == "__main__":
    exit(main())
