"""
Data models for representing War Thunder battle data.

This module re-exports models from specialized model modules.
"""

# Base models
from .base_models import SerializableModel

# Currency model
from .currency_models import Currency

# Damage models
from .damage_models import (
    DamageEntry,
    DamageSection
)

# Scouting models
from .scouting_models import (
    ScoutingEntry,
    ScoutingDestructionEntry,
    ScoutingSection
)

# Activity models
from .activity_models import (
    ActivityEntry,
    TimePlayedEntry,
    CaptureEntry
)

# Reward models
from .reward_models import (
    AwardEntry,
    SkillBonusEntry,
    Research,
    ResearchUnit,
    ResearchProgress,
    BoosterInfo
)

# Battle models
from .battle_models import (
    BattleSummary,
    Battle
)

# For type checking and explicit exports
__all__ = [
    'SerializableModel',
    'Currency',
    'DamageEntry',
    'DamageSection',
    'ScoutingEntry',
    'ScoutingDestructionEntry',
    'ScoutingSection',
    'ActivityEntry',
    'TimePlayedEntry',
    'CaptureEntry',
    'AwardEntry',
    'SkillBonusEntry',
    'ResearchProgress',
    'BoosterInfo',
    'BattleSummary',
    'Battle'
]