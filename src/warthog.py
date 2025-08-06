import logging

logger = logging.getLogger(__name__)

import argparse
from datetime import datetime
from typing import Optional
from pathlib import Path

import pyperclip
from pywinauto import clipboard

from config import get_config
from enums import BattleType, AppMode
from models.battle_models import Battle
from models.replay_models import Replay
from services import (
    WindowService,
    VehicleService,
    ReplayParserService,
    WarThunderClientService,
    BattleParserService,
    LoggingService,
    WtExtCliClientService,
)


class Warthog:
    """
    Main class to orchestrate the collection of battle data from War Thunder.
    """

    # Statics

    ROOT_DIR = Path(__file__).resolve().parent

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

        # Init services
        self.logging_service = LoggingService(self.config.logging_config)
        self.window_service = WindowService()
        self.wt_client = WarThunderClientService()
        self.wt_ext_cli_client = WtExtCliClientService(self.config.replay_config.wt_ext_cli_path)

        processed_vehicle_data_dir = self.config.vehicle_service_config.processed_vehicle_data_directory_path
        processed_vehicle_data = list(processed_vehicle_data_dir.glob("*.json"))
        processed_vehicle_data.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        self._vehicle_service = VehicleService(processed_vehicle_data[0])

        self.battle_parser_service = BattleParserService(self._vehicle_service)
        self.replay_parser_service = ReplayParserService(self._vehicle_service, self.wt_ext_cli_client)

        # Init the input paths and validate them
        self._data_path = data_path
        self._data_dir_path = data_dir_path
        if self._data_path is None and self._data_dir_path is None:
            raise ValueError(
                f"Neither data path: {self._data_path} nor data directory: {self._data_dir_path} provided."
            )

        # Init the output path and validate it
        output_dir = Path(output_dir) if output_dir else Path(self.config.storage_config.output_dir)
        self.battle_output_dir = output_dir / "battle"
        self.replay_output_dir = output_dir / "replay"
        if not self.battle_output_dir.exists():
            logger.info(f"Output directory {self.battle_output_dir} does not exist. Creating it.")
            self.battle_output_dir.mkdir(parents=True, exist_ok=True)
        if not self.replay_output_dir.exists():
            logger.info(f"Output directory {self.replay_output_dir} does not exist. Creating it.")
            self.replay_output_dir.mkdir(parents=True, exist_ok=True)

        ## Member init
        self._mode = mode
        self._allow_overwrite = allow_overwrite
        self.is_running = False
        self.current_battle = 0
        self.original_clipboard = None
        self.recent_sessions = set()

        self.load_recent_sessions()

    # Methods

    def load_recent_sessions(self):
        """Load recent sessions based on the configured mode."""
        logger.info(f"Loading recent sessions for mode: {self._mode.value}")

        if self._mode == AppMode.BATTLE:
            self._load_recent_battle_data()
        elif self._mode == AppMode.REPLAY:
            self._load_recent_replay_data()

        logger.info(f"Loaded {len(self.recent_sessions)} recent sessions")

    def _load_recent_battle_data(self):
        """Load recent battle data sessions to avoid duplicates."""
        try:
            # Create data directory if it doesn't exist
            self.battle_output_dir.mkdir(parents=True, exist_ok=True)

            # Look for battle data JSON files
            battle_files = list(self.battle_output_dir.glob("*.json"))
            battle_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Load session IDs from recent battle files
            count = 0
            for file_path in battle_files:
                if count >= self.config.battle_config.warthunder_config.max_battle_count:
                    break

                # Extract session ID from filename
                session_id = file_path.stem
                self.recent_sessions.add(session_id)
                count += 1

            logger.debug(f"Loaded {count} recent battle sessions")

        except Exception as e:
            logger.error(f"Error loading recent battle data: {e}")

    def _load_recent_replay_data(self):
        """Load recent replay data sessions to avoid duplicates."""
        try:
            # Create data directory if it doesn't exist
            self.replay_output_dir.mkdir(parents=True, exist_ok=True)

            # Look for JSON files that might be replay-generated
            json_files = list(self.replay_output_dir.glob("*.json"))
            json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            for file_path in json_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        replay = Replay.model_validate_json(f.read())
                        self.recent_sessions.add(replay.session_id)
                except Exception as e:
                    logger.debug(f"Could not parse {file_path} as JSON: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error loading recent replay data: {e}")

    def is_duplicate(self, battle_or_replay: Battle | Replay) -> bool:
        """Check if a battle or replay is a duplicate of one we've already seen."""
        if isinstance(battle_or_replay, Battle):
            return battle_or_replay.session in self.recent_sessions
        elif isinstance(battle_or_replay, Replay):
            return battle_or_replay.session_id in self.recent_sessions

    def get_battle(self) -> Optional[Battle]:
        battle_type: BattleType = self.config.battle_config.warthunder_config.battle_type
        battle_data = ""
        timestamp: Optional[datetime] = None

        # If battle data is provided during construction, use it directly
        if self._data_path:
            logger.info(f"Using provided battle data from {self._data_path}")
            with open(self._data_path, "r", encoding="utf-8") as f:
                battle_data = f.read()

        # Otherwise copy battle data to clipboard
        else:
            battle_data = self.wt_client.copy_battle_data()
            if not battle_data:
                logger.error(f"No battle data copied. Please ensure you are in the Battles tab.")
                return None
            timestamp = self.wt_client.get_battle_timestamp()

        # Parse the battle data
        battle = self.battle_parser_service.parse_battle(battle_data, battle_type=battle_type, timestamp=timestamp)
        if not battle:
            logger.warning(f"Failed to parse battle {self.current_battle}. Skipping.")
            return None

        return battle

    def save_battle(self, battle: Battle) -> Path:
        """Save a battle to the data directory."""
        try:
            file_path = battle.save_to_file(self.battle_output_dir)
            logger.info(f"Saved battle data to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving battle: {e}")
            raise

    def get_replay(self, replay_file_path: Path) -> Optional[Replay]:
        """Parse a replay file and return Replay."""
        if not self.replay_parser_service:
            logger.error("Replay parser not initialized. Check mode configuration.")
            return None

        try:
            logger.info(f"Parsing replay file: {replay_file_path}")
            replay = self.replay_parser_service.parse_replay_file(replay_file_path)
            return replay
        except Exception as e:
            logger.error(f"Error parsing replay file {replay_file_path}: {e}")
            return None

    def process_replay_file(self, replay_file: Path) -> Optional[Replay]:
        """Process a single replay file."""
        replay = self.get_replay(replay_file)
        if replay:
            # Check for duplicates
            if self.is_duplicate(replay):
                if not self._allow_overwrite:
                    logger.info(f"Replay {replay_file.name} is a duplicate (session: {replay.session_id}). Skipping.")
                    return None
                else:
                    logger.info(
                        f"Replay {replay_file.name} is a duplicate (session: {replay.session_id}), but overwriting is allowed."
                    )

            # Save the replay data
            replay.save_to_file(self.replay_output_dir)
            self.recent_sessions.add(replay.session_id)
            return replay

        return None

    def process_replay_files(self, replay_directory: Path) -> int:
        """Process all replay files in a directory."""
        if not replay_directory.exists():
            logger.error(f"Replay directory does not exist: {replay_directory}")
            return 0

        replay_files = list(replay_directory.glob("*.wrpl"))
        if not replay_files:
            logger.warning(f"No replay files found in {replay_directory}")
            return 0

        logger.info(f"Found {len(replay_files)} replay files to process")
        processed_count = 0

        for replay_file in replay_files:
            try:
                replay = self.process_replay_file(replay_file)
                if replay:
                    processed_count += 1
                    logger.info(f"Successfully processed replay: {replay_file.name} (session: {replay.session_id})")

            except Exception as e:
                logger.error(f"Error processing replay file {replay_file}: {e}")
                continue

        logger.info(f"Processed {processed_count} replay files")
        return processed_count

    def start_collection(self):
        """Start the data collection process based on configured mode."""
        logger.info(f"Starting War Thunder data collection (mode: {self._mode.value})")
        print(f"\nWar Thunder Stats Collector")
        print(f"===========================")
        print(f"\nMode: {self._mode.value}")
        print(f"Starting collection process...\n")

        if self._mode == AppMode.BATTLE:
            # Store the original clipboard content to restore it later
            try:
                self.original_clipboard = clipboard.GetData()
                logger.info(
                    f"Saved original clipboard content ({len(self.original_clipboard) if self.original_clipboard else 0} characters)"
                )
            except Exception as e:
                logger.warning(f"Could not save clipboard content: {e}")

            self._start_battle_collection()
        elif self._mode == AppMode.REPLAY:
            self._start_replay_processing()
        else:
            raise ValueError(f"Invalid application mode: {self._mode.value}")

        logger.info(f"Data collection finished.")

    def _start_battle_collection(self):
        """Start battle data collection process."""
        if self._data_path is None:
            # Navigate to the Battles tab
            if not self.wt_client.navigate_to_battles_tab():
                logger.error(f"Failed to navigate to Battles tab. Stopping collection.")
                return

            ## Select the first battle
            if not self.wt_client.select_battle(0):
                logger.error(f"Failed to select the first battle. Stopping collection.")
                return

            max_battle_count = self.config.battle_config.warthunder_config.max_battle_count
        else:
            max_battle_count = 1

        # Start collecting data for each battle
        self.is_running = True
        self.current_battle = 0
        last_battle: Optional[Battle] = None
        while self.is_running and self.current_battle < max_battle_count:
            self.current_battle += 1
            progress = f"({self.current_battle}/{max_battle_count})"
            logger.info(f"Processing battle {progress}")

            try:
                battle = self.get_battle()

                # Check and see if the last battle processed is the same as the current one.
                # This happens when you've reached the last battle in the last and there's not a next one to go to.
                if battle and last_battle and battle == last_battle:
                    logger.info(
                        f"Processed same battle (session: {battle.session}), so the end of the collection process has been reached."
                    )
                    self.is_running = False
                    continue

                if battle:
                    # Check for duplicates from previous sessions
                    if self.is_duplicate(battle):
                        if not self._allow_overwrite:
                            logger.info(
                                f"Battle {self.current_battle} is a duplicate (session: {battle.session}). Skipping."
                            )
                            continue
                        else:
                            logger.info(
                                f"Battle {self.current_battle} is a duplicate (session: {battle.session}), but overwriting is allowed."
                            )

                    # Save the battle and update our list of recent sessions
                    self.save_battle(battle)
                    self.recent_sessions.add(battle.session)
                    last_battle = battle

                    outcome = "Victory" if battle.victory else "Defeat"
                    logger.info(
                        f"Successfully processed battle: '{outcome} in the [{battle.mission_type}] {battle.mission_name} mission' (session: {battle.session})"
                    )
                else:
                    logger.warning(f"Skipping battle {self.current_battle} due to parsing error or duplicate.")

                # Check if we need to go to the next battle
                if self.current_battle < max_battle_count:
                    if not self.wt_client.go_to_next_battle():
                        logger.error(f"Failed to navigate to next battle. Stopping collection.")
                        break

            except Exception as e:
                logger.error(f"Error processing battle {self.current_battle}: {e}")
                # Try to continue with the next battle
                if not self.wt_client.go_to_next_battle():
                    logger.error(f"Failed to navigate to next battle after error. Stopping collection.")
                    break

        logger.info(f"Battle collection completed. Processed {self.current_battle} battles.")

    def _start_replay_processing(self):
        """Start replay file processing."""
        if not self.replay_parser_service:
            logger.error("Replay parser not available. Check configuration.")
            return

        # TODO: Add configuration for replay directory
        replay = self._data_path
        replay_dir = self._data_dir_path
        if not replay_dir and not replay:
            logger.error("No replay file or directory provided for processing.")
            return

        ## Process the replay file(s)
        processed_count = 0
        if replay and replay.exists() and replay.is_file():
            processed_replay = self.process_replay_file(replay)
            if processed_replay:
                processed_count += 1
        if replay_dir and replay_dir.exists() and replay_dir.is_dir():
            processed_count = self.process_replay_files(replay_dir)

        logger.info(f"Replay processing completed. Processed {processed_count} replay files.")

    def stop_collection(self):
        """Stop the collection process."""
        logger.info("Stopping collection process")
        self.is_running = False

        # Restore the original clipboard content if we saved it
        if self.original_clipboard is not None:
            try:
                pyperclip.copy(self.original_clipboard)
                logger.info(f"Restored original clipboard content ({len(self.original_clipboard)} characters)")
            except Exception as e:
                logger.warning(f"Failed to restore clipboard content: {e}")
        else:
            logger.info(f"No original clipboard content to restore")

        # Flash the window in the taskbar to notify the user that the process is complete.
        self.window_service.flash_window()


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
