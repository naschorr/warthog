"""
Common services
"""

from .logging_service import LoggingService
from .vehicle_service import VehicleService

# For type checking and explicit exports
__all__ = [
    "LoggingService",
    "VehicleService",
]
