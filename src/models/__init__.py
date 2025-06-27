"""
Data models for representing War Thunder battle data.

This module re-exports models from specialized model modules.
"""

from .coordinate import Coordinate
from .ocr_result import OCRResult

# For type checking and explicit exports
__all__ = ["Coordinate", "OCRResult"]
