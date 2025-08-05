"""
War Thunder replay model.
"""

from typing import Optional
from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator, field_serializer

from enums import BattleType
from ..serializable_model import SerializableModel
from .player import Player


class Replay(SerializableModel):
    """Represents a complete War Thunder replay file."""

    # Header fields
    version: int = Field(default=0)
    session_id: str = Field(default="")
    level: str = Field(default="")
    level_settings: str = Field(default="")
    battle_type: BattleType = Field(default=BattleType.UNKNOWN)
    environment: str = Field(default="")
    visibility: str = Field(default="")
    session_type: int = Field(default=0)
    loc_name: str = Field(default="")
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    time_limit_minutes: int = Field(default=0)
    score_limit: int = Field(default=0)
    battle_class: str = Field(default="")
    battle_kill_streak: str = Field(default="")
    status: str = Field(default="left")
    time_played: float = Field(default=0.0)

    # Results fields
    author: Player = Field(default_factory=Player)
    players: list[Player] = Field(default_factory=list)

    # Pydantic De/Serialization

    @field_validator("battle_type", mode="before")
    @classmethod
    def validate_battle_type(cls, v: str | BattleType) -> BattleType:
        """Convert string battle type values to BattleType enum."""
        if isinstance(v, str):
            for battle_enum in BattleType:
                if battle_enum.value == v:
                    return battle_enum
            raise ValueError(f"Invalid battle type: {v}")
        return v

    @field_serializer("battle_type")
    @classmethod
    def serialize_battle_type(cls, v: BattleType) -> str:
        """Serialize battle type to its string value."""
        return v.value if isinstance(v, BattleType) else str(v)

    # Methods

    def save_to_file(self, directory: Path) -> Path:
        """Save the replay to a file."""
        file_name_parts = ["replay"]
        if self.start_time:
            file_name_parts.append(self.start_time.strftime("%Y-%m-%d"))
            file_name_parts.append(self.start_time.strftime("%H-%M-%S"))
        file_name_parts.append(self.session_id)

        file_path = directory / f"{'_'.join(file_name_parts)}.json"
        replay_json = self.model_dump_json(indent=2)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(replay_json)

        return file_path
