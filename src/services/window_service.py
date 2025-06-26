import logging

logger = logging.getLogger(__name__)

import os
import sys
import time
from typing import Optional

import psutil
import win32gui
import win32con
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper

from config import get_config
from models import Coordinate
from services import HIDService

WindowRef = UIAWrapper | str


class WindowService:
    """
    Handles basic window operations such as finding, activating,
    and verifying active state of application windows.
    """

    ## Statics

    UIA_BACKEND = "uia"
    WINDOW_CLASS_NAME_CONTAINS_BLOCK_LIST = ["Tray", "Wnd", "Progman"]

    ## Lifecycle

    def __init__(self):
        self._config = get_config()
        self._hid_service = HIDService()

    ## Methods

    def _resolve_window_ref(self, window_ref: WindowRef) -> Optional[UIAWrapper]:
        """
        Resolved a WindowRef to a UIAWrapper instance or None if not found.
        """
        if isinstance(window_ref, UIAWrapper):
            return window_ref
        elif isinstance(window_ref, str):
            desktop = Desktop(backend=self.UIA_BACKEND)
            windows = desktop.windows(title=window_ref)

            if windows:
                window = windows[0]
                logger.info(f"Found window: {window.window_text()}")
                return window

            logger.info(f"Window with title '{window_ref}' not found.")
            return None

    def get_window_center(self, window_ref: WindowRef) -> Coordinate:
        """
        Returns the coordinate of the center of a given window.
        """
        window = self._resolve_window_ref(window_ref)
        if not window:
            raise ValueError("Window reference is invalid or not found.")

        rect = window.rectangle()
        center_x = int(rect.left + rect.width() / 2)
        center_y = int(rect.top + rect.height() / 2)
        return Coordinate(center_x, center_y)

    def _get_current_process_id(self) -> int:
        """
        Get the process ID of the current Python process.
        """
        return os.getpid()

    def _get_pid_hierarchy(self) -> list[int]:
        """
        Get the hierarchy of process IDs starting from current process up to root.
        """
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

    def _get_window_by_pid_chain(self, pids: list[int]) -> Optional[UIAWrapper]:
        """
        Find a window associated with the given list of PIDs (representing the call chain).
        """
        try:
            desktop = Desktop(backend=self.UIA_BACKEND)
            windows = desktop.windows()

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
                            logger.info(
                                f"Found window for PID {pid}: {window.window_text()}"
                            )
                            return window
                except Exception as e:
                    logger.debug(f"Could not find window for PID {pid}: {e}")
                    continue

            logger.warning(f"No window found for PIDs: {pids}")
            return None
        except Exception as e:
            logger.error(f"Error finding window by PID: {e}")
            return None

    def get_current_application_window(self) -> Optional[UIAWrapper]:
        """
        Get the window of the application that's running this script.
        """
        try:
            # Try with parent process hierarchy
            pid_hierarchy = self._get_pid_hierarchy()
            if pid_hierarchy:
                window = self._get_window_by_pid_chain(pid_hierarchy)
                if window:
                    return window

            return None
        except Exception as e:
            logger.error(f"Error getting current application window: {e}")
            return None

    def get_window(self, title: str) -> Optional[UIAWrapper]:
        """
        Find and return a window by its title.
        """
        try:
            return self._resolve_window_ref(title)
        except Exception as e:
            logger.error(f"Error finding window by title '{title}': {e}")
            return None

    def flash_window(
        self,
        window_ref: Optional[WindowRef] = None,
        *,
        count: int = 5,
        rate_ms: int = 500,
    ) -> bool:
        """
        Flash the window's taskbar icon to get the user's attention.
        """
        # Resolve the window reference
        window = None
        if window_ref:
            window = self._resolve_window_ref(window_ref)
            if not window:
                raise ValueError("Window reference is invalid or not found.")

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
            # Get the window handle and prep the flash parameters
            hwnd = window.handle
            flags = win32con.FLASHW_TRAY

            # Flash the window
            logger.debug(f"Flashing window: {window.window_text()} (HWND: {hwnd})")
            win32gui.FlashWindowEx(hwnd, flags, count, rate_ms)
            return True

        except Exception as e:
            logger.error(f"Error flashing window: {e}")
            return False

    def activate_window(self, window_ref: WindowRef) -> bool:
        """
        Bring a window to the foreground.
        """
        try:
            # Resolve the window reference
            window = self._resolve_window_ref(window_ref)
            if not window:
                raise ValueError("Window reference is invalid or not found.")

            # Activate the window
            window.set_focus()

            # Wait for the window to become active
            time.sleep(self._config.delay_config.foreground_delay.random_delay_seconds)

            # Verify window is active
            if not self.is_window_active(window.window_text()):
                logger.info(
                    f"Window not active after activation attempt: {window.window_text()}"
                )
                return False

            # Wait for the window to become active
            time.sleep(self._config.delay_config.foreground_delay.random_delay_seconds)

            logger.info(f"Window activated: {window.window_text()}")
            return True
        except Exception as e:
            logger.error(f"Error activating window: {e}")
            return False

    def is_window_active(self, window_ref: WindowRef) -> bool:
        """
        Check if a window with the given title is currently active.
        """
        try:
            # Resolve the window reference
            window = self._resolve_window_ref(window_ref)
            if not window:
                raise ValueError("Window reference is invalid or not found.")

            return window is not None
        except Exception as e:
            logger.error(f"Error checking if window is active: {e}")
            return False
