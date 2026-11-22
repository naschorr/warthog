import json
import sys
import os
import datetime
from pathlib import Path
from collections import Counter, OrderedDict, defaultdict
from typing import Optional
from enum import Enum

# Import third-party libraries
import pandas as pd
import numpy as np

# Import Plotly for interactive visualizations
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

# Import project modules
from src.replay_data_explorer.services import BattleRatingTierDisplayBuilder
from confiddle import Confiddle, ConfiddleConfigModel, JsonProviderConfig, ProviderConfigModel
from src.common.configuration import WarthogConfig
from src.common.utilities import get_root_directory
from src.common.enums import BattleType, Country, VehicleType
from src.common.models.vehicle_models import Vehicle
from src.common.factories import ServiceFactory
from src.replay_data_explorer.enums import BattleRatingTier
from src.replay_data_explorer.services import BattleRatingTierClassifier, DataFilterer, DataLoaders, TitleBuilder
from src.replay_data_explorer.common import hex_to_rgba
from src.replay_data_explorer.configuration.graph_configuration import *


def get_battle_rating_axis_options(battle_ratings: pd.Series) -> dict[str, object]:
    """Return shared BR ticks and half-step padding for numeric BR axes."""
    values = pd.to_numeric(battle_ratings, errors="raise").dropna()
    battle_ratings = sorted({round(float(value), 1) for value in values})
    if not battle_ratings:
        raise ValueError("At least one battle rating is required to configure the axis")

    return {
        "range": [
            round(battle_ratings[0] - BATTLE_RATING_AXIS_PADDING, 2),
            round(battle_ratings[-1] + BATTLE_RATING_AXIS_PADDING, 2),
        ],
        "tickmode": "array",
        "tickvals": battle_ratings,
        "ticktext": [f"{battle_rating:.1f}" for battle_rating in battle_ratings],
        "tickangle": 45 if len(battle_ratings) > 10 else 0,
    }


def get_battle_rating_category_axis_options(battle_ratings: list[float]) -> dict[str, object]:
    """Keep the first and last BR heatmap cells fully visible."""
    if not battle_ratings:
        raise ValueError("At least one battle rating is required to configure the axis")

    return {
        "type": "category",
        "range": [-0.5, len(battle_ratings) - 0.5],
    }


def filter_to_replay_br_ceiling(df: pd.DataFrame, battle_rating_column: str) -> tuple[pd.DataFrame, Optional[float]]:
    """Keep rows where the plotted BR does not exceed that row's replay BR."""
    if "battle_rating" not in df.columns:
        raise ValueError("DataFrame must include replay battle_rating")
    if battle_rating_column not in df.columns:
        raise ValueError(f"DataFrame must include {battle_rating_column}")

    replay_brs = pd.to_numeric(df["battle_rating"], errors="raise")
    player_brs = pd.to_numeric(df[battle_rating_column], errors="raise")
    valid_rows = replay_brs.notna() & (replay_brs > 0) & player_brs.notna() & (player_brs <= replay_brs)
    if not valid_rows.any():
        return df.iloc[0:0].copy(), None

    max_replay_br = float(replay_brs.loc[valid_rows].max())
    return df.loc[valid_rows].copy(), max_replay_br


def get_br_limited_graph_data(
    performance_df: pd.DataFrame,
    columns: list[str],
    *,
    battle_rating_column: str,
    require_valid_br_delta: bool = False,
) -> tuple[pd.DataFrame, Optional[float]]:
    """Select graph-required columns and apply the shared BR and delta limits."""
    required_columns = list(dict.fromkeys(["battle_rating", battle_rating_column, *columns]))
    if require_valid_br_delta and "player.battle_rating_delta" not in required_columns:
        required_columns.append("player.battle_rating_delta")

    missing_columns = [column for column in required_columns if column not in performance_df.columns]
    if missing_columns:
        raise ValueError(f"Performance data is missing required columns: {missing_columns}")

    graph_df = performance_df.loc[:, required_columns].copy()
    graph_df, _ = filter_to_replay_br_ceiling(graph_df, battle_rating_column)
    if require_valid_br_delta:
        graph_df = graph_df[graph_df["player.battle_rating_delta"] <= 0.0]
    if graph_df.empty:
        return graph_df, None

    max_replay_br = float(pd.to_numeric(graph_df["battle_rating"], errors="raise").max())
    return graph_df, max_replay_br


def get_player_br_limited_graph_data(
    performance_df: pd.DataFrame,
    columns: list[str],
    *,
    battle_rating_column: str,
    require_valid_br_delta: bool = False,
) -> tuple[pd.DataFrame, Optional[float]]:
    """Select player graph data and return its maximum observed player BR."""
    graph_df, _ = get_br_limited_graph_data(
        performance_df,
        columns,
        battle_rating_column=battle_rating_column,
        require_valid_br_delta=require_valid_br_delta,
    )

    if graph_df.empty:
        return graph_df, None

    max_player_br = float(pd.to_numeric(graph_df[battle_rating_column], errors="raise").max())
    return graph_df, max_player_br


# Initialize configuration
_confiddle = Confiddle(
    ConfiddleConfigModel(
        app=ProviderConfigModel(json_file_provider=JsonProviderConfig(directory_path=get_root_directory() / "src"))
    )
)
_warthog_config = _confiddle.load_config(WarthogConfig)
config = _warthog_config.replay_data_explorer_config

# Initialize replay_data_grabber services
service_factory = ServiceFactory(_warthog_config)
vehicle_service = service_factory.get_vehicle_service()
replay_manager_service = service_factory.get_replay_manager_service()

# Initialize replay_data_explorer services and utility functions
battle_rating_tier_classifier = BattleRatingTierClassifier()
battle_rating_tier_display_builder = BattleRatingTierDisplayBuilder()
data_filterer = DataFilterer()
data_loaders = DataLoaders(replay_manager_service)
title_builder = TitleBuilder()
