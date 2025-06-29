import logging

logger = logging.getLogger(__name__)

import re
import time
from typing import Optional
from datetime import datetime

from pywinauto import clipboard
from pynput.keyboard import Key

from config import get_config, BaseDelayConfig
from models import Coordinate, OCRResult
from services import WindowService, HIDService, OCRService


class WarThunderClientManager:
    """
    Handles War Thunder specific operations including UI navigation,
    keyboard interactions, and data retrieval via clipboard.
    """

    ## Statics

    BATTLE_TIMESTAMP_TIME_REGEX = re.compile(
        r"(\d{1,2})\s*[\Wi]\s*(\d{2})\s*[\Wi]\s*(\d{2})"
    )
    BATTLE_TIMESTAMP_DATETIME_REGEX = re.compile(
        r"(\w+)\s*(\d{2})\s*[\Wi]\s*(\d{4})\s*(\d{1,2})\s*[\Wi]?\s*(\d{2})\s*[\Wi]?\s*(\d{2})",
        re.IGNORECASE,
    )

    ## Lifecycle

    def __init__(self):
        self._window_service = WindowService()
        self._hid_service = HIDService()
        self._ocr_service = OCRService()
        self._config = get_config()

    ## Methods

    def _delay(self, delay_config: BaseDelayConfig) -> None:
        """Grab a random delay from the provided delay configuration and sleep for that duration."""
        delay_seconds = delay_config.random_delay_seconds
        time.sleep(delay_seconds)

    def navigate_to_battles_tab(self) -> bool:
        """
        Navigate to the Battles tab in the Messages screen.

        Returns:
            bool: True if navigation was successful, False otherwise.
        """
        if not self._window_service.activate_window(
            self._config.warthunder_config.window_title
        ):
            logger.error("Failed to activate game window for navigation")
            return False

        ## Grab a reference to the game window
        window = self._window_service.get_window(
            self._config.warthunder_config.window_title
        )
        if not window:
            logger.error("Game window activated, but then not found")
            return False

        # Smoothly move the cursor to the center of the window using ease-in-out, then click to select the Messages UI.
        logger.info("Moving cursor to window center")
        self._hid_service.move_cursor_ease_in_out(
            self._window_service.get_window_center(window)
        )
        logger.info("Clicking to select Messages interface")
        self._hid_service.click_mouse()

        ## Final bit of wait after the click has gone through to ensure the UI is ready.
        self._delay(self._config.delay_config.foreground_delay)

        try:
            logger.info("Navigating to Battles tab")

            # Press Up Arrow multiple times to ensure we're at the top
            logger.info("Selecting Messages tab row")
            self._hid_service.press_key(
                Key.up,
                times=self._config.warthunder_ui_navigation_config.up_arrow_count,
            )

            # Press Left Arrow multiple times to ensure we're at the leftmost tab
            logger.info("Selecting left-most Messages tab")
            self._hid_service.press_key(
                Key.left,
                times=self._config.warthunder_ui_navigation_config.left_arrow_count,
            )

            # Press Right Arrow once to select the Battles tab (second tab)
            logger.info("Choosing Battles tab")
            self._hid_service.press_key(Key.right)

            # Delay to allow the UI to update
            self._delay(self._config.delay_config.tab_switch_delay)

            # Select the Battles tab
            logger.info("Selecting Battles tab")
            self._hid_service.press_key(Key.space)

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
                self._hid_service.press_key(Key.down)
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
            clipboard.EmptyClipboard()

            # Send Ctrl+C to copy
            logger.info("Copying battle data to clipboard")
            self._hid_service.press_key_combination([Key.ctrl, "c"])

            # Delay to allow the clipboard to be populated
            self._delay(self._config.delay_config.clipboard_delay)

            # Get clipboard contents
            clipboard_data = clipboard.GetData()

            if not clipboard_data:
                logger.warning("No data copied to clipboard")
                return None

            logger.info(f"Successfully copied {len(clipboard_data)} characters")
            return clipboard_data

        except Exception as e:
            logger.error(f"Error copying battle data: {e}")
            return None

    def get_battle_timestamp(self) -> Optional[datetime]:
        """
        Get the timestamp of the currently selected battle.
        """
        window = self._window_service.get_window(
            self._config.warthunder_config.window_title
        )
        if not window:
            raise RuntimeError("Game window not found")

        if not self._window_service.is_window_active(window):
            raise RuntimeError("Game window is not active")

        # Initialize variables
        battle_timestamp: Optional[datetime] = None

        # Build the region to capture
        width, height = self._window_service.get_window_dimensions(window)
        window_center = self._window_service.get_window_center(window)
        screenshot_region = (
            Coordinate(window_center.x, 0),
            Coordinate(width, window_center.y),
        )

        tries = 0
        max_tries = 2  # todo: configure max tries
        while not battle_timestamp and tries < max_tries:
            # Get the screenshot
            screenshot = self._window_service.capture_screenshot(
                window, region=screenshot_region
            )
            if screenshot is None:
                logger.error("Failed to capture screenshot")
                return None

            # OCR the text
            ocr_results = self._ocr_service.extract_text_from_image(screenshot)

            # Filter the OCR results down to candidate timestamps
            filtered_results: list[OCRResult] = []
            for result in ocr_results:
                # Filter results based on regex patterns
                # fmt: off
                if (
                    self.BATTLE_TIMESTAMP_TIME_REGEX.match(result.text) or
                    self.BATTLE_TIMESTAMP_DATETIME_REGEX.match(result.text)
                ):
                    filtered_results.append(result)
                # fmt: on

            # Sort results vertically, with the lowest y-coordinate first
            sorted_results = sorted(
                filtered_results, key=lambda result: result.origin.y, reverse=True
            )

            if sorted_results:
                result = sorted_results[0]  # Take the first result (closest to center)

                # Try to parse the timestamp from the OCR result
                try:
                    datetime_match = self.BATTLE_TIMESTAMP_DATETIME_REGEX.search(
                        result.text
                    )
                    if datetime_match:
                        battle_timestamp = datetime.strptime(
                            f"{datetime_match.group(1)} {datetime_match.group(2)} {datetime_match.group(3)} {datetime_match.group(4)} {datetime_match.group(5)} {datetime_match.group(6)}",
                            "%B %d %Y %H %M %S",
                        )

                    if not battle_timestamp:
                        time_match = self.BATTLE_TIMESTAMP_TIME_REGEX.search(
                            result.text
                        )
                        if time_match:
                            battle_timestamp = datetime.strptime(
                                f"{time_match.group(1)} {time_match.group(2)} {time_match.group(3)}",
                                "%H %M %S",
                            ).replace(
                                year=datetime.now().year,
                                month=datetime.now().month,
                                day=datetime.now().day,
                            )
                except Exception as e:
                    logger.error(f"Failed to parse timestamp: {e}")
                    battle_timestamp = None
                    self._hid_service.scroll_mouse(1)
                    self._delay(self._config.delay_config.battle_select_delay)
                    tries += 1
            else:
                logger.warning(
                    "No valid timestamp found in OCR results, scrolling up to try again"
                )
                self._hid_service.scroll_mouse(1)
                self._delay(self._config.delay_config.battle_select_delay)
                tries += 1

        # Scroll back down to restore the original position
        if tries > 0:
            logger.info(
                f"Restoring original position after {tries} retr{'ies' if tries != 1 else 'y'}"
            )
            self._hid_service.scroll_mouse(tries * -1)

        # Set the timezone to the current system timezone
        if battle_timestamp:
            battle_timestamp.replace(tzinfo=datetime.now().astimezone().tzinfo)

        # Log and return
        if battle_timestamp:
            logger.info(f"Timestamp found: {battle_timestamp}")
        else:
            logger.warning("No valid timestamp found")
        return battle_timestamp

    def go_to_next_battle(self) -> bool:
        """
        Navigate to the next battle in the list.

        Returns:
            bool: True if navigation was successful, False otherwise
        """
        try:
            # Press Down Arrow to go to the next battle
            logger.info("Moving to next battle")
            self._hid_service.press_key(Key.down)

            # Delay to allow the UI to update
            self._delay(self._config.delay_config.battle_select_delay)

            return True

        except Exception as e:
            logger.error(f"Error navigating to next battle: {e}")
            return False
