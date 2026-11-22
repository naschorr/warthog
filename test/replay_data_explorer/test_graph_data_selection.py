from datetime import datetime
import importlib

import pandas as pd

from src.replay_data_explorer.enums import BattleRatingTier
from src.replay_data_explorer.graphs.initialization import (
    get_br_limited_graph_data,
    get_battle_rating_axis_options,
    get_battle_rating_category_axis_options,
    get_player_br_limited_graph_data,
)
from src.replay_data_explorer.graphs.player.heatmap_br_delta_by_country_and_br import (
    create_heatmap_br_delta_by_country_and_br,
)
from src.replay_data_explorer.graphs.player.heatmap_score_by_country_and_br import (
    create_heatmap_score_by_country_and_br,
)
from src.replay_data_explorer.graphs.player.heatmap_winrate_by_country_and_br import (
    create_heatmap_winrate_by_country_and_br,
)
from src.replay_data_explorer.graphs.player.scatter_score_vs_team_mean import create_scatter_score_vs_team_mean
from src.replay_data_explorer.graphs.tier.bar_tier_frequency_vs_br import create_bar_tier_frequency_vs_br


def test_graph_data_uses_each_replay_br_and_only_selects_required_columns() -> None:
    def make_row(
        session_id: str, replay_br: float, player_br: float, author_br: float
    ) -> dict[str, object]:
        return {
            "session_id": session_id,
            "battle_rating": replay_br,
            "author": {"battle_rating": author_br},
            "player.battle_rating": player_br,
            "player.battle_rating_delta": round(player_br - replay_br, 2),
            "player.country": "Germany",
        }

    performance_df = pd.DataFrame(
        [
            make_row(
                "session-normal", replay_br=9.3, player_br=9.3, author_br=9.3
            ),
            make_row(
                "session-player-above-replay",
                replay_br=5.0,
                player_br=5.3,
                author_br=9.3,
            ),
            make_row(
                "session-replay-above-author",
                replay_br=10.0,
                player_br=9.3,
                author_br=9.3,
            ),
            make_row(
                "session-squadmate-lower-br",
                replay_br=14.7,
                player_br=10.3,
                author_br=9.3,
            ),
        ]
    )

    graph_df, max_replay_br = get_br_limited_graph_data(
        performance_df,
        ["session_id", "player.country"],
        battle_rating_column="player.battle_rating",
    )

    assert graph_df["session_id"].tolist() == [
        "session-normal",
        "session-replay-above-author",
        "session-squadmate-lower-br",
    ]
    assert max_replay_br == 14.7
    assert "author" not in graph_df.columns

    valid_delta_df, max_valid_delta_replay_br = get_br_limited_graph_data(
        performance_df,
        ["session_id", "player.country"],
        battle_rating_column="player.battle_rating",
        require_valid_br_delta=True,
    )
    assert valid_delta_df["session_id"].tolist() == [
        "session-normal",
        "session-replay-above-author",
        "session-squadmate-lower-br",
    ]
    assert max_valid_delta_replay_br == 14.7

    player_performance_df = performance_df[
        performance_df["session_id"] != "session-replay-above-author"
    ]
    player_graph_df, max_player_br = get_player_br_limited_graph_data(
        player_performance_df,
        ["session_id", "player.country"],
        battle_rating_column="player.battle_rating",
        require_valid_br_delta=True,
    )
    assert player_graph_df["session_id"].tolist() == [
        "session-normal",
        "session-squadmate-lower-br",
    ]
    assert max_player_br == 10.3


def test_br_axis_preserves_decimal_endpoints_and_adds_edge_padding() -> None:
    axis_options = get_battle_rating_axis_options(pd.Series([1.0, 3.0, 9.3]))
    category_options = get_battle_rating_category_axis_options([1.0, 9.3])

    assert axis_options["range"] == [0.85, 9.45]
    assert axis_options["tickvals"] == [1.0, 3.0, 9.3]
    assert axis_options["ticktext"] == ["1.0", "3.0", "9.3"]
    assert category_options["range"] == [-0.5, 1.5]


