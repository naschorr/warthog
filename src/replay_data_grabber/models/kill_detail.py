from datetime import datetime
from typing import Optional
from pydantic import Field

from src.common.models.serializable_model import SerializableModel


class KillDetail(SerializableModel):
    """
    Detailed record of a single kill event, from the killer's perspective.

    Populated from the replay stream.  All fields are self-contained so the
    record can be read without cross-referencing the parent Player object.
    """

    # Killer fields
    killer_vehicle: str = Field(description="Internal name of the vehicle that scored the kill")
    killer_user_id: Optional[str] = Field(
        default=None,
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

    # Victim fields
    victim_vehicle: Optional[str] = Field(
        default=None,
        description="Internal name of the vehicle that was killed (None if unresolvable from stream)",
    )
    victim_user_id: Optional[str] = Field(
        default=None,
        description="User ID of the player who was killed (None if unresolvable from stream)",
    )
    victim_username: Optional[str] = Field(
        default=None,
        description="Username of the player who was killed (None if unresolvable from stream)",
    )
    victim_slot: Optional[int] = Field(
        default=None,
        description="Stream-space slot index of the victim (None if unresolvable from stream)",
    )

    time_utc: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the kill event",
    )
    # TODO: add ammo_used once that stream field is decoded
