from typing import Optional

from pydantic import BaseModel, Field

from .currency_models import Currency


class AwardEntry(BaseModel):
    """Represents an award earned in battle."""

    timestamp: Optional[str] = None
    name: str
    currency: Currency = Field(default_factory=Currency)


class SkillBonusEntry(BaseModel):
    """Represents skill bonus for a specific vehicle."""

    vehicle: str
    tier: str
    currency: Currency = Field(default_factory=Currency)


class ResearchUnit(BaseModel):
    """Represents a researchable unit in War Thunder."""

    unit: str
    currency: Currency = Field(default_factory=Currency)


class ResearchProgress(BaseModel):
    """Represents research progress on a specific vehicle/module."""

    item: str
    currency: Currency = Field(default_factory=Currency)


class Research(BaseModel):
    """Represents research progress for a specific vehicle."""

    research_units: list[ResearchUnit] = Field(default_factory=list)
    research_progress: list[ResearchProgress] = Field(default_factory=list)


class BoosterInfo(BaseModel):
    """Represents information about an active booster."""

    type: str
    rarity: str
    percentage: int
    description: Optional[str] = None
