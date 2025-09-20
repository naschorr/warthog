from src.replay_data_explorer.graphs.initialization import *


def create_bar_tier_frequency_vs_br(player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]):
    """
    Create an interactive Plotly stacked bar chart showing tier frequency percentages by battle rating.

    Args:
        player_performance_df: DataFrame with performance data including tier status
        player_name: Optional player name for title
        country_filters: List of countries to filter by

    Returns:
        Plotly figure object
    """
    if player_performance_df.empty:
        print("No performance data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = player_performance_df.copy()

    # Get available battle ratings
    available_brs = sorted(df["player.battle_rating"].unique())

    # Calculate tier percentages for each battle rating
    br_tier_data = []
    for br in available_brs:
        br_data = df[df["player.battle_rating"] == br]
        tier_counts = pd.Series(br_data["player.tier_status"]).value_counts()
        total_battles = len(br_data)

        # Calculate percentages for each tier
        tier_percentages = {}
        for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
            count = tier_counts.get(tier_status) or 0
            percentage = (count / total_battles) * 100 if total_battles > 0 else 0
            tier_percentages[tier_status] = {"percentage": percentage, "count": count, "total": total_battles}

        br_tier_data.append({"battle_rating": br, "tier_percentages": tier_percentages, "total_battles": total_battles})

    # Create the stacked bar chart
    fig = go.Figure()

    # Add a bar for each tier status
    for tier_status in reversed(PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER):
        tier_status_display = battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(
            tier_status
        )
        battle_ratings = [data["battle_rating"] for data in br_tier_data]
        percentages = [data["tier_percentages"][tier_status]["percentage"] for data in br_tier_data]
        counts = [data["tier_percentages"][tier_status]["count"] for data in br_tier_data]
        totals = [data["total_battles"] for data in br_tier_data]

        # Only add bars that have data
        if any(p > 0 for p in percentages):
            fig.add_trace(
                go.Bar(
                    name=tier_status_display,
                    x=battle_ratings,
                    y=percentages,
                    text=[str(count) if count > 0 else "" for count in counts],
                    textposition="inside",
                    textfont=dict(color="white", size=9),
                    marker_color=PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier_status],
                    customdata=list(zip(counts, totals)),
                    hovertemplate=(
                        f"<b>{tier_status_display}</b><br>"
                        + "Battle Rating: %{x}<br>"
                        + "Percentage: %{y:.1f}%<br>"
                        + "Count: %{customdata[0]}<br>"
                        + "Total Battles: %{customdata[1]}<br>"
                        + "<extra></extra>"
                    ),
                )
            )

    # Build the graph's title
    title_filters = OrderedDict()
    if player_name:
        title_filters["Player"] = player_name
    total_battles = sum(data["total_battles"] for data in br_tier_data)
    title_filters["Battles"] = total_battles
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [country.value for country in country_filters]
        )
    title = title_builder.build_title("Tier Frequency by Battle Rating", filters=title_filters)

    # Update layout for stacked bar chart
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(
            title="Battle Rating",
            tickangle=45 if len(available_brs) > 10 else 0,
            tickvals=available_brs,
            ticktext=[f"{br:.1f}" for br in available_brs],
        ),
        yaxis=dict(title="Percentage (%)", range=[0, 100]),
        barmode="stack",
        width=1000,
        height=600,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(r=150, b=100),  # Add margins for legend and BR labels
        plot_bgcolor="white",
    )

    return fig
