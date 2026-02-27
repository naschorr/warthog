from datetime import datetime
from typing import Optional
from pydantic import Field

from src.common.models.serializable_model import SerializableModel


class DeathDetail(SerializableModel):
    """
    Detailed record of a single death event, from the victim's perspective.

    Populated from the replay stream.  All fields are self-contained so the
    record can be read without cross-referencing the parent Player object.
    """

    # Victim fields
    victim_vehicle: str = Field(
        description="Internal name of the vehicle that was killed",
    )
    victim_user_id: Optional[str] = Field(
        default=None,
        description="User ID of the player who was killed",
    )
    victim_username: Optional[str] = Field(
        default=None,
        description="Username of the player who was killed",
    )
    victim_slot: Optional[int] = Field(
        default=None,
        description="Stream-space slot index of the victim",
    )

    # Killer fields
    killer_vehicle: str = Field(
        description="Internal name of the vehicle that scored the kill",
    )
    killer_user_id: str = Field(
        description="User ID of the player who scored the kill",
    )
    killer_username: Optional[str] = Field(
        default=None,
        description="Username of the player who scored the kill",
    )
    killer_slot: Optional[int] = Field(
        default=None,
        description="Stream-space slot index of the killer",
    )

    time_utc: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the death event",
    )
    # TODO: add ammo_used once that stream field is decoded
