import logging

logger = logging.getLogger(__name__)

import argparse
import shutil
from pathlib import Path

from config import get_config
from services.logging_service import LoggingService
from services.replay_parser_service import ReplayParserService
from services.replay_manager_service import ReplayManagerService
from services.vehicle_service import VehicleService
from services.wt_ext_cli_client_service import WtExtCliClientService


class WarthunderReplayCopier:
    """
    Class to handle copying War Thunder replay files into a specified output directory.

    Handy to store raw data for later processing, or building up a history to regenerate Replay objects if the schema
    needs to change.
    """

    # Lifecycle

    def __init__(
        self, replay_manager_service: ReplayManagerService, *, output_dir: Path, allow_overwrite: bool = False
    ):
        self._replay_manager_service = replay_manager_service
        self._output_dir = output_dir
        self._allow_overwrite = allow_overwrite

        if not self._output_dir.exists():
            logger.info(f"Output directory {self._output_dir} does not exist. Creating it.")
            self._output_dir.mkdir(parents=True, exist_ok=True)

    # Methods

    def copy_replays(self):
        """
        Discovers all replay files, and copies them to the output directory.
        """

        replay_files = self._replay_manager_service.discover_raw_replay_files()

        duplicate_files = []
        copied_files = []
        for replay_file in replay_files:
            destination_path = self._output_dir / replay_file.name

            if destination_path.exists() and not self._allow_overwrite:
                duplicate_files.append(replay_file.name)
                continue

            try:
                shutil.copy2(replay_file, destination_path)
                copied_files.append(replay_file.name)
                logger.info(f"Copied {replay_file.name} to {destination_path}")
            except OSError as e:
                logger.error(f"Failed to copy {replay_file} to {destination_path}: {e}")

        logger.info(f"Copied {len(copied_files)} replay files to {self._output_dir}")
        if duplicate_files:
            logger.info(f"Skipped {len(duplicate_files)} duplicate replay files.")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="War Thunder Replay File Copier")

    parser.add_argument(
        "--replay_dir",
        "-r",
        type=str,
        required=True,
        help="Path to the directory containing War Thunder replay files (.wrpl)",
    )

    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        required=True,
        help="Path to the output directory for copied replay files",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing replay files (default: False)",
    )

    return parser.parse_args()


def main():
    """Run the replay copy process."""
    args = parse_arguments()
    config = get_config()
    LoggingService(config.logging_config)

    warthunder_replay_dir = Path(args.replay_dir)
    processed_replay_dir = Path(config.storage_config.output_dir) / "replay"
    copied_replay_dir = Path(args.output_dir)

    processed_vehicle_data_dir = config.vehicle_service_config.processed_vehicle_data_directory_path
    processed_vehicle_data = list(processed_vehicle_data_dir.glob("*.json"))
    processed_vehicle_data.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    vehicle_service = VehicleService(processed_vehicle_data[0])

    wt_ext_cli_client = WtExtCliClientService(config.replay_config.wt_ext_cli_path if config.replay_config else None)
    replay_parser_service = ReplayParserService(vehicle_service, wt_ext_cli_client)
    replay_manager_service = ReplayManagerService(
        replay_parser_service,
        raw_replay_directory=warthunder_replay_dir,
        processed_replay_directory=processed_replay_dir,
        allow_overwrite=args.overwrite,
    )

    replay_copier = WarthunderReplayCopier(
        replay_manager_service, output_dir=copied_replay_dir, allow_overwrite=args.overwrite
    )
    replay_copier.copy_replays()


if __name__ == "__main__":
    main()
