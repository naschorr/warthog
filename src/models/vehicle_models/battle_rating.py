from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class BattleRating(BaseModel):
    """Represents the battle rating of a vehicle in different game modes."""

    arcade: float = Field(description="Battle rating in Arcade battles", ge=0.0, multiple_of=0.1)
    realistic: float = Field(description="Battle rating in Realistic battles", ge=0.0, multiple_of=0.1)
    simulation: float = Field(description="Battle rating in Simulation battles", ge=0.0, multiple_of=0.1)

    # Lifecycle

    def __init__(self, **data):
        super().__init__(**data)

    # Magic Methods

    def __gt__(self, other: "BattleRating") -> bool:
        """Check if this battle rating is greater than another."""
        return self.arcade > other.arcade and self.realistic > other.realistic and self.simulation > other.simulation

    def __ge__(self, other: "BattleRating") -> bool:
        """Check if this battle rating is greater than or equal to another."""
        return self.arcade >= other.arcade and self.realistic >= other.realistic and self.simulation >= other.simulation
