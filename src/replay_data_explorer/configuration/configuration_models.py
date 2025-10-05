from typing import Optional
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from src.common.utilities import get_root_directory
from src.common.enums import Country, BattleType
from src.common.configuration.validators import Validators


class GraphExportConfig(BaseModel):
    """Configuration for exporting graphs."""

    output_directory_path: Path = Field(
        default=get_root_directory() / "output" / "graphs",
        description="Directory to save exported graphs.",
    )

    @field_validator("output_directory_path")
    @classmethod
    def ensure_output_directory_exists(cls, v: Path) -> Path:
        return Validators.create_directory_validator(v)

    enable_png_export: bool = Field(
        default=False,
        description="Whether to enable exporting graphs as PNG images.",
    )

    png_width: Optional[int] = Field(
        default=1200,
        description="Width of exported PNG images in pixels.",
    )

    png_height: Optional[int] = Field(
        default=None,
        description="Height of exported PNG images in pixels.",
    )

    png_scale: float = Field(
        default=1.0,
        description="Scale factor for PNG resolution (e.g., 2.0 for 2x resolution).",
    )


class WarthogReplayDataExplorerConfig(BaseModel):
    """Replay data explorer specific configuration."""

    player_name: Optional[str] = Field(
        default=None,
        description="Player name to analyze in the replays. If None, the replay author will be analyzed.",
    )

    @field_validator("player_name")
    @classmethod
    def ensure_player_name_isnt_placeholder(cls, v: Optional[str]) -> Optional[str]:
        if v and v == "<username>":  # Technically a player could be named this, but it's super unlikely
            return None
        return v

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

    graph_export_config: GraphExportConfig = Field(default_factory=GraphExportConfig)
