from typing import Optional

from pydantic import BaseModel, Field

from src.common.enums import Country, BattleType


class WarthogReplayDataExplorerConfig(BaseModel):
    """Replay data explorer specific configuration."""

    player_name: Optional[str] = Field(
        default=None,
        description="Player name to analyze in the replays. If None, the replay author will be analyzed.",
    )

    country_filters: list[Country] = Field(
        default_factory=list,
        description="List of countries to filter replays by.",
    )

    battle_type: BattleType = Field(
        default=BattleType.REALISTIC,
        description="The type of battle to analyze.",
    )

    standard_deviation: float = Field(
        default=2.0,
        description="Number of standard deviations to use for outlier removal in performance data.",
    )
