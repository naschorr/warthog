"""
Basic enums for representing data.
"""

from .battle_type import BattleType
from .country import Country
from .vehicle_type import VehicleType

# For type checking and explicit exports
__all__ = ["Country", "VehicleType", "BattleType"]
