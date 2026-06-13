import logging

logger = logging.getLogger(__name__)

import traceback
import argparse
from typing import Optional
from pathlib import Path

from src.common.factories import ServiceFactory
from src.replay_data_grabber.models import Replay
from src.replay_data_grabber.models.enums import ProcessingMode


class WarthogReplayDataGrabber:
    """
    Main class to orchestrate the collection of battle data from War Thunder.
    """

    # Lifecycle

    def __init__(
        self,
        *,
        raw_replay_path: Optional[Path] = None,
        raw_replay_dir_path: Optional[Path] = None,
        processed_replay_dir_path: Optional[Path] = None,
        processing_mode: ProcessingMode = ProcessingMode.NEW,
    ):
        service_factory = ServiceFactory()
        service_factory.create_logging_service()
        self._processing_mode = processing_mode
        self._replay_manager_service = service_factory.get_replay_manager_service(
            raw_replay_dir=raw_replay_dir_path,
            processed_replay_dir=processed_replay_dir_path,
            allow_overwrite=processing_mode == ProcessingMode.ALL,
        )

        ## Little bit of mode validation
        if self._processing_mode == ProcessingMode.FILE:
            if raw_replay_path is None:
                raise ValueError("When processing a single file, raw_replay_path must be provided.")
            else:
                self._raw_replay_path = Path(raw_replay_path)

        if self._processing_mode in [ProcessingMode.ALL, ProcessingMode.NEW]:
            if raw_replay_dir_path is None:
                raise ValueError("When processing a directory, raw_replay_dir_path must be provided.")
            else:
                self._raw_replay_dir_path = self._replay_manager_service._raw_replay_dir_path
                self._processed_replay_dir_path = self._replay_manager_service._processed_replay_dir_path

    # Methods

    def start_data_grabbing(self):
        logger.info(f"Starting Warthog Replay Data Grabber")

        if self._processing_mode == ProcessingMode.FILE:
            self.parse_single_replay_file(self._raw_replay_path)
        elif self._processing_mode == ProcessingMode.NEW:
            self.parse_new_replay_files(self._raw_replay_dir_path, self._processed_replay_dir_path)
        elif self._processing_mode == ProcessingMode.ALL:
            self.parse_all_replay_files(self._raw_replay_dir_path)

        logger.info(f"Data collection finished.")

    def _parse_replay_file(self, replay_file_path: Path) -> Replay:
        replay = self._replay_manager_service.parse_raw_replay_file(replay_file_path)
        if replay is None:
            raise ValueError(f"Failed to parse replay file: {replay_file_path}")
        return replay

    def parse_single_replay_file(self, replay_file_path: Path) -> Path:
        """Parse a single .wrpl replay file and write its JSON output.

        Args:
            replay_file_path: Path to the .wrpl file to parse.

        Returns:
            Path of the saved JSON output file.

        Raises:
            FileNotFoundError: If the replay file does not exist.
            ValueError: If the file cannot be parsed.
        """
        logger.info(f"Parsing single replay file: {replay_file_path}")
        replay = self._parse_replay_file(replay_file_path)
        output_path = self._replay_manager_service.store_replay(replay, overwrite=True)
        logger.info(f"Saved parsed replay to: {output_path}")
        return output_path

    def parse_new_replay_files(self, raw_replay_directory: Path, processed_replay_directory: Path):
        """Parse all new .wrpl replay files in the raw replay directory that have not yet been processed.

        Args:
            raw_replay_directory: Directory containing raw .wrpl replay files.
            processed_replay_directory: Directory to check for already processed replays and to save new outputs.

        Returns:
            List of Paths to the saved JSON output files for the newly processed replays.
        """
        logger.info(f"Parsing new replay files from {raw_replay_directory} and saving to {processed_replay_directory}")
        raw_replay_session_map = self._replay_manager_service.discover_raw_replay_files(raw_replay_directory)
        processed_replay_session_map = self._replay_manager_service.discover_processed_replay_files(
            processed_replay_directory
        )
        processed_replay_sessions = set(processed_replay_session_map.values())
        new_replays_session_map = {
            path: session_id
            for path, session_id in raw_replay_session_map.items()
            if session_id not in processed_replay_sessions
        }
        new_replays = set(new_replays_session_map.keys())

        logger.info(f"Found {len(new_replays)} new replay files to process.")
        for replay_file in new_replays:
            try:
                replay = self._parse_replay_file(replay_file)
                self._replay_manager_service.store_replay(replay)
            except Exception as e:
                logger.error(f"Error processing replay file {replay_file}: {e}")
                continue

    def parse_all_replay_files(self, replay_directory: Optional[Path] = None):
        """Parse all .wrpl replay files in the given directory, overwriting any existing processed outputs.

        Args:
            replay_directory: Directory containing raw .wrpl replay files. If None, uses the default raw replay directory.

        Returns:
            List of Paths to the saved JSON output files for all processed replays.
        """
        logger.info(f"Parsing all replay files from {replay_directory} and saving to {self._processed_replay_dir_path}")
        replay_files = self._replay_manager_service.discover_raw_replay_files(replay_directory)
        logger.info(f"Found {len(replay_files)} replay files to process.")
        for replay_file in replay_files:
            try:
                replay = self._parse_replay_file(replay_file)
                self._replay_manager_service.store_replay(replay, overwrite=True)
            except Exception as e:
                logger.error(f"Error processing replay file {replay_file}: {e}")
                continue

    def stop_collection(self):
        logger.info("Stopping collection process")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="War Thunder Replay Data Grabber")

    parser.add_argument(
        "--replay-dir-path",
        "-d",
        type=str.strip,
        help="Path to directory containing replay files to be processed (ex: /path/to/replays/)",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--file",
        "-f",
        type=str.strip,
        help="Path to a single .wrpl replay file to parse and output as JSON",
    )
    mode_group.add_argument(
        "--all",
        action="store_true",
        help="Process all replays in the input directory and overwrite existing processed output.",
    )
    mode_group.add_argument(
        "--new",
        action="store_true",
        help="Process only new replays that are not yet stored in the output directory.",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str.strip,
        help="Path to output directory to store processed replay data",
    )

    return parser.parse_args()


def main():
    """
    Main function to run the Warthog Replay Data Grabber from command line.
    """
    args = parse_arguments()

    if args.file:
        raw_replay_dir_path = Path(args.replay_dir_path) if args.replay_dir_path else Path(args.file).parent
    else:
        if not args.replay_dir_path:
            raise SystemExit("When processing a replay directory, --replay-dir-path is required.")
        if not (args.all or args.new):
            raise SystemExit("Either --all or --new must be specified when processing a replay directory.")
        raw_replay_dir_path = Path(args.replay_dir_path)

    # Initialize the main class
    processing_mode = ProcessingMode.FILE if args.file else ProcessingMode.ALL if args.all else ProcessingMode.NEW
    replay_data_grabber = WarthogReplayDataGrabber(
        raw_replay_path=Path(args.file) if args.file else None,
        raw_replay_dir_path=raw_replay_dir_path,
        processed_replay_dir_path=args.output,
        processing_mode=processing_mode,
    )

    try:
        logger.info("Starting Warthog Replay Data Grabber...")
        replay_data_grabber.start_data_grabbing()
        logger.info(f"Processing complete.")
        return 0
    except Exception as e:
        logger.error(f"Error processing replay data: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())
