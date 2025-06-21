import logging
logger = logging.getLogger(__name__)

import argparse
from typing import Optional
from pathlib import Path

import colorama
from colorama import Fore, Style

from src.config import get_config
from models import Battle
from battle_parser import BattleParser
from warthunder_client import WarThunderClientManager

# Initialize colorama
colorama.init()


class Warthog:
    """
    Main class to orchestrate the collection of battle data from War Thunder.
    """

    def __init__(self, *,
            battle_data_path: Optional[Path]=None,
            output_dir: Optional[Path]=None,
            allow_overwrite=False
    ):
        self.wt_client = WarThunderClientManager()
        self.parser = BattleParser()
        self.config = get_config()
        self.battle_data_path = battle_data_path
        self.data_dir = Path(output_dir) if output_dir else Path(self.config.storage_config.data_dir)
        self.allow_overwrite = allow_overwrite
        self.is_running = False
        self.current_battle = 0
        self.skip_current = False
        self.recent_sessions = set()
        self.load_recent_sessions()
        self.setup_logging()


    def setup_logging(self):
        """Configure logging based on config settings."""
        log_level = getattr(logging, self.config.logging_config.console_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )


    def load_recent_sessions(self):
        """Load the most recent battle sessions to avoid duplicates."""
        try:
            # Create data directory if it doesn't exist
            self.data_dir.mkdir(parents=True, exist_ok=True)

            data_files = list(self.data_dir.glob('*.json'))
            # Sort by modification time (most recent first)
            data_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Load the session IDs from the most recent files
            count = 0
            for file_path in data_files:
                if count >= self.config.warthunder_ui_navigation_config.battle_count:
                    break

                # Extract session ID from filename
                session_id = file_path.stem
                self.recent_sessions.add(session_id)
                count += 1

            logger.info(f"Loaded {len(self.recent_sessions)} recent battle sessions")

        except Exception as e:
            logger.error(f"Error loading recent sessions: {e}")


    def is_duplicate(self, battle: Battle) -> bool:
        """Check if a battle is a duplicate of one we've already seen."""
        return battle.session in self.recent_sessions and not self.allow_overwrite


    def process_battle(self, battle_data: str = ""):
        """Process a single battle."""
        # Display progress
        self.current_battle += 1
        progress = f"({self.current_battle}/{self.config.warthunder_ui_navigation_config.battle_count})"
        logger.info(f"{Fore.CYAN}Processing battle {progress}{Style.RESET_ALL}")

        # Check if we should skip this battle
        if self.skip_current:
            logger.info(f"{Fore.YELLOW}Skipping battle {self.current_battle}{Style.RESET_ALL}")
            self.skip_current = False
            return

        # Parse the battle data
        battle = self.parser.parse_battle(battle_data)
        if not battle:
            logger.warning(f"{Fore.YELLOW}Failed to parse battle {self.current_battle}. Skipping.{Style.RESET_ALL}")
            return

        # Check for duplicates
        if self.is_duplicate(battle):
            logger.info(f"{Fore.YELLOW}Battle {self.current_battle} is a duplicate (session: {battle.session}). Skipping.{Style.RESET_ALL}")
            return

        # Save the battle and update our list of recent sessions
        self.save_battle(battle)
        self.recent_sessions.add(battle.session)

        # Log success
        outcome = "Victory" if battle.victory else "Defeat"
        logger.info(f"{Fore.GREEN}Successfully processed battle {self.current_battle}: {outcome} on {battle.mission_name}{Style.RESET_ALL}")


    def get_battle_data(self) -> str:
        battle_data = ""

        # If battle data is provided during construction, use it directly
        if (self.battle_data_path):
            logger.info(f"{Fore.GREEN}Using provided battle data from {self.battle_data_path}{Style.RESET_ALL}")
            with open(self.battle_data_path, 'r', encoding='utf-8') as f:
                battle_data = f.read()

        # Otherwise copy battle data to clipboard
        else:
            battle_data = self.wt_client.copy_battle_data()
            if not battle_data:
                logger.error(f"{Fore.RED}No battle data copied. Please ensure you are in the Battles tab.{Style.RESET_ALL}")
                battle_data = ""

        return battle_data


    def save_battle(self, battle: Battle) -> Path:
        """Save a battle to the data directory."""
        try:
            file_path = battle.save_to_file(self.data_dir)
            logger.info(f"Saved battle data to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error saving battle: {e}")
            raise


    def start_collection(self):
        """Start the battle data collection process."""
        logger.info(f"{Fore.GREEN}Starting War Thunder battle data collection{Style.RESET_ALL}")
        print(f"\nWar Thunder Stats Collector")
        print(f"===========================")
        print(f"\nStarting collection process...\n")

        self.is_running = True

        if (self.battle_data_path is None):
            # Navigate to the Battles tab
            if not self.wt_client.navigate_to_battles_tab():
                logger.error(f"{Fore.RED}Failed to navigate to Battles tab. Stopping collection.{Style.RESET_ALL}")
                return

            ## Select the first battle
            if not self.wt_client.select_battle(0):
                logger.error(f"{Fore.RED}Failed to select the first battle. Stopping collection.{Style.RESET_ALL}")
                return

            battle_count = self.config.warthunder_ui_navigation_config.battle_count

        else:
            battle_count = 1

        # Start collecting data for each battle
        self.current_battle = 0
        while self.is_running and self.current_battle < battle_count:
            try:
                battle_data = self.get_battle_data()
                self.process_battle(battle_data)

                # Check if we need to go to the next battle
                if self.current_battle < battle_count:
                    if not self.wt_client.go_to_next_battle():
                        logger.error(f"{Fore.RED}Failed to navigate to next battle. Stopping collection.{Style.RESET_ALL}")
                        break

            except Exception as e:
                logger.error(f"{Fore.RED}Error processing battle {self.current_battle + 1}: {e}{Style.RESET_ALL}")
                # Try to continue with the next battle
                if not self.wt_client.go_to_next_battle():
                    logger.error(f"{Fore.RED}Failed to navigate to next battle after error. Stopping collection.{Style.RESET_ALL}")
                    break

        logger.info(f"{Fore.GREEN}Collection completed. Processed {self.current_battle} battles.{Style.RESET_ALL}")


    def stop_collection(self):
        """Stop the collection process."""
        self.is_running = False
        logger.info("Stopping collection process")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="War Thunder Stats Collector")

    parser.add_argument(
        "--battle_data_path", "-d",
        type=str,
        help="Path to War Thunder battle data text file for processing without going through the game"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing battle data (default: False)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Path to output directory to store processed JSON battle data"
    )

    return parser.parse_args()


def run_collection():
    """Run the battle collection process."""
    args = parse_arguments()

    # Create warthog instance with CLI options
    warthog = Warthog(
        battle_data_path=Path(args.battle_data_path) if args.battle_data_path else None,
        output_dir=args.output,
        allow_overwrite=args.overwrite
    )

    try:
        warthog.start_collection()
    except KeyboardInterrupt:
        logger.info("Collection process interrupted by user")
    finally:
        warthog.stop_collection()
        colorama.deinit()


if __name__ == "__main__":
    run_collection()