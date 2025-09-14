from enum import Enum


class BattleRatingTier(str, Enum):
    DOWNTIER = "downtier"
    PARTIAL_DOWNTIER = "partial_downtier"
    BALANCED = "balanced"
    PARTIAL_UPTIER = "partial_uptier"
    UPTIER = "uptier"
