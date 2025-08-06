from typing import Optional

from pydantic import BaseModel, Field

from .currency_models import Currency


class ScoutingEntry(BaseModel):
    """Represents a single scouting event in a battle."""

    timestamp: str
    scout_vehicle: str
    target_vehicle: str
    mission_points: int
    currency: Currency = Field(default_factory=Currency)

    def __init__(self, **data):
        # Handle backward compatibility with old data format
        if "sl_reward" in data:
            if "currency" not in data:
                data["currency"] = {}
            data["currency"]["silver_lions"] = data.pop("sl_reward")

        super().__init__(**data)


class ScoutingDestructionEntry(BaseModel):
    """Represents destruction of an enemy that was scouted by the player."""

    timestamp: str
    scout_vehicle: str
    target_vehicle: str
    mission_points: int
    currency: Currency = Field(default_factory=Currency)

    def __init__(self, **data):
        # Handle backward compatibility with old data format
        if "sl_reward" in data:
            if "currency" not in data:
                data["currency"] = {}
            data["currency"]["silver_lions"] = data.pop("sl_reward")
        if "rp_reward" in data:
            if "currency" not in data:
                data["currency"] = {}
            data["currency"]["research_points"] = data.pop("rp_reward")
        if "rp_booster" in data and data["rp_booster"] is not None:
            if "currency" not in data:
                data["currency"] = {}
            data["currency"]["rp_booster"] = data.pop("rp_booster")
        if "total_rp" in data and data["total_rp"] is not None:
            if "currency" not in data:
                data["currency"] = {}
            data["currency"]["total_rp"] = data.pop("total_rp")

        super().__init__(**data)


class ScoutingSection(BaseModel):
    """Collection of scouting-related entries."""

    scouted: list[ScoutingEntry] = []
    damage_by_scouted: list[ScoutingEntry] = []
    destruction_of_scouted: list[ScoutingDestructionEntry] = []
