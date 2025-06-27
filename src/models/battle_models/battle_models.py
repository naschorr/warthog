from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .base_models import SerializableModel
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

    timestamp: Optional[datetime] = None
    session: str
    mission_name: str
    mission_type: str
    victory: bool
    vehicles: list[str] = Field(default_factory=list)
    damage: DamageSection = Field(default_factory=DamageSection)
    scouting: ScoutingSection = Field(default_factory=ScoutingSection)
    captures: list[CaptureEntry] = Field(default_factory=list)
    awards: list[AwardEntry] = Field(default_factory=list)
    activity: list[ActivityEntry] = Field(default_factory=list)
    time_played: list[TimePlayedEntry] = Field(default_factory=list)
    reward: Currency = Field(default_factory=Currency)
    skill_bonus: list[SkillBonusEntry] = Field(default_factory=list)
    summary: BattleSummary = Field(default_factory=BattleSummary)

    def save_to_file(self, directory: Path) -> Path:
        """Save the battle to a JSON file in the specified directory."""
        filename = f"{self.session}.json"
        file_path = directory / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

        return file_path

    def __init__(self, **data):
        super().__init__(**data)