def test_player_graph_axes_extend_to_player_br() -> None:
    player_rows = []
    teammate_rows = []
    for index, (player_br, replay_br) in enumerate(((8.7, 9.7), (9.3, 10.3))):
        session_id = f"session-{index}"
        player_rows.append(
            {
                "session_id": session_id,
                "battle_rating": replay_br,
                "author": {"battle_rating": 9.3},
                "status": "success",
                "start_time": datetime(2026, 1, index + 1),
                "player.username": "Ranol",
                "player.country": "Germany",
                "player.team": 1,
                "player.battle_rating": player_br,
                "player.battle_rating_delta": -1.0,
                "player.tier_status": BattleRatingTier.UPTIER.value,
                "player.score": 1000 + index * 100,
            }
        )
        teammate_rows.append(
            {
                "session_id": session_id,
                "player.username": f"teammate-{index}",
                "player.team": 1,
                "player.score": 800,
            }
        )
    player_rows.append(
        {
            "session_id": "low-player-br-replay",
            "battle_rating": 14.7,
            "author": {"battle_rating": 9.3},
            "status": "success",
            "start_time": datetime(2026, 1, 3),
            "player.username": "Ranol",
            "player.country": "Germany",
            "player.team": 1,
            "player.battle_rating": 1.3,
            "player.battle_rating_delta": -13.4,
            "player.tier_status": BattleRatingTier.UPTIER.value,
            "player.score": 500,
        }
    )
    teammate_rows.append(
        {
            "session_id": "low-player-br-replay",
            "player.username": "teammate-low-br",
            "player.team": 1,
            "player.score": 800,
        }
    )

    player_df = pd.DataFrame(player_rows)
    global_df = pd.concat([player_df, pd.DataFrame(teammate_rows)], ignore_index=True)

    score_vs_br_module = importlib.import_module(
        "src.replay_data_explorer.graphs.player.scatter_score_vs_br"
    )

    score_vs_br = score_vs_br_module.create_scatter_score_vs_br(player_df, global_df)

    relative_score = create_scatter_score_vs_team_mean(player_df, global_df)
    tier_frequency = create_bar_tier_frequency_vs_br(player_df)
    score_heatmap = create_heatmap_score_by_country_and_br(player_df)
    winrate_heatmap = create_heatmap_winrate_by_country_and_br(player_df)
    br_delta_heatmap = create_heatmap_br_delta_by_country_and_br(player_df)

    assert score_vs_br.layout.xaxis.range == (1.15, 9.45)
    assert score_vs_br.layout.xaxis.title.text == "Player Battle Rating"
    assert relative_score.layout.xaxis.range == (1.15, 9.45)
    assert tier_frequency.layout.xaxis.range == (1.15, 9.45)
    assert list(score_vs_br.layout.xaxis.tickvals) == [1.3, 8.7, 9.3]
    assert list(score_vs_br.layout.xaxis.ticktext) == ["1.3", "8.7", "9.3"]
    score_hover_row = next(
        row
        for trace in score_vs_br.data
        if trace.customdata is not None
        for row in trace.customdata
        if row[6] == "session-1"
    )
    assert score_hover_row[2] == 9.3
    assert score_hover_row[3] == 10.3
    assert score_hover_row[4] == 800
    assert list(tier_frequency.layout.xaxis.tickvals) == [1.3, 8.7, 9.3]
    assert list(score_heatmap.data[0].x) == ["1.3", "8.7", "9.3"]
    assert score_heatmap.layout.xaxis.range == (-0.5, 2.5)
    assert list(winrate_heatmap.data[0].x) == ["1.3", "8.7", "9.3"]
    assert list(br_delta_heatmap.data[0].x) == ["1.3", "8.7", "9.3"]
