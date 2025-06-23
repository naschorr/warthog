import logging

logger = logging.getLogger(__name__)

import sys
import time
import os
import psutil
from typing import Optional

import win32gui
import win32con
import pygetwindow as gw
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper


from config import get_config
from hid_manager import HIDManager


class WindowManager:
    """
    Handles basic window operations such as finding, activating,
    and verifying active state of application windows.
    """

    ## Statics

    WINDOW_CLASS_NAME_CONTAINS_BLOCK_LIST = ["Tray", "Wnd", "Progman"]

    ## Lifecycle

    def __init__(self):
        self._config = get_config()
        self._hid_manager = HIDManager()

    ## Methods

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

    def _get_current_process_id(self) -> int:
        """Get the process ID of the current Python process."""
        return os.getpid()

    def _get_pid_hierarchy(self) -> list[int]:
        """Get the hierarchy of process IDs starting from current process up to root."""
        try:
            current_process = psutil.Process(self._get_current_process_id())
            pid_hierarchy = [current_process.pid, current_process.ppid()]

            parent_exists = True
            while parent_exists:
                try:
                    process = psutil.Process(pid_hierarchy[-1])
                    parent = process.ppid()
                    pid_hierarchy.append(parent)
                except psutil.NoSuchProcess:
                    parent_exists = False

            return pid_hierarchy
        except Exception as e:
            logger.error(f"Error getting parent process ID: {e}")
            return []

    def find_window_by_process_ids(self, pids: list[int]) -> Optional[gw.Window]:
        """Find a window associated with the given process IDs using pywinauto."""
        try:
            windows: list[UIAWrapper] = Desktop(backend="uia").windows()

            # Start with oldest processes (parent processes first)
            for pid in reversed(pids):
                try:
                    # Look at all the windows on the desktop
                    for window in windows:
                        ## Does the window's PID match up with the one we're looking for, and is the window's class valid?
                        if window.process_id() == pid and not any(
                            block in window.class_name()
                            for block in self.WINDOW_CLASS_NAME_CONTAINS_BLOCK_LIST
                        ):
                            # Convert to pygetwindow Window object
                            gw_window = gw.Window(hWnd=window.handle)
                            logger.info(
                                f"Found window for PID {pid}: {gw_window.title}"
                            )
                            return gw_window
                except Exception as e:
                    logger.debug(f"Could not find window for PID {pid}: {e}")
                    continue

            logger.warning(f"No window found for PIDs: {pids}")
            return None
        except Exception as e:
            logger.error(f"Error finding window by process ID: {e}")
            return None

    def get_current_application_window(self) -> Optional[gw.Window]:
        """Get the window of the application that's running this script."""
        try:
            # Try with parent process hierarchy
            pid_hierarchy = self._get_pid_hierarchy()
            if pid_hierarchy:
                window = self.find_window_by_process_ids(pid_hierarchy)
                if window:
                    return window

            return None
        except Exception as e:
            logger.error(f"Error getting current application window: {e}")
            return None

    def find_window_by_title(self, title: str) -> Optional[gw.Window]:
        """Find and return a window by its title using pywinauto."""
        try:
            # Use pywinauto to find windows by title
            desktop = Desktop(backend="win32")
            windows = desktop.windows(title=title)

            if windows:
                pywinauto_window = windows[0]
                hwnd = pywinauto_window.handle

                # Convert to pygetwindow Window object for compatibility
                for window in gw.getAllWindows():
                    if window._hWnd == hwnd:
                        logger.info(f"Found window: {pywinauto_window.window_text()}")
                        return window

            logger.warning(f"Window not found with title: {title}")
            return None
        except Exception as e:
            logger.error(f"Error finding window: {e}")
            return None

    def flash_window(
        self, window: Optional[gw.Window] = None, *, count: int = 5, rate_ms: int = 500
    ):
        """
        Flash the window's taskbar icon to get the user's attention.

        Args:
            window: The window to flash
            count: Number of times to flash the window (default: 5)
            rate_ms: Flash rate in milliseconds (default: 500ms)

        Returns:
            bool: True if the flash operation was initiated successfully
        """
        # Ensure we're on Windows
        if "win" not in sys.platform:
            logger.warning("Taskbar flashing is only supported on Windows")
            return False

        # If no window is provided, try to get the window for this program
        if window is None:
            window = self.get_current_application_window()
            if not window:
                logger.warning("Could not find current application window to flash")
                return False

        try:
            # Get the window handle from pygetwindow and prep the flash parameters
            hwnd = window._hWnd
            flags = win32con.FLASHW_TRAY

            # Flash the window
            logger.debug(f"Flashing window: {window.title} (HWND: {hwnd})")
            win32gui.FlashWindowEx(hwnd, flags, count, rate_ms)
            return True

        except Exception as e:
            logger.error(f"Error flashing window: {e}")
            return False

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
