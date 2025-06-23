import logging

logger = logging.getLogger(__name__)

import time
from typing import Optional

import pygetwindow as gw

from config import get_config
from hid_manager import HIDManager


class WindowManager:
    """
    Handles basic window operations such as finding, activating,
    and verifying active state of application windows.
    """

    def __init__(self):
        self._config = get_config()
        self._hid_manager = HIDManager()

    def get_window_center(self, window: gw.Window) -> tuple[int, int]:
        """
        Returns the center coordinates of the given window.

        Args:
            window: The window to get the center of

        Returns:
            Tuple of (x, y) coordinates of the window center
        """
        center_x = int(window.left + window.width / 2)
        center_y = int(window.top + window.height / 2)
        return (center_x, center_y)

    def find_window_by_title(self, title: str) -> Optional[gw.Window]:
        """Find and return a window by its title."""
        try:
            windows = gw.getWindowsWithTitle(title)
            for window in windows:
                if title in window.title:
                    logger.info(f"Found window: {window.title}")
                    return window

            logger.warning(f"Window not found with title: {title}")
            return None
        except Exception as e:
            logger.error(f"Error finding window: {e}")
            return None

    def activate_window(self, window: gw.Window) -> bool:
        """
        Bring a window to the foreground.

        Args:
            window: The window to activate

        Returns:
            bool: True if activation was successful
        """
        try:
            # Activate the window
            window.maximize()
            window.activate()

            # Wait for the window to become active
            time.sleep(self._config.delay_config.foreground_delay.random_delay_seconds)

            # Verify window is active
            if not self.is_window_active(window.title):
                logger.info(
                    f"Window not active after activation attempt: {window.title}"
                )
                return False

            # Wait for the window to become active
            time.sleep(self._config.delay_config.foreground_delay.random_delay_seconds)

            logger.info(f"Window activated: {window.title}")
            return True
        except Exception as e:
            logger.error(f"Error activating window: {e}")
            return False

    def activate_window_by_title(self, title: str) -> bool:
        """
        Activate a window by its title.

        Args:
            title: The title of the window to activate

        Returns:
            bool: True if activation was successful
        """
        window = self.find_window_by_title(title)
        if window:
            return self.activate_window(window)
        else:
            logger.warning(f"Window with title '{title}' not found.")
            return False

    def is_window_active(self, title: str) -> bool:
        """Check if a window with the given title is currently active."""
        try:
            active_window = gw.getActiveWindow()
            if active_window and title in active_window.title:
                return True
            return False

        except Exception as e:
            logger.error(f"Error checking if window is active: {e}")
            return False
