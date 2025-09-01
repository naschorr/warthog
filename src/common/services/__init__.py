"""
Common services
"""

from .git_service import GitService
from .logging_service import LoggingService
from .vehicle_service import VehicleService

# For type checking and explicit exports
__all__ = [
    "GitService",
    "LoggingService",
    "VehicleService",
]
