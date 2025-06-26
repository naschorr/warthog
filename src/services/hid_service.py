import logging

logger = logging.getLogger(__name__)

import time
import math

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

from config import get_config, BaseDelayConfig
from models import Coordinate

KeyInput = Key | str


class HIDService:
    """
    Handles Human Interface Device (HID) operations such as mouse movement
    and keyboard input.
    """

    def __init__(self):
        self._config = get_config()
        self._mouse = MouseController()
        self._keyboard = KeyboardController()

    def _delay(self, delay_config: BaseDelayConfig) -> None:
        """Grab a random delay from the provided delay configuration and sleep for that duration."""
        delay_seconds = delay_config.random_delay_seconds
        time.sleep(delay_seconds)

    def get_cursor_position(self) -> Coordinate:
        """
        Returns the current cursor position as a Coordinate object.
        """
        return Coordinate(*self._mouse.position)

    def move_cursor_ease_in_out(
        self, destination: Coordinate, base_delay_seconds: float = 0.001
    ) -> None:
        """
        Smoothly moves the cursor to the destination coordinates using an ease-in-out movement pattern.
        The cursor starts slowly, accelerates in the middle, and slows down as it approaches the destination.

        Args:
            destination: Coordinate object representing the (x, y) coordinates to move to
            base_delay_seconds: Base delay factor, lower values result in faster movement
        """
        # Get current position
        start = self.get_cursor_position()

        # Calculate distance
        distance = int(
            math.sqrt((destination.x - start.x) ** 2 + (destination.y - start.y) ** 2)
        )
        distance = distance // 4

        # Skip if we're close enough to the destination
        if distance < 5:
            return

        # Move the cursor in steps with ease-in-out timing
        for i in range(1, distance + 1):
            # Calculate progress (0.0 to 1.0)
            t = i / distance

            # Calculate intermediate position with ease factor
            intermediate_x = int(start.x + (destination.x - start.x) * t)
            intermediate_y = int(start.y + (destination.y - start.y) * t)

            # Move to the intermediate position
            self._mouse.position = (intermediate_x, intermediate_y)

            # Calculate delay factor using ease-in-out curve
            # This is a basic quadratic curve that takes roughly 2 seconds to complete.
            delay_factor = 12 * math.pow(t - 0.5, 2)  # 0.5 since t is normalized
            time.sleep(delay_factor * base_delay_seconds)

        # Ensure we end up exactly at the destination
        self._mouse.position = destination.to_tuple()

    def click_mouse(self, button=Button.left, *, count=1):
        """
        Click the mouse with specified button.

        Args:
            button: The mouse button to click (default: left)
            count: Number of clicks (default: 1)
        """
        for _ in range(count):
            self._mouse.click(button)
            self._delay(
                self._config.delay_config.key_press_delay
            )  # Reuse the keypress delay for mouse clicks

    def press_key(self, key: KeyInput, *, times: int = 1, dwell_ms: int = 100) -> None:
        """Press and release a key with a random delay."""

        dwell_s = dwell_ms / 1000  # Convert ms to seconds

        if times != 1:
            logger.info(f"Pressing key: '{key}' {times} times")

        try:
            for _ in range(times):
                logger.debug(f"Pressing key: '{key}'")
                self._keyboard.press(key)
                time.sleep(dwell_s)
                self._keyboard.release(key)
                self._delay(self._config.delay_config.key_press_delay)
        except Exception as e:
            logger.error(f"Error pressing key: '{key}', {e}")

    def press_key_combination(
        self, keys: list[KeyInput], *, dwell_ms: int = 100
    ) -> None:
        """
        Press a combination of keys simultaneously (like Ctrl+C).

        Args:
            keys: List of keys to press simultaneously, with the last one being the "action" key
        """
        dwell_s = dwell_ms / 1000  # Convert ms to seconds

        try:
            # Press all modifier keys except the last one
            for key in keys[:-1]:
                self._keyboard.press(key)
                time.sleep(dwell_s)

            # Press and release the last key
            self._keyboard.press(keys[-1])
            time.sleep(dwell_s)
            self._keyboard.release(keys[-1])

            # Release all modifier keys in reverse order
            for key in reversed(keys[:-1]):
                self._keyboard.release(key)

        except Exception as e:
            logger.error(f"Error pressing key combination: {e}")
            # Make sure all keys are released
            for key in keys:
                try:
                    self._keyboard.release(key)
                except:
                    pass
