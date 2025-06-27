import cv2
import numpy as np


def show_image(image: np.ndarray, title: str = "Image") -> None:
    """
    Display an image using OpenCV.
    """
    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
