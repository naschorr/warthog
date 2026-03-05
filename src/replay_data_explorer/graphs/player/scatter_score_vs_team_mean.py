from src.replay_data_explorer.graphs.initialization import *


def create_scatter_score_vs_team_mean(
    player_performance_df: pd.DataFrame,
    global_performance_df: pd.DataFrame,
    *,
    player_name: Optional[str] = None,
    country_filters: list = [],
):
    """
    Create an interactive Plotly scatter plot of relative player score vs Battle Rating.

    Each point represents a single battle plotted at the player's BR (x) and
    their score relative to their team's mean (y). Y = 0 is the team average;
    positive values mean the player outperformed their team.

    Args:
        player_performance_df: DataFrame with per-battle player performance data.
        global_performance_df: DataFrame with all-player performance data (used
            to compute team averages).
        player_name: Optional player name used in the graph title.
        country_filters: Optional list of Country enums for filtering.

    Returns:
        Plotly Figure object.
    """
    if player_performance_df.empty:
        print("No performance data available for plotting")
        return go.Figure()

    df = player_performance_df.copy()

    # --- Calculate team mean score (excluding the player) for each battle ----
    team_avg_scores = _calculate_team_avg_scores(df, global_performance_df)
    df["team_avg_score"] = team_avg_scores

    # Drop rows where we couldn't compute a team average
    df = df.dropna(subset=["team_avg_score"])

    if df.empty:
        print("No valid team average data available for plotting")
        return go.Figure()

    # Y axis: score relative to team mean (0 = team average)
    df["score_diff"] = df["player.score"] - df["team_avg_score"]

    # --- Build figure -------------------------------------------------------
    fig = go.Figure()

    outcome_config = [
        (k, PLOTLY_BATTLE_OUTCOME_SYMBOLS[k], PLOTLY_BATTLE_OUTCOME_DISPLAY[k]) for k in PLOTLY_BATTLE_OUTCOME_ORDER
    ]

    # Scatter traces per tier status
    for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
        tier_data = df[df["player.tier_status"] == tier_status]
        if tier_data.empty:
            continue

        tier_display = battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(
            tier_status
        )

        symbols = tier_data["status"].map(PLOTLY_BATTLE_OUTCOME_SYMBOLS).fillna("circle").tolist()
        result_labels = tier_data["status"].map(PLOTLY_BATTLE_OUTCOME_DISPLAY).fillna(tier_data["status"])

        custom_data = pd.DataFrame(
            {
                "username": tier_data["player.username"],
                "country": tier_data["player.country"],
                "battle_rating": tier_data["player.battle_rating"],
                "player_score": tier_data["player.score"],
                "team_avg": tier_data["team_avg_score"],
                "score_diff": tier_data["score_diff"],
                "start_time": tier_data["start_time"],
                "result": result_labels,
            }
        )

        fig.add_trace(
            go.Scatter(
                x=tier_data["player.battle_rating"],
                y=tier_data["score_diff"],
                mode="markers",
                name=tier_display,
                marker=dict(
                    color=PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier_status],
                    symbol=symbols,
                    size=8,
                    line=dict(width=1, color="white"),
                    opacity=0.7,
                ),
                customdata=custom_data.values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    + "Country: %{customdata[1]}<br>"
                    + "BR: %{customdata[2]}<br>"
                    + "Tier: "
                    + tier_display
                    + "<br>"
                    + "Result: %{customdata[7]}<br>"
                    + "Player Score: %{customdata[3]:.0f}<br>"
                    + "Team Mean: %{customdata[4]:.0f}<br>"
                    + "Difference: %{customdata[5]:+.0f}<br>"
                    + "Date: %{customdata[6]}<br>"
                    + "<extra></extra>"
                ),
            )
        )

    # Shape key entries (no group title)
    for status_key, symbol, status_name in outcome_config:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                name=status_name,
                legendgroup=f"outcome_{status_key}",
                marker=dict(symbol=symbol, color="gray", size=8, line=dict(width=1, color="white")),
                showlegend=True,
                hoverinfo="skip",
            )
        )

    # --- Title --------------------------------------------------------------
    title_filters: OrderedDict[str, str | None] = OrderedDict()
    if player_name:
        title_filters["Player"] = player_name
    title_filters["Replays"] = str(len(df))
    if country_filters:
        label = "Country" if len(country_filters) == 1 else "Countries"
        title_filters[label] = ", ".join(c.value for c in country_filters)

    title = title_builder.build_title("Score vs Battle Rating (Relative to Team Mean)", filters=title_filters)

    # --- Layout -------------------------------------------------------------
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(
            title="Battle Rating",
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False,
        ),
        yaxis=dict(
            title="Score Relative to Team Mean",
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=True,
            zerolinecolor="gray",
            zerolinewidth=1.5,
        ),
        plot_bgcolor="white",
        width=get_graph_width(),
        height=600,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(r=150),
        hovermode="closest",
    )

    return fig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _calculate_team_avg_scores(player_df: pd.DataFrame, global_df: pd.DataFrame) -> list[float | None]:
    """Return a list of team-mean scores aligned with *player_df* rows.

    For each battle the player participated in, the mean score of all
    *other* players on the same team is computed from *global_df*.  If no
    teammates are found the value is ``None``.
    """
    if global_df.empty:
        return [None] * len(player_df)

    team_avg_scores: list[float | None] = []

    for _, row in player_df.iterrows():
        session_id = row["session_id"]
        player_team = row["player.team"]
        player_username = row["player.username"]

        teammates = global_df.loc[
            (global_df["session_id"] == session_id)
            & (global_df["player.team"] == player_team)
            & (global_df["player.username"] != player_username)
        ]

        if len(teammates) > 0:
            team_avg_scores.append(float(teammates["player.score"].mean()))
        else:
            team_avg_scores.append(None)

    return team_avg_scores
