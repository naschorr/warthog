"""
War Thunder replay kills model.
"""

from pydantic import Field

from src.common.models.serializable_model import SerializableModel


class Kills(SerializableModel):
    """Represents kill statistics for a player in a War Thunder replay."""

    # Player vs Player kills
    air: int = Field(default=0, description="Air vehicle player kills")
    ground: int = Field(default=0, description="Ground vehicle player kills")
    naval: int = Field(default=0, description="Naval vehicle player kills")
    team: int = Field(default=0, description="Team kills (friendly fire)")

    # AI kills
    ai_air: int = Field(default=0, description="AI aircraft kills")
    ai_ground: int = Field(default=0, description="AI ground vehicle kills")
    ai_naval: int = Field(default=0, description="AI naval vehicle kills")

    @property
    def total_player_kills(self) -> int:
        """Get total player kills (excluding AI)."""
        return self.air + self.ground + self.naval

    @property
    def total_ai_kills(self) -> int:
        """Get total AI kills."""
        return self.ai_air + self.ai_ground + self.ai_naval

    @property
    def total_kills(self) -> int:
        """Get total kills (including AI)."""
        return self.total_player_kills + self.total_ai_kills
