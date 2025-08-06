import logging

logger = logging.getLogger(__name__)

import argparse
from typing import Optional
from pathlib import Path

from config import get_config
from enums import AppMode
from services import (
    WindowService,
    VehicleService,
    ReplayParserService,
    WarThunderClientService,
    BattleParserService,
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
        data_path: Optional[Path] = None,
        data_dir_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        allow_overwrite=False,
        mode: AppMode,
    ):
        self.config = get_config()
        self.logging_service = LoggingService(self.config.logging_config)

        # Init the input paths and validate them
        self._data_path = data_path
        self._data_dir_path = data_dir_path
        if self._data_path is None and self._data_dir_path is None:
            raise ValueError(
                f"Neither data path: {self._data_path} nor data directory: {self._data_dir_path} provided."
            )

        # Init the output path and validate it
        output_dir = Path(output_dir) if output_dir else Path(self.config.storage_config.output_dir)
        self.replay_output_dir = output_dir / "replay"
        if not self.replay_output_dir.exists():
            logger.info(f"Output directory {self.replay_output_dir} does not exist. Creating it.")
            self.replay_output_dir.mkdir(parents=True, exist_ok=True)

        ## Member init
        self._mode = mode
        self._allow_overwrite = allow_overwrite

        # Init services
        self.window_service = WindowService()
        self.wt_client = WarThunderClientService()
        self.wt_ext_cli_client = WtExtCliClientService(self.config.replay_config.wt_ext_cli_path)

        processed_vehicle_data_dir = self.config.vehicle_service_config.processed_vehicle_data_directory_path
        processed_vehicle_data = list(processed_vehicle_data_dir.glob("*.json"))
        processed_vehicle_data.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        self._vehicle_service = VehicleService(processed_vehicle_data[0])

        self.battle_parser_service = BattleParserService(self._vehicle_service)
        self.replay_parser_service = ReplayParserService(self._vehicle_service, self.wt_ext_cli_client)
        self.replay_manager_service = ReplayManagerService(
            self.replay_parser_service,
            self.replay_output_dir,
            allow_overwrite=allow_overwrite,
        )

    # Methods

    def start_collection(self):
        """Start the data collection process based on configured mode."""
        print(f"\nWar Thunder Stats Collector")
        print(f"===========================")
        print(f"Starting collection process...\n")

        if self._data_dir_path:
            replay_map = self.replay_manager_service.ingest_replay_files_from_directory(self._data_dir_path)
            for _, replay in replay_map.items():
                self.replay_manager_service.store_replay(replay)
        elif self._data_path:
            replay = self.replay_manager_service.ingest_replay_file(self._data_path)
            if replay:
                self.replay_manager_service.store_replay(replay)

        logger.info(f"Data collection finished.")

    def stop_collection(self):
        """Stop the collection process."""
        logger.info("Stopping collection process")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="War Thunder Stats Collector")

    parser.add_argument(
        "--data_path",
        "-f",
        type=str,
        help="Path to data file for processing (ex: pre-existing battle data text file, or replay .wrpl file)",
    )

    parser.add_argument(
        "--data_dir_path",
        "-d",
        type=str,
        help="Path to data directory for processing (ex: pre-existing battle data text files, or replay .wrpl files)",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing battle data (default: False)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Path to output directory to store processed JSON battle data",
    )

    parser.add_argument(
        "--mode",
        "-m",
        type=str.lower,
        choices=list(map(lambda x: x.value, AppMode._member_map_.values())),
        help="Collection mode: battle (collect battle data), replay (parse replay files), or both",
    )

    return parser.parse_args()


def run_collection():
    """Run the collection process."""
    args = parse_arguments()
    config = get_config()

    # Create warthog instance with CLI options
    warthog = Warthog(
        data_path=Path(args.data_path) if args.data_path else None,
        data_dir_path=Path(args.data_dir_path) if args.data_dir_path else None,
        output_dir=args.output,
        allow_overwrite=args.overwrite,
        mode=AppMode(args.mode) if args.mode else config.battle_config.warthunder_config.mode,
    )

    try:
        warthog.start_collection()
    except KeyboardInterrupt:
        logger.info("Collection process interrupted by user")
    finally:
        warthog.stop_collection()


if __name__ == "__main__":
    run_collection()
