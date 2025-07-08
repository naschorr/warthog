from typing import List, Optional

from pydantic import BaseModel, Field

from .currency_models import Currency


class ActivityEntry(BaseModel):
    """Represents activity time for a specific vehicle."""

    vehicle: str
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


class TimePlayedEntry(BaseModel):
    """Represents time played with a specific vehicle."""

    vehicle: str
    activity_percentage: int
    time_str: str
    currency: Currency = Field(default_factory=Currency)

    def __init__(self, **data):
        # Handle backward compatibility with old data format
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


class CaptureEntry(BaseModel):
    """Represents a point capture event."""

    timestamp: str
    vehicle: str
    capture_percentage: int
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


class LandingEntry(BaseModel):
    """Represents a landing reward for an aircraft."""

    timestamp: str
    vehicle: str
    currency: Currency = Field(default_factory=Currency)

    def __init__(self, **data):
        # Handle backward compatibility with old data format
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
