from enum import Enum


class VehicleType(Enum):
    """Enum representing different vehicle types in War Thunder."""

    # Air Vehicle Types
    FIGHTER = "Fighter"
    STRIKE_AIRCRAFT = "Strike Aircraft"
    BOMBER = "Bomber"

    # Helicopter Types
    ATTACK_HELICOPTER = "Attack Helicopter"
    UTILITY_HELICOPTER = "Utility Helicopter"

    # Ground Vehicle Types
    LIGHT_TANK = "Light Tank"
    MEDIUM_TANK = "Medium Tank"
    HEAVY_TANK = "Heavy Tank"
    TANK_DESTROYER = "Tank Destroyer"
    ANTI_AIR = "Anti-Air"

    # Bluewater Fleet Vehicle Types
    DESTROYER = "Destroyer"
    LIGHT_CRUISER = "Light Cruiser"
    HEAVY_CRUISER = "Heavy Cruiser"
    BATTLESHIP = "Battleship"
    BATTLECRUISER = "Battlecruiser"

    # Coastal Fleet Vehicle Types
    BARGE = "Barge"
    BOAT = "Boat"
    HEAVY_BOAT = "Heavy Boat"
    FRIGATE = "Frigate"
