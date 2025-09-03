import logging

logger = logging.getLogger(__name__)

import argparse
import shutil
from pathlib import Path

from src.replay_data_grabber.services.replay_manager_service import ReplayManagerService
from src.common.factories import ServiceFactory


class WarthogReplayDataCopier:
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
        "--replay-dir-path",
        "-d",
        type=str,
        help="Path to directory containing replay files to be processed (ex: /path/to/replays/)",
    )

    parser.add_argument(
        "--output-dir-path",
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
    service_factory = ServiceFactory()
    replay_manager_service = service_factory.get_replay_manager_service()

    replay_copier = WarthogReplayDataCopier(
        replay_manager_service, output_dir=Path(args.output_dir_path), allow_overwrite=args.overwrite
    )
    replay_copier.copy_replays()


if __name__ == "__main__":
    main()
