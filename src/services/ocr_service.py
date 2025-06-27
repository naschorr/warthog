import logging

from src.models.coordinate import Coordinate
from src.models.ocr_result import OCRResult

logger = logging.getLogger(__name__)

import cv2
import easyocr
import numpy as np

from config import get_config
from services import WindowService


class OCRService:
    """
    Handles OCR (Optical Character Recognition) operations
    """

    ## Lifecycle

    def __init__(self):
        self._config = get_config()
        self._window_service = WindowService()

        # Initialize EasyOCR reader
        self._reader = None
        self._languages = ["en"]  # todo: config

        try:
            logger.info(f"Initializing EasyOCR with languages: {self._languages}")
            self._reader = easyocr.Reader(self._languages)  ## todo: configure GPU
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")

    ## Methods

    def extract_text_from_image(
        self,
        image: np.ndarray,
        *,
        confidence_threshold: float = 0.8,
    ) -> list[OCRResult]:
        """
        Extract text from an image using OCR.
        """
        if self._reader is None:
            logger.error("EasyOCR reader not initialized")
            return []

        # Get intermediate results
        raw_results = []
        try:
            # Extract text using EasyOCR
            raw_results = self._reader.readtext(image)
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return []

        # Process and filter results
        results: list[OCRResult] = []
        for result in raw_results:
            raw_bounding_box, text, confidence = result

            # Filter out results below the confidence threshold
            if float(confidence) < confidence_threshold:
                continue

            # Build a bounding box from the raw EasyOCR values
            bounding_box: tuple[Coordinate, Coordinate, Coordinate, Coordinate] = (
                Coordinate(*[int(value) for value in raw_bounding_box[0]]),
                Coordinate(*[int(value) for value in raw_bounding_box[1]]),
                Coordinate(*[int(value) for value in raw_bounding_box[2]]),
                Coordinate(*[int(value) for value in raw_bounding_box[3]]),
            )

            # Create an OCRResult object
            ocr_result = OCRResult(
                text=text.strip(),
                bounding_box=bounding_box,
                confidence=float(confidence),
            )
            results.append(ocr_result)

        return results
