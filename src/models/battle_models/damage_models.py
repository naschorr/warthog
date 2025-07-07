from typing import Optional

from pydantic import BaseModel, Field

from .currency_models import Currency


class DamageEntry(BaseModel):
    """Represents a single damage event in a battle."""

    timestamp: str
    attack_vehicle: str
    ammunition: str
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


class DamageSection(BaseModel):
    """Collection of damage-related entries."""

    destruction_ground: list[DamageEntry] = Field(default_factory=list)
    destruction_air: list[DamageEntry] = Field(default_factory=list)
    critical: list[DamageEntry] = Field(default_factory=list)
    assistance: list[DamageEntry] = Field(default_factory=list)
    damage: list[DamageEntry] = Field(default_factory=list)
