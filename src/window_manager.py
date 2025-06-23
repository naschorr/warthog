import logging

logger = logging.getLogger(__name__)

import time
import math
from typing import Optional

import pygetwindow as gw
from pynput.mouse import Button, Controller as MouseController

from config import get_config


class WindowManager:
    """
    Handles basic window operations such as finding, activating,
    and verifying active state of application windows.
    """

    def __init__(self):
        self._config = get_config()
        self._mouse = MouseController()

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

    def get_cursor_position(self) -> tuple[int, int]:
        """
        Returns the current cursor position as a tuple of (x, y) coordinates.
        """
        return self._mouse.position

    def move_cursor_ease_in_out(
        self, destination: tuple[int, int], base_delay_seconds: float = 0.001
    ) -> None:
        """
        Smoothly moves the cursor to the destination coordinates using an ease-in-out movement pattern.
        The cursor starts slowly, accelerates in the middle, and slows down as it approaches the destination.

        Args:
            destination: Tuple of (x, y) coordinates to move to
            base_delay_seconds: Base delay factor (will be adjusted by ease curve)
        """
        # Get current position
        start_x, start_y = self._mouse.position
        end_x, end_y = destination

        # Calculate distance
        distance = int(math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2))
        distance = distance // 4

        # Skip if we're close enough to the destination
        if distance < 5:
            return

        # Move the cursor in steps with ease-in-out timing
        for i in range(1, distance + 1):
            # Calculate progress (0.0 to 1.0)
            t = i / distance

            # Calculate intermediate position with ease factor
            intermediate_x = int(start_x + (end_x - start_x) * t)
            intermediate_y = int(start_y + (end_y - start_y) * t)

            # Move to the intermediate position
            self._mouse.position = (intermediate_x, intermediate_y)

            # Calculate delay factor using ease-in-out curve
            delay_factor = 12 * math.pow(t - 0.5, 2)  # 0.5 since t is normalized
            time.sleep(delay_factor * base_delay_seconds)

        # Ensure we end up exactly at the destination
        self._mouse.position = destination

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

            # Smoothly move the cursor to the center of the window using ease-in-out
            logger.info(f"Moving cursor to window center: {window.title}")
            self.move_cursor_ease_in_out(self.get_window_center(window))

            ## todo: hoist click logic into warthunder client
            # Click to ensure focus and select a battle
            logger.info("Clicking to select battle.")
            self._mouse.click(Button.left)

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
