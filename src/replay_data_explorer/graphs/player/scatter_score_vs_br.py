from src.replay_data_explorer.graphs.initialization import *


def create_scatter_score_vs_br(
    player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[], std_dev=None
):
    """
    Create an interactive Plotly scatter plot of Score vs Battle Rating.

    Args:
        player_performance_df: DataFrame with performance data including tier status
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
    df = player_performance_df.copy()

    # Remove outliers if specified
    if std_dev is not None:
        df = data_filterer.filter_outliers(df, "player.score", std_dev)

    # Create the interactive scatter plot
    fig = go.Figure()

    # Add scatter traces for each tier status
    for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
        tier_data = df[df["player.tier_status"] == tier_status]
        if not tier_data.empty:
            # Get matching indices for the current tier data
            tier_status_name = BATTLE_RATING_TIER_NAMES[tier_status]

            # Prepare custom data with all the hover information
            custom_data = pd.DataFrame(
                {
                    "username": tier_data["player.username"],
                    "country": tier_data["player.country"],
                    "battle_rating": tier_data["battle_rating"],
                    "start_time": tier_data["start_time"],
                    "session_id": tier_data["session_id"],
                }
            )

            fig.add_trace(
                go.Scatter(
                    x=tier_data["player.battle_rating"],
                    y=tier_data["player.score"],
                    mode="markers",
                    name=tier_status_name,
                    marker=dict(
                        color=PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier_status],
                        size=8,
                        line=dict(width=1, color="white"),
                        opacity=0.7,
                    ),
                    customdata=custom_data.values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        + "Country: %{customdata[1]}<br>"
                        + "BR: %{customdata[2]}<br>"
                        + "Tier Status: "
                        + tier_status_name
                        + "<br>"
                        + "Score: %{y}<br>"
                        + "Date: %{customdata[3]}<br>"
                        + "Session: %{customdata[4]}<br><extra></extra>"
                    ),
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
                hovertemplate="Overall Trend<br>BR: %{x:.1f}<br>Predicted Score: %{y:.0f}<extra></extra>",
                showlegend=True,
            )
        )

    # Add per-tier trend lines
    for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
        tier_data = df[df["player.tier_status"] == tier_status]
        tier_status_name = BATTLE_RATING_TIER_NAMES[tier_status]
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
                        name=f"{tier_status_name} Trend ({z_tier[0]:.1f})",
                        line=dict(color=hex_to_rgba(tier_color, PLOTLY_TRENDLINE_OPACITY), width=1.5, dash="dot"),
                        hovertemplate=f"{tier_status_name} Trend<br>BR: %{{x}}<br>Predicted Score: %{{y:.0f}}<extra></extra>",
                        showlegend=True,
                        legendgroup=tier_status_name,  # Group with the scatter points
                        visible="legendonly",
                    )
                )
            except Exception as e:
                print(f"Could not calculate trend line for {tier_status_name}: {e}")
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
    title = title_builder.build_title("Score vs Battle Rating with Tier", filters=title_filters)

    # Update the graph's layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Battle Rating", gridcolor="lightgray", gridwidth=1, zeroline=False),
        yaxis=dict(title="Score", gridcolor="lightgray", gridwidth=1, zeroline=False),
        plot_bgcolor="white",
        width=1000,
        height=600,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(r=150),  # Add right margin for legend
        hovermode="closest",
    )

    return fig
