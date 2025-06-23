import logging

logger = logging.getLogger(__name__)

import time
import random
from typing import Optional

import pyperclip
from pynput.keyboard import Key

from config import get_config, BaseDelayConfig
from window_manager import WindowManager
from hid_manager import HIDManager


class WarThunderClientManager:
    """
    Handles War Thunder specific operations including UI navigation,
    keyboard interactions, and data retrieval via clipboard.
    """

    ## Lifecycle

    def __init__(self):
        self._hid_manager = HIDManager()
        self._window_manager = WindowManager()
        self._config = get_config()

        self._messages_ui_bounds: list[tuple[int, int]] = []

    ## Methods

    def _delay(self, delay_config: BaseDelayConfig) -> None:
        """Grab a random delay from the provided delay configuration and sleep for that duration."""
        delay_seconds = delay_config.random_delay_seconds
        time.sleep(delay_seconds)

    def press_key(self, key: Key | str, *, times: int = 1, dwell_ms: int = 50) -> None:
        """Press and release a key with a random delay using HIDManager."""
        self._hid_manager.press_key(key, times=times, dwell_ms=dwell_ms)

    def _activate_game_window(self) -> bool:
        """Bring the game window to the foreground."""
        window = self._window_manager.find_window_by_title(
            self._config.warthunder_config.window_title
        )
        if window:
            return self._window_manager.activate_window(window)
        return False

    def navigate_to_battles_tab(self) -> bool:
        """
        Navigate to the Battles tab in the Messages screen.

        Returns:
            bool: True if navigation was successful, False otherwise.
        """
        if not self._window_manager.activate_window_by_title(
            self._config.warthunder_config.window_title
        ):
            logger.error("Failed to activate game window for navigation")
            return False

        ## Grab a reference to the game window
        window = self._window_manager.find_window_by_title(
            self._config.warthunder_config.window_title
        )
        if not window:
            logger.error("Game window activated, but then not found.")
            return False

        # Smoothly move the cursor to the center of the window using ease-in-out, then click to select the Messages UI.
        logger.info("Moving cursor to window center.")
        self._hid_manager.move_cursor_ease_in_out(
            self._window_manager.get_window_center(window)
        )
        logger.info("Clicking to select Messages interface.")
        self._hid_manager.click_mouse()

        ## Final bit of wait after the click has gone through to ensure the UI is ready.
        self._delay(self._config.delay_config.foreground_delay)

        try:
            logger.info("Navigating to Battles tab")

            # Press Up Arrow multiple times to ensure we're at the top
            logger.info(
                f"Pressing Up Arrow {self._config.warthunder_ui_navigation_config.up_arrow_count} times"
            )
            self.press_key(
                Key.up,
                times=self._config.warthunder_ui_navigation_config.up_arrow_count,
            )

            # Press Left Arrow multiple times to ensure we're at the leftmost tab
            logger.info(
                f"Pressing Left Arrow {self._config.warthunder_ui_navigation_config.left_arrow_count} times"
            )
            self.press_key(
                Key.left,
                times=self._config.warthunder_ui_navigation_config.left_arrow_count,
            )

            # Press Right Arrow once to select the Battles tab (second tab)
            logger.info("Pressing Right Arrow to select Battles tab")
            self.press_key(Key.right)

            # Delay to allow the UI to update
            self._delay(self._config.delay_config.tab_switch_delay)

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
            for _ in range(
                index + 1
            ):  # +1 because we need to move from the tab to the first battle
                self.press_key(Key.down)
                self._delay(self._config.delay_config.battle_select_delay)

            # Delay to allow the UI to update
            self._delay(self._config.delay_config.battle_select_delay)

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
            self._hid_manager.press_key_combination([Key.ctrl, "c"])

            # Delay to allow the clipboard to be populated
            self._delay(self._config.delay_config.clipboard_delay)

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
            self._delay(self._config.delay_config.battle_select_delay)

            return True

        except Exception as e:
            logger.error(f"Error navigating to next battle: {e}")
            return False
