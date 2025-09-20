from enum import Enum


class BattleRatingTierDisplay(str, Enum):
    DOWNTIER = "Downtier"
    PARTIAL_DOWNTIER = "Partial Downtier"
    BALANCED = "Balanced"
    PARTIAL_UPTIER = "Partial Uptier"
    UPTIER = "Uptier"
