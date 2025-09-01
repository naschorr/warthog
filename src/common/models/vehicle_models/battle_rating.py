from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class BattleRating(BaseModel):
    """Represents the battle rating of a vehicle in different game modes."""

    arcade: float = Field(description="Battle rating in Arcade battles", ge=0.0)
    realistic: float = Field(description="Battle rating in Realistic battles", ge=0.0)
    simulation: float = Field(description="Battle rating in Simulation battles", ge=0.0)

    # Lifecycle

    def __init__(self, **data):
        super().__init__(**data)
