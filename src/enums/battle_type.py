from enum import Enum


class BattleType(Enum):
    """Enum representing different battle types in War Thunder."""

    ARCADE = "arcade"
    REALISTIC = "realistic"
    SIMULATION = "simulation"
    UNKNOWN = "unknown"
