import logging

logger = logging.getLogger(__name__)

import traceback
import argparse
from typing import Optional
from pathlib import Path

from src.common.factories import ServiceFactory


class WarthogReplayDataGrabber:
    """
    Main class to orchestrate the collection of battle data from War Thunder.
    """

    # Lifecycle

    def __init__(
        self,
        *,
        raw_replay_dir_path: Optional[Path] = None,
        processed_replay_dir_path: Optional[Path] = None,
        allow_overwrite=False,
    ):
        service_factory = ServiceFactory()
        self._replay_manager_service = service_factory.get_replay_manager_service(
            raw_replay_dir=raw_replay_dir_path,
            processed_replay_dir=processed_replay_dir_path,
            allow_overwrite=allow_overwrite,
        )

        self._raw_replay_dir_path = self._replay_manager_service._raw_replay_dir_path

    # Methods

    def start_collection(self):
        logger.info(f"Starting Warthog Replay Data Grabber")

        replay_map = self._replay_manager_service.ingest_raw_replay_files_from_directory(self._raw_replay_dir_path)
        for _, replay in replay_map.items():
            self._replay_manager_service.store_replay(replay)

        logger.info(f"Data collection finished.")

    def stop_collection(self):
        logger.info("Stopping collection process")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="War Thunder Stats Collector")

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
        raw_replay_dir_path=Path(args.replay_dir_path) if args.replay_dir_path else None,
        processed_replay_dir_path=args.output,
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
