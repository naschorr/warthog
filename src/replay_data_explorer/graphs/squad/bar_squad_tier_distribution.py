from src.replay_data_explorer.graphs.squad.common.squad_flavor import add_squad_flavor_column, SquadFlavor
from src.replay_data_explorer.graphs.initialization import *


def create_bar_squad_tier_distribution(player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]):
    """
    Create an interactive Plotly stacked bar chart showing battle tier rating percentages by squad type.

    Args:
        player_performance_df: DataFrame with performance data including tier status (should include squad, team, auto_squad columns)
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

    # Apply squad flavor determination with session-based grouping
    df = add_squad_flavor_column(df)

    # Filter for the specific player if provided
    if player_name:
        df = df[df["player.username"] == player_name]

    # Get available squad types using enum order
    squad_flavor_order = [flavor.value for flavor in SquadFlavor]
    unique_flavors = pd.Series(df["squad_flavor"]).unique()
    available_squad_types = [flavor for flavor in squad_flavor_order if flavor in unique_flavors]

    if len(available_squad_types) == 0:
        print("No squad types found in data")
        return None

    # Calculate tier percentages for each squad type
    squad_tier_data = []
    for squad_type in available_squad_types:
        squad_data = df[df["squad_flavor"] == squad_type]
        tier_counts = pd.Series(squad_data["player.tier_status"]).value_counts()
        total_battles = len(squad_data)

        # Calculate percentages for each tier
        tier_percentages = {}
        for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
            tier_status_name = BATTLE_RATING_TIER_NAMES[tier_status]
            count = tier_counts.get(tier_status) or 0
            percentage = (count / total_battles) * 100 if total_battles > 0 else 0
            tier_percentages[tier_status_name] = {"percentage": percentage, "count": count, "total": total_battles}

        squad_tier_data.append(
            {"squad_type": squad_type, "tier_percentages": tier_percentages, "total_battles": total_battles}
        )

    # Create the stacked bar chart
    fig = go.Figure()

    # Add a bar for each tier status
    for tier_status in reversed(PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER):
        tier_status_name = BATTLE_RATING_TIER_NAMES[tier_status]

        squad_types = [data["squad_type"] for data in squad_tier_data]
        percentages = [data["tier_percentages"][tier_status_name]["percentage"] for data in squad_tier_data]
        counts = [data["tier_percentages"][tier_status_name]["count"] for data in squad_tier_data]
        totals = [data["total_battles"] for data in squad_tier_data]

        # Only add bars that have data
        if any(p > 0 for p in percentages):
            fig.add_trace(
                go.Bar(
                    name=tier_status_name,
                    x=squad_types,
                    y=percentages,
                    text=[str(count) if count > 0 else "" for count in counts],
                    textposition="inside",
                    textfont=dict(color="white", size=10),
                    marker_color=PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier_status],
                    customdata=list(zip(counts, totals)),
                    hovertemplate=(
                        f"<b>{tier_status_name}</b><br>"
                        + "Squad Type: %{x}<br>"
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
    total_battles = sum(data["total_battles"] for data in squad_tier_data)
    title_filters["Battles"] = str(total_battles)
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [c.value for c in country_filters]
        )
    title = title_builder.build_title("Battle Rating Tier Frequency by Squad Type", filters=title_filters)

    # Update layout for stacked bar chart
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Squad Type", tickangle=0),
        yaxis=dict(title="Percentage (%)", range=[0, 100]),
        barmode="stack",
        width=800,
        height=600,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(r=150),  # Add right margin for legend
        bargap=0.1,
    )

    return fig
