"""
Death-summary model for War Thunder replay data.
"""

from pydantic import Field

from src.common.models.serializable_model import SerializableModel
from .death_detail import DeathDetail


class Deaths(SerializableModel):
    """
    Aggregated death statistics plus per-event detail records for a player.

    ``total`` is the authoritative scoreboard value from the BLK results JSON.
    ``vehicles`` is a best-effort per-event breakdown derived from the replay
    stream; it may contain fewer entries than ``total`` when some kills cannot
    be attributed to a specific vehicle or the death occurred before any
    tankModels event fired.
    """

    total: int = Field(default=0, description="Authoritative total deaths from BLK results")
    vehicles: list[DeathDetail] = Field(
        default_factory=list,
        description="Per-death event detail records (best-effort, may be incomplete)",
    )
