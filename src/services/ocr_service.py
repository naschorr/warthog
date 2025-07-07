import logging

logger = logging.getLogger(__name__)

from typing import Optional

import cv2
import torch
import easyocr
import numpy as np

from config import get_config
from services import WindowService
from models import Coordinate
from models import OCRResult


class OCRService:
    """
    Handles OCR (Optical Character Recognition) operations
    """

    ## Lifecycle

    def __init__(self):
        self._config = get_config()
        self._window_service = WindowService()

        self._languages = ["en"]

        try:
            self._reader = easyocr.Reader(
                self._languages, gpu=self._is_cuda_available()
            )
            logger.info("EasyOCR initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")

    ## Methods

    def _is_cuda_available(self) -> bool:
        """
        Check if CUDA is available for GPU acceleration.
        """
        try:
            return torch.cuda.is_available()
        except Exception as e:
            logger.error(f"Error checking CUDA availability: {e}")
            return False

    def extract_text_from_image(
        self,
        image: np.ndarray,
        *,
        confidence_threshold: Optional[float] = None,
    ) -> list[OCRResult]:
        """
        Extract text from an image using OCR.
        """
        # Sanity check for the OCR reader
        if self._reader is None:
            logger.error("EasyOCR reader not initialized")
            return []

        # Load configured defaults
        if confidence_threshold is None:
            confidence_threshold = self._config.ocr_config.confidence_threshold

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
            if confidence_threshold and float(confidence) < confidence_threshold:
                logger.debug(
                    f"Skipping result '{text.strip()}' with confidence {confidence} below threshold {confidence_threshold}"
                )
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
