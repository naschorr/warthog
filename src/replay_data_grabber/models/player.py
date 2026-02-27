from typing import Optional
from pydantic import Field, field_validator, field_serializer

from .kills import Kills
from .deaths import Deaths
from src.common.enums import PlatformType, Country
from src.common.models.serializable_model import SerializableModel


class Player(SerializableModel):
    """Represents a player in a War Thunder replay with their performance data."""

    # Player identity fields
    user_id: str = Field(default="")
    username: str = Field(default="")
    squadron_id: Optional[str] = Field(default=None)
    squadron_tag: Optional[str] = Field(default=None)
    platform: str = Field(default="")
    platform_type: Optional[PlatformType] = Field(default=None)
    country: Optional[Country] = Field(default=None)

    # Replay metadata
    team: Optional[int] = Field(default=None)
    squad: Optional[int] = Field(default=None)
    auto_squad: bool = Field(default=False)
    slot: Optional[int] = Field(
        default=None,
        description="0-based position in the replay players array; stable stream-space identifier",
    )
    wait_time: float = Field(default=0.0)
    tier: Optional[int] = Field(default=None)
    rank: Optional[int] = Field(default=None)
    m_rank: Optional[int] = Field(default=None)
    battle_rating: float = Field(default=0.0)
    min_battle_rating: float = Field(default=0.0)
    mean_battle_rating: float = Field(default=0.0)

    # Performance
    kills: Kills = Field(default_factory=Kills)
    assists: int = Field(default=0)
    deaths: Deaths = Field(default_factory=Deaths)
    capture_zone: int = Field(default=0)
    damage_zone: int = Field(default=0)
    score: int = Field(default=0)
    award_damage: int = Field(default=0)
    missile_evades: int = Field(default=0)

    # Vehicle stats
    lineup: list[str] = Field(default_factory=list)
    is_premium: bool = Field(
        default=False, description="Indicates if the player has any premium vehicles in their lineup"
    )
    vehicle_kills: dict[str, int] = Field(
        default_factory=dict,
        description="Kill counts keyed by vehicle internal name",
    )
    vehicle_deaths: dict[str, int] = Field(
        default_factory=dict,
        description=("Death counts keyed by vehicle internal name (might be inaccurate)"),
    )
    awards: list[str] = Field(
        default_factory=list,
        description="Award internal identifiers received by this player",
    )

    def model_post_init(self, __context) -> None:
        """Initialize lineup list if None."""
        if self.lineup is None:
            self.lineup = []

    @property
    def kill_death_ratio(self) -> float:
        """Calculate kill/death ratio."""
        if self.deaths.total == 0:
            return float(self.kills.total_kills) if self.kills.total_kills > 0 else 0.0
        return self.kills.total_kills / self.deaths.total

    @property
    def total_kills(self) -> int:
        """Get total kills (including AI)."""
        return self.kills.total_kills

    @property
    def display_name(self) -> str:
        """Get display name with squadron tag if available."""
        if self.squadron_tag:
            return f"[{self.squadron_tag}] {self.username}"
        return self.username

    # Pydantic De/Serialization

    @field_validator("platform_type", mode="before")
    @classmethod
    def validate_platform_type(cls, v: str | PlatformType) -> PlatformType:
        """Convert string platform values to PlatformType enum."""
        if isinstance(v, str):
            for platform_enum in PlatformType:
                if platform_enum.value == v:
                    return platform_enum
            raise ValueError(f"Invalid platform: {v}")
        return v

    @field_serializer("platform_type")
    @classmethod
    def serialize_platform_type(cls, v: PlatformType) -> str:
        """Serialize PlatformType enum to its string value."""
        return v.value if isinstance(v, PlatformType) else str(v)

    @field_validator("country", mode="before")
    @classmethod
    def validate_country(cls, v: str | Country) -> Country:
        """Convert string country values to Country enum."""
        if isinstance(v, str):
            for country_enum in Country:
                if country_enum.value == v:
                    return country_enum
            raise ValueError(f"Invalid country: {v}")
        return v

    @field_serializer("country")
    @classmethod
    def serialize_country(cls, v: Country) -> str:
        """Serialize Country enum to its string value."""
        return v.value if isinstance(v, Country) else str(v)
