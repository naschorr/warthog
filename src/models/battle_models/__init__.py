"""
Battle models for War Thunder data.

This module contains models that were relocated from the parent models package.
"""

# Import and re-export all models explicitly
from .activity_models import ActivityEntry, TimePlayedEntry, CaptureEntry, LandingEntry
from .battle_models import BattleSummary, Battle
from .currency_models import Currency
from .damage_models import DamageEntry, DamageSection
from .reward_models import (
    AwardEntry,
    SkillBonusEntry,
    Research,
    ResearchUnit,
    ResearchProgress,
    BoosterInfo,
)
from .scouting_models import ScoutingEntry, ScoutingDestructionEntry, ScoutingSection

# Define __all__ for explicit exports
__all__ = [
    "Currency",
    "DamageEntry",
    "DamageSection",
    "ScoutingEntry",
    "ScoutingDestructionEntry",
    "ScoutingSection",
    "ActivityEntry",
    "TimePlayedEntry",
    "CaptureEntry",
    "LandingEntry",
    "AwardEntry",
    "SkillBonusEntry",
    "Research",
    "ResearchUnit",
    "ResearchProgress",
    "BoosterInfo",
    "BattleSummary",
    "Battle",
]
