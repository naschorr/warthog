from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator

from enums import Country
from models.serializable_model import SerializableModel
from .currency_models import Currency
from .damage_models import DamageSection
from .scouting_models import ScoutingSection
from .activity_models import ActivityEntry, TimePlayedEntry, CaptureEntry
from .reward_models import AwardEntry, SkillBonusEntry, Research, BoosterInfo


class BattleSummary(BaseModel):
    """Summary information about a battle's results."""

    earnings: Currency = Field(default_factory=Currency)
    total_currency: Currency = Field(default_factory=Currency)
    activity_percentage: float = Field(default=0.0, ge=0.0, le=1.0)
    damaged_vehicles: list[str] = Field(default_factory=list)
    repair_cost: int = 0
    ammo_cost: int = 0
    research: Research = Field(default_factory=Research)
    boosters: list[BoosterInfo] = Field(default_factory=list)


class Battle(SerializableModel):
    """Represents a complete War Thunder battle record."""

    # Derived/external fields
    timestamp: Optional[datetime] = None
    country: Optional[Country] = None
    player_battle_rating: Optional[float] = Field(
        default=None,
        description="Player's battle rating in the battle",
        ge=0.0,
        multiple_of=0.1,
    )
    enemy_battle_rating: Optional[float] = Field(
        default=None,
        description="Maximum battle rating of encountered enemies",
        ge=0.0,
        multiple_of=0.1,
    )

    # Fields provided by the game
    session: str
    mission_name: str
    mission_type: str
    victory: bool
    player_vehicles: list[str] = Field(default_factory=list)
    enemy_vehicles: list[str] = Field(default_factory=list)
    damage: DamageSection = Field(default_factory=DamageSection)
    scouting: ScoutingSection = Field(default_factory=ScoutingSection)
    captures: list[CaptureEntry] = Field(default_factory=list)
    awards: list[AwardEntry] = Field(default_factory=list)
    activity: list[ActivityEntry] = Field(default_factory=list)
    time_played: list[TimePlayedEntry] = Field(default_factory=list)
    reward: Currency = Field(default_factory=Currency)
    skill_bonus: list[SkillBonusEntry] = Field(default_factory=list)
    summary: BattleSummary = Field(default_factory=BattleSummary)

    # Lifecycle

    def __init__(self, **data):
        super().__init__(**data)

    # Magic Methods

    def __eq__(self, other) -> bool:
        """Check if two battles are equal based on their session ID."""
        if not isinstance(other, Battle):
            raise TypeError("Comparison must be with another Battle instance")

        return self.session == other.session

    # Properties

    @property
    def battle_rating_discrepancy(self) -> float:
        """
        Calculate the discrepancy between player and enemy battle ratings. Positive values if the player's rating is
        higher, negative if the enemy's rating is higher.
        """
        if self.player_battle_rating is None or self.enemy_battle_rating is None:
            return 0.0
        return self.player_battle_rating - self.enemy_battle_rating

    # Pydantic De/Serialization

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

    # Methods

    def save_to_file(self, directory: Path) -> Path:
        """Save the battle to a JSON file in the specified directory."""
        filename = f"{self.session}.json"
        file_path = directory / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

        return file_path
