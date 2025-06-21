import logging
logger = logging.getLogger(__name__)

import time
import random
from typing import Optional

import pyperclip
from pynput.keyboard import Key, Controller as KeyboardController

from config import get_config, BaseDelayConfig
from window_manager import WindowManager


class WarThunderClientManager:
    """
    Handles War Thunder specific operations including UI navigation,
    keyboard interactions, and data retrieval via clipboard.
    """

    ## Lifecycle

    def __init__(self):
        self.window_manager = WindowManager()
        self.keyboard = KeyboardController()
        self.config = get_config()

    ## Methods

    def _delay(self, delay_config: BaseDelayConfig) -> None:
        """Grab a random delay from the provided delay configuration and sleep for that duration."""
        delay_seconds = delay_config.random_delay_seconds
        time.sleep(delay_seconds)


    def press_key(self, key: Key | str, *, times: int = 1) -> None:
        """Press and release a key with a random delay."""

        if (times == 1):
            logger.info(f"Pressing key: '{key}'")
        else:
            logger.info(f"Pressing key: '{key}' {times} times")

        try:
            for _ in range(times):
                logger.debug(f"Pressing key: '{key}'")
                self.keyboard.press(key)
                self._delay(self.config.delay_config.key_press_delay)
                self.keyboard.release(key)
        except Exception as e:
            logger.error(f"Error pressing key: '{key}', {e}")


    def _activate_game_window(self) -> bool:
        """Bring the game window to the foreground."""
        window = self.window_manager.find_window_by_title(self.config.warthunder_config.window_title)
        if window:
            return self.window_manager.activate_window(window)
        return False


    def navigate_to_battles_tab(self) -> bool:
        """
        Navigate to the Battles tab in the Messages screen.

        Returns:
            bool: True if navigation was successful, False otherwise.
        """
        if not self._activate_game_window():
            logger.error("Failed to activate game window for navigation")
            return False

        try:
            logger.info("Navigating to Battles tab")

            # Press Up Arrow multiple times to ensure we're at the top
            logger.info(f"Pressing Up Arrow {self.config.warthunder_ui_navigation_config.up_arrow_count} times")
            self.press_key(Key.up, times=self.config.warthunder_ui_navigation_config.up_arrow_count)

            # Press Left Arrow multiple times to ensure we're at the leftmost tab
            logger.info(f"Pressing Left Arrow {self.config.warthunder_ui_navigation_config.left_arrow_count} times")
            self.press_key(Key.left, times=self.config.warthunder_ui_navigation_config.left_arrow_count)

            # Press Right Arrow once to select the Battles tab (second tab)
            logger.info("Pressing Right Arrow to select Battles tab")
            self.press_key(Key.right)

            # Delay to allow the UI to update
            self._delay(self.config.delay_config.tab_switch_delay)

            logger.info("Successfully navigated to Battles tab")
            return True

        except Exception as e:
            logger.error(f"Error navigating to Battles tab: {e}")
            return False


    def select_battle(self, index: int = 0) -> bool:
        """
        Select a battle from the list by index (0 = first battle).

        Args:
            index: The index of the battle to select (0-based)

        Returns:
            bool: True if selection was successful, False otherwise
        """
        try:
            # Press Down Arrow the specified number of times
            for _ in range(index + 1):  # +1 because we need to move from the tab to the first battle
                self.press_key(Key.down)
                self._delay(self.config.delay_config.battle_select_delay)

            # Delay to allow the UI to update
            self._delay(self.config.delay_config.battle_select_delay)

            return True

        except Exception as e:
            logger.error(f"Error selecting battle at index {index}: {e}")
            return False


    def copy_battle_data(self) -> Optional[str]:
        """
        Copy the currently selected battle data to clipboard.

        Returns:
            str or None: The battle data string if successful, None otherwise
        """
        try:
            # Clear clipboard before copying
            pyperclip.copy("")

            # Send Ctrl+C to copy
            logger.info("Copying battle data to clipboard")
            with self.keyboard.pressed(Key.ctrl):
                self.press_key("c")

            # Delay to allow the clipboard to be populated
            self._delay(self.config.delay_config.clipboard_delay)

            # Get clipboard contents
            clipboard_data = pyperclip.paste()

            if not clipboard_data:
                logger.warning("No data copied to clipboard")
                return None

            logger.info(f"Successfully copied {len(clipboard_data)} characters")
            return clipboard_data

        except Exception as e:
            logger.error(f"Error copying battle data: {e}")
            return None


    def go_to_next_battle(self) -> bool:
        """
        Navigate to the next battle in the list.

        Returns:
            bool: True if navigation was successful, False otherwise
        """
        try:
            # Press Down Arrow to go to the next battle
            logger.info("Moving to next battle")
            self.press_key(Key.down)

            # Delay to allow the UI to update
            self._delay(self.config.delay_config.battle_select_delay)

            return True

        except Exception as e:
            logger.error(f"Error navigating to next battle: {e}")
            return False
