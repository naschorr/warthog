from src.replay_data_explorer.graphs.squad.common.squad_flavor import add_squad_flavor_column, SquadFlavor
from src.replay_data_explorer.graphs.initialization import *


def create_bar_squad_win_rate(player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]):
    """
    Create an interactive Plotly stacked bar chart showing win rates by squad type.
    Shows victory, loss, and left percentages for each squad type.

    Args:
        player_performance_df: DataFrame with performance data (should include squad, team, auto_squad, status columns)
        player_name: Optional player name for title
        country_filters: List of countries to filter by

    Returns:
        Plotly figure object
    """
    if player_performance_df.empty:
        print("No data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = player_performance_df.copy()

    # Apply squad flavor determination with session-based grouping
    df = add_squad_flavor_column(df)

    # Filter for the specific player if provided
    if player_name:
        df = df[df["player.username"] == player_name]

    if df.empty:
        print("No data available after filtering")
        return None

    # Get available squad types using enum order
    squad_flavor_order = [flavor.value for flavor in SquadFlavor]
    available_squad_types = [flavor for flavor in squad_flavor_order]

    if len(available_squad_types) == 0:
        print("No squad types found in data")
        return None

    # Status order for stacking and colors (using same logic as score distribution graph)
    status_order = ["success", "fail", "left"]
    status_colors = {
        "left": PLOTLY_CONCLUSION_COLORS["neutral"],
        "fail": PLOTLY_CONCLUSION_COLORS["bad"],
        "success": PLOTLY_CONCLUSION_COLORS["good"],
    }
    status_names = {"left": "Left Early", "fail": "Loss", "success": "Victory"}

    # Calculate win rate percentages for each squad type
    squad_data = []
    for squad_type in available_squad_types:
        squad_battles = df[df["squad_flavor"] == squad_type]
        status_counts = pd.Series(squad_battles["status"]).value_counts()
        total_battles = len(squad_battles)

        # Calculate percentages for each status
        percentages = {}
        for status in status_order:
            count = status_counts.get(status) or 0
            percentage = (count / total_battles) * 100 if total_battles > 0 else 0
            percentages[status] = {"percentage": percentage, "count": count}

        squad_data.append({"squad_type": squad_type, "percentages": percentages, "total_battles": total_battles})

    # Create the stacked bar chart
    fig = go.Figure()

    # Add a bar for each status
    for status in reversed(status_order):  # Reverse to stack correctly
        status_name = status_names[status]

        squad_types = [data["squad_type"] for data in squad_data]
        percentages = [data["percentages"][status]["percentage"] for data in squad_data]
        counts = [data["percentages"][status]["count"] for data in squad_data]
        totals = [data["total_battles"] for data in squad_data]

        # Only add bars that have data
        if any(p > 0 for p in percentages):
            fig.add_trace(
                go.Bar(
                    name=status_name,
                    x=squad_types,
                    y=percentages,
                    text=[f"{p:.1f}%" if p > 5 else "" for p in percentages],  # Only show text if percentage > 5%
                    textposition="inside",
                    textfont=dict(color="white", size=10, family="Arial"),
                    marker_color=status_colors[status],
                    customdata=list(zip(counts, totals)),
                    hovertemplate=(
                        f"<b>{status_name}</b><br>"
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
    total_battles = sum(data["total_battles"] for data in squad_data)
    title_filters["Battles"] = str(total_battles)
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [c.value for c in country_filters]
        )
    title = title_builder.build_title("Win Rate by Squad Type", filters=title_filters)

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
