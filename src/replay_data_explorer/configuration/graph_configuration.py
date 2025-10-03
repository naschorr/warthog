from src.replay_data_explorer.enums import BattleRatingTier
from src.replay_data_explorer.common import hex_to_rgba

# Define common colors for battle rating tiers
BATTLE_RATING_TIER_COLORS = {
    BattleRatingTier.DOWNTIER: {"hex": "#0A9200"},
    BattleRatingTier.PARTIAL_DOWNTIER: {"hex": "#00C24E"},
    BattleRatingTier.BALANCED: {"hex": "#0000ff"},
    BattleRatingTier.PARTIAL_UPTIER: {"hex": "#FF5A00"},
    BattleRatingTier.UPTIER: {"hex": "#ff0000"},
}

# Define Plotly specific configurations
PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS = {
    BattleRatingTier.DOWNTIER: BATTLE_RATING_TIER_COLORS[BattleRatingTier.DOWNTIER]["hex"],
    BattleRatingTier.PARTIAL_DOWNTIER: BATTLE_RATING_TIER_COLORS[BattleRatingTier.PARTIAL_DOWNTIER]["hex"],
    BattleRatingTier.BALANCED: BATTLE_RATING_TIER_COLORS[BattleRatingTier.BALANCED]["hex"],
    BattleRatingTier.PARTIAL_UPTIER: BATTLE_RATING_TIER_COLORS[BattleRatingTier.PARTIAL_UPTIER]["hex"],
    BattleRatingTier.UPTIER: BATTLE_RATING_TIER_COLORS[BattleRatingTier.UPTIER]["hex"],
}

PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER = [
    BattleRatingTier.DOWNTIER,
    BattleRatingTier.PARTIAL_DOWNTIER,
    BattleRatingTier.BALANCED,
    BattleRatingTier.PARTIAL_UPTIER,
    BattleRatingTier.UPTIER,
]

PLOTLY_TRENDLINE_OPACITY = 0.5

PLOTLY_COLOR_SCALE = [
    (0, BATTLE_RATING_TIER_COLORS[BattleRatingTier.BALANCED]["hex"]),
    (1, BATTLE_RATING_TIER_COLORS[BattleRatingTier.PARTIAL_UPTIER]["hex"]),
]

PLOTLY_SINGLE_COLOR = hex_to_rgba(BATTLE_RATING_TIER_COLORS[BattleRatingTier.BALANCED]["hex"], 0.75)

PLOTLY_CONCLUSION_COLORS = {
    "good": BATTLE_RATING_TIER_COLORS[BattleRatingTier.DOWNTIER]["hex"],
    "neutral": "#808080",
    "bad": BATTLE_RATING_TIER_COLORS[BattleRatingTier.UPTIER]["hex"],
}

MINIMUM_ITEMS_FOR_PLOTTING = 10
