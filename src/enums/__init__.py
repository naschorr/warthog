"""
Basic enums for representing data.
"""

from .battle_type import BattleType
from .country import Country
from .platform_type import PlatformType
from .vehicle_type import VehicleType
from .app_mode import AppMode

# For type checking and explicit exports
__all__ = ["Country", "VehicleType", "BattleType", "AppMode", "PlatformType"]
