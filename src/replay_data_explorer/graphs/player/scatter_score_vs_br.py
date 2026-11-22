from src.replay_data_explorer.graphs.initialization import *


def create_scatter_score_vs_br(
    player_performance_df: pd.DataFrame,
    global_performance_df: Optional[pd.DataFrame] = None,
    *,
    player_name=None,
    country_filters=[],
    std_dev=None,
):
    """
    Create an interactive Plotly scatter plot of Score vs Battle Rating.

    Args:
        player_performance_df: DataFrame with performance data including tier status
        global_performance_df: Optional all-player data for team averages
        player_name: Optional player name for filtering
        country_filters: Optional list of Country enums for filtering
        std_dev: Optional standard deviation for outlier removal

    Returns:
        Plotly figure object
    """
    if player_performance_df.empty:
        print("No performance data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df, max_display_br = get_player_br_limited_graph_data(
        player_performance_df,
        [
            "session_id",
            "status",
            "start_time",
            "player.username",
            "player.country",
            "player.team",
            "player.tier_status",
            "player.score",
        ],
        battle_rating_column="player.battle_rating",
        require_valid_br_delta=True,
    )
    if df.empty or max_display_br is None:
        print("No data available within the replay battle-rating limit")
        return None

    # Load global performance data to calculate team averages
    global_df = global_performance_df
    if global_df is None:
        global_df = data_loaders.get_global_performance_data(country_filters)

    # Calculate team average score for each game (excluding the player)
    if not global_df.empty:
        team_avg_scores = []
        for idx, player_row in df.iterrows():
            session_id = player_row["session_id"]
            player_team = player_row["player.team"]
            player_username = player_row["player.username"]

            # Get all players on the same team in this session (excluding the player themselves)
            team_players = global_df[
                (global_df["session_id"] == session_id)
                & (global_df["player.team"] == player_team)
                & (global_df["player.username"] != player_username)
            ]

            if len(team_players) > 0:
                team_avg = team_players["player.score"].mean()
            else:
                team_avg = player_row["player.score"]  # Fallback if no teammates

            team_avg_scores.append(team_avg)

        df["team_avg_score"] = team_avg_scores
    else:
        df["team_avg_score"] = df["player.score"]  # Fallback if no global data

    # Remove outliers if specified
    if std_dev is not None:
        df = data_filterer.filter_outliers(df, "player.score", std_dev)

    outcome_symbols = PLOTLY_BATTLE_OUTCOME_SYMBOLS
    outcome_display_map = PLOTLY_BATTLE_OUTCOME_DISPLAY
    outcome_config = [
        (k, PLOTLY_BATTLE_OUTCOME_SYMBOLS[k], PLOTLY_BATTLE_OUTCOME_DISPLAY[k]) for k in PLOTLY_BATTLE_OUTCOME_ORDER
    ]

    # Create the interactive scatter plot
    fig = go.Figure()

    # One trace per tier — clicking a tier legend item filters all points of that tier.
    for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
        tier_data = df[df["player.tier_status"] == tier_status.value]
        if tier_data.empty:
            continue

        tier_status_display = battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(
            tier_status
        )

        # Per-point symbol encodes outcome
        symbols = tier_data["status"].map(outcome_symbols).fillna("circle").tolist()
        result_labels = tier_data["status"].map(outcome_display_map).fillna(tier_data["status"])

        custom_data = pd.DataFrame(
            {
                "username": tier_data["player.username"],
                "country": tier_data["player.country"],
                "player_battle_rating": tier_data["player.battle_rating"],
                "replay_battle_rating": tier_data["battle_rating"],
                "team_avg": tier_data["team_avg_score"],
                "start_time": tier_data["start_time"],
                "session_id": tier_data["session_id"],
                "result": result_labels,
            }
        )

        fig.add_trace(
            go.Scatter(
                x=tier_data["player.battle_rating"],
                y=tier_data["player.score"],
                mode="markers",
                name=tier_status_display,
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
                    + "Player BR: %{customdata[2]:.1f}<br>"
                    + "Replay Max BR: %{customdata[3]:.1f}<br>"
                    + "Tier: "
                    + tier_status_display
                    + "<br>"
                    + "Result: %{customdata[7]}<br>"
                    + "Score: %{y:.0f}<br>"
                    + "Team Avg: %{customdata[4]:.0f}<br>"
                    + "Date: %{customdata[5]}<br>"
                    + "Session: %{customdata[6]}<br><extra></extra>"
                ),
            )
        )

    # Shape key: one entry per outcome, no group title.
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

    # Add overall trend line
    if len(df) > 1:
        # Calculate overall trend line
        z = np.polyfit(df["player.battle_rating"], df["player.score"], 1)
        trend_line = np.poly1d(z)

        # Create trend line points
        br_range = np.linspace(df["player.battle_rating"].min(), df["player.battle_rating"].max(), 100)
        trend_y = trend_line(br_range)

        fig.add_trace(
            go.Scatter(
                x=br_range,
                y=trend_y,
                mode="lines",
                name=f"Overall Trend (slope: {z[0]:.1f})",
                line=dict(color=hex_to_rgba("#000000", PLOTLY_TRENDLINE_OPACITY), width=2, dash="dash"),
                hovertemplate="Overall Trend<br>Player BR: %{x:.1f}<br>Predicted Score: %{y:.0f}<extra></extra>",
                showlegend=True,
            )
        )

    # Add per-tier trend lines
    for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
        tier_data = df[df["player.tier_status"] == tier_status.value]
        tier_status_display = battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(
            tier_status
        )

        if len(tier_data) > 1:  # Need at least 2 points for a trend line
            try:
                # Calculate trend line for this tier
                z_tier = np.polyfit(tier_data["player.battle_rating"], tier_data["player.score"], 1)
                trend_line_tier = np.poly1d(z_tier)

                # Create trend line points for this tier's BR range
                tier_br_range = np.linspace(
                    tier_data["player.battle_rating"].min(), tier_data["player.battle_rating"].max(), 50
                )
                tier_trend_y = trend_line_tier(tier_br_range)

                # Use the same color as the tier but make it a solid line
                tier_color = PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier_status]

                fig.add_trace(
                    go.Scatter(
                        x=tier_br_range,
                        y=tier_trend_y,
                        mode="lines",
                        name=f"{tier_status_display} Trend ({z_tier[0]:.1f})",
                        line=dict(color=hex_to_rgba(tier_color, PLOTLY_TRENDLINE_OPACITY), width=1.5, dash="dot"),
                        hovertemplate=f"{tier_status_display} Trend<br>Player BR: %{{x}}<br>Predicted Score: %{{y:.0f}}<extra></extra>",
                        showlegend=True,
                        legendgroup=tier_status_display,  # Group with the scatter points
                        visible="legendonly",
                    )
                )
            except Exception as e:
                print(f"Could not calculate trend line for {tier_status_display}: {e}")
                continue

    # Build the graph's title
    title_filters = OrderedDict()
    if player_name:
        title_filters["Player"] = player_name
    title_filters["Replays"] = len(df)
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) else 'ies'}"] = ", ".join(
            [country.value for country in country_filters]
        )
    if std_dev is not None:
        title_filters["σ"] = str(std_dev)
    title = title_builder.build_title("Score vs Player Battle Rating with Tier", filters=title_filters)

    # Update the graph's layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(
            title="Player Battle Rating",
            **get_battle_rating_axis_options(df["player.battle_rating"]),
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False,
        ),
        yaxis=dict(title="Score", gridcolor="lightgray", gridwidth=1, zeroline=False),
        plot_bgcolor="white",
        width=get_graph_width(),
        height=600,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(r=150),  # Add right margin for legend
        hovermode="closest",
    )

    return fig
