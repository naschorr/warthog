from src.replay_data_explorer.graphs.initialization import *


def create_pie_tier_frequency(player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]):
    """
    Create an interactive Plotly pie chart showing the frequency of each battle rating tier.

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

    # Count the frequency of each tier status
    tier_counts = df["player.tier_status"].value_counts()

    # Ensure all tier statuses are represented (with 0 counts if necessary)
    all_tier_counts = {}
    for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
        count = tier_counts.get(tier_status, 0)
        all_tier_counts[tier_status] = count

    # Filter out zero counts for cleaner visualization
    filtered_tier_counts = {k: v for k, v in all_tier_counts.items() if v > 0}

    if not filtered_tier_counts:
        print("No tier data found after filtering")
        return None

    # Create lists for the pie chart
    labels = [
        battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(filtered_tier_count)
        for filtered_tier_count in filtered_tier_counts
    ]
    values = list(filtered_tier_counts.values())

    # Map colors to the labels
    colors = []
    for label in labels:
        for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
            tier_status_display = (
                battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(tier_status)
            )
            if tier_status_display == label:
                colors.append(PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier_status])
                break

    # Create the pie chart
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.3,  # Creates a donut chart
                marker=dict(colors=colors, line=dict(color="white", width=2)),
                textinfo="label+percent+value",
                texttemplate="<b>%{label}</b><br>%{percent}<br>%{value} battles",
                textposition="auto",  # Automatically position text to avoid overlap
                insidetextorientation="horizontal",  # Keep text horizontal, not angled
                insidetextfont=dict(size=12, color="white"),  # White text inside sectors
                outsidetextfont=dict(size=12, color="black"),  # Dark text outside sectors
                hovertemplate="<b>%{label}</b><br>"
                + "Count: %{value}<br>"
                + "Percentage: %{percent}<br>"
                + "<extra></extra>",
            )
        ]
    )

    # Build the graph's title
    title_filters = OrderedDict()
    if player_name:
        title_filters["Player"] = player_name
    title_filters["Battles"] = len(df)
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [country.value for country in country_filters]
        )
    title = title_builder.build_title("Battle Rating Tier Frequency", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        width=800,
        height=600,
        showlegend=False,
        plot_bgcolor="white",
    )

    return fig
