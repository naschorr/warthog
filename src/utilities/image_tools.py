from uuid import uuid4

import cv2
import numpy as np


def show_image(
    image: np.ndarray,
    *,
    title: str = "Image",
    wait: bool = False,
    x: int = None,
    y: int = None,
) -> None:
    """
    Display an image in a window with optional positioning.

    Args:
        image: The image (numpy array) to display
        title: Title for the window
        wait: If True, wait for a key press before continuing
        x: X coordinate for window position (None for default)
        y: Y coordinate for window position (None for default)
    """
    window_name = f"{title}-{uuid4()}"
    cv2.imshow(window_name, image)

    # Set window position if coordinates are provided
    if x is not None and y is not None:
        cv2.moveWindow(window_name, x, y)

    if wait:
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        cv2.waitKey(1)
