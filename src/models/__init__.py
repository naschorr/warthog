"""
Data models for representing War Thunder battle data.

This module re-exports models from specialized model modules.
"""

# Coordinate model (kept in the original location)
from .coordinate import Coordinate

# For type checking and explicit exports
__all__ = ["Coordinate"]
