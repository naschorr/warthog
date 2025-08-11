import logging

logger = logging.getLogger(__name__)

import argparse
from typing import Optional
from pathlib import Path

from configuration import get_config
from services import (
    VehicleService,
    ReplayParserService,
    LoggingService,
    WtExtCliClientService,
    ReplayManagerService,
)


class Warthog:
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
        self._config = get_config()
        LoggingService(self._config.logging_config)

        # Init the input paths and validate them
        self._replay_file_path = replay_file_path
        self._replay_dir_path = replay_dir_path or self._config.war_thunder_config.replay_dir
        if self._replay_file_path is None and self._replay_dir_path is None:
            raise ValueError(
                f"Neither replay file path: {self._replay_file_path} nor replay directory: {self._replay_dir_path} provided."
            )

        # Init wt ext cli client service
        self.wt_ext_cli_client = WtExtCliClientService(self._config.wt_ext_cli_service_config.wt_ext_cli_path)

        # Init the vehicle service
        processed_vehicle_data_dir = self._config.vehicle_service_config.processed_vehicle_data_directory_path
        processed_vehicle_data = list(processed_vehicle_data_dir.glob("*.json"))
        processed_vehicle_data.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        self._vehicle_service = VehicleService(processed_vehicle_data[0])

        # Init the replay parser service
        self.replay_parser_service = ReplayParserService(self._vehicle_service, self.wt_ext_cli_client)

        # Init the replay manager service
        self._processed_replay_dir = output_dir or self._config.replay_manager_service_config.processed_replay_dir
        overwrite_existing_replays = allow_overwrite or self._config.overwrite_existing_replays
        self.replay_manager_service = ReplayManagerService(
            self.replay_parser_service,
            raw_replay_directory=self._replay_dir_path,
            processed_replay_directory=self._processed_replay_dir,
            allow_overwrite=overwrite_existing_replays,
        )

    # Methods

    def start_collection(self):
        """Start the data collection process based on configured mode."""
        print(f"\nWar Thunder Stats Collector")
        print(f"===========================")
        print(f"Starting collection process...\n")

        if self._replay_file_path:
            replay = self.replay_manager_service.ingest_raw_replay_file(self._replay_file_path)
            if replay:
                self.replay_manager_service.store_replay(replay)
        elif self._replay_dir_path:
            replay_map = self.replay_manager_service.ingest_raw_replay_files_from_directory(self._replay_dir_path)
            for _, replay in replay_map.items():
                self.replay_manager_service.store_replay(replay)

        logger.info(f"Data collection finished.")

    def stop_collection(self):
        """Stop the collection process."""
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


def run_collection():
    """Run the collection process."""
    args = parse_arguments()

    # Create warthog instance with CLI options
    warthog = Warthog(
        replay_file_path=Path(args.replay_file_path) if args.replay_file_path else None,
        replay_dir_path=Path(args.replay_dir_path) if args.replay_dir_path else None,
        output_dir=args.output,
        allow_overwrite=args.overwrite,
    )

    try:
        warthog.start_collection()
    except KeyboardInterrupt:
        logger.info("Collection process interrupted by user")
    finally:
        warthog.stop_collection()


if __name__ == "__main__":
    run_collection()
