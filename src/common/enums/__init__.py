"""
Common enums for representing data.
"""

from .battle_type import BattleType
from .country import Country
from .platform_type import PlatformType
from .vehicle_type import VehicleType

# For type checking and explicit exports
__all__ = ["Country", "VehicleType", "BattleType", "PlatformType"]
