from src.replay_data_explorer.enums import BattleRatingTier
from src.replay_data_explorer.common import hex_to_rgba

# Define common colors for battle rating tiers
BATTLE_RATING_TIER_COLORS = {
    BattleRatingTier.DOWNTIER: {"hex": "#ff0000"},
    BattleRatingTier.PARTIAL_DOWNTIER: {"hex": "#FF5A00"},
    BattleRatingTier.BALANCED: {"hex": "#0000ff"},
    BattleRatingTier.PARTIAL_UPTIER: {"hex": "#00C24E"},
    BattleRatingTier.UPTIER: {"hex": "#0A9200"},
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
    BattleRatingTier.UPTIER,
    BattleRatingTier.PARTIAL_UPTIER,
    BattleRatingTier.BALANCED,
    BattleRatingTier.PARTIAL_DOWNTIER,
    BattleRatingTier.DOWNTIER,
]

PLOTLY_TRENDLINE_OPACITY = 0.5

PLOTLY_COLOR_SCALE = [
    (0, BATTLE_RATING_TIER_COLORS[BattleRatingTier.BALANCED]["hex"]),
    (1, BATTLE_RATING_TIER_COLORS[BattleRatingTier.PARTIAL_DOWNTIER]["hex"]),
]

PLOTLY_SINGLE_COLOR = hex_to_rgba(BATTLE_RATING_TIER_COLORS[BattleRatingTier.BALANCED]["hex"], 0.75)

PLOTLY_CONCLUSION_COLORS = {
    "good": BATTLE_RATING_TIER_COLORS[BattleRatingTier.UPTIER]["hex"],
    "neutral": "#808080",
    "bad": BATTLE_RATING_TIER_COLORS[BattleRatingTier.DOWNTIER]["hex"],
}

MINIMUM_ITEMS_FOR_PLOTTING = 10
