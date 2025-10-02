from src.replay_data_explorer.graphs.squad.common.squad_flavor import add_squad_flavor_column, SquadFlavor
from src.replay_data_explorer.graphs.initialization import *


def create_bar_squad_br_delta(
    global_performance_df: pd.DataFrame, *, player_name, display_player_name=None, country_filters=[]
):
    """
    Create an interactive Plotly bar chart showing average battle rating delta by squad size.

    Args:
        global_performance_df: DataFrame with performance data (should include squad, team, auto_squad columns)
        player_name: Optional player name for title
        country_filters: List of countries to filter by

    Returns:
        Plotly figure object
    """
    if global_performance_df.empty:
        print("No performance data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = global_performance_df.copy()

    # Apply squad flavor determination with session-based grouping
    df = add_squad_flavor_column(df)
    df = df[df["player.username"] == player_name]

    # Check if we have any data after filtering
    if df.empty:
        print(f"No data available for player {player_name}")
        return None

    # Calculate average BR delta by squad flavor
    squad_br_delta = df.groupby("squad_flavor").agg({"player.battle_rating_delta": ["mean", "count", "std"]}).round(3)

    # Flatten column names
    squad_br_delta.columns = ["avg_br_delta", "battle_count", "std_dev"]

    # Create ordered list of squad flavors for consistent display
    squad_flavor_order = [flavor.value for flavor in SquadFlavor]
    available_flavors = [flavor for flavor in squad_flavor_order if flavor in squad_br_delta.index]

    if not available_flavors:
        print("No squad flavors found in data")
        return None

    # Reorder the data to match the desired order
    ordered_br_delta = squad_br_delta.reindex(available_flavors)

    # Create the bar chart
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=available_flavors,
            y=ordered_br_delta["avg_br_delta"],
            name="Mean BR Delta",
            marker=dict(color=PLOTLY_SINGLE_COLOR, line=dict(color="white", width=1)),
            text=ordered_br_delta["avg_br_delta"],
            textposition="outside",
            texttemplate="%{text:.3f}",
            customdata=list(zip(ordered_br_delta["battle_count"], ordered_br_delta["std_dev"])),
            hovertemplate=(
                "<b>%{x}</b><br>"
                + "Mean BR Delta: %{y:.3f}<br>"
                + "Battles: %{customdata[0]}<br>"
                + "Std Dev: %{customdata[1]:.3f}<br>"
                + "<extra></extra>"
            ),
        )
    )

    # Build the graph's title
    title_filters = OrderedDict()
    if player_name and not display_player_name:
        title_filters["Player"] = player_name
    elif player_name and display_player_name:
        title_filters["Player"] = display_player_name
    title_filters["Battles"] = len(df)
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [c.value for c in country_filters]
        )
    title = title_builder.build_title("Mean BR Delta by Squad Type", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Squad Type", gridcolor="lightgray", gridwidth=1, type="category"),
        yaxis=dict(
            title="Mean BR Delta",
            gridcolor="lightgray",
            gridwidth=1,
        ),
        width=800,
        height=500,
        plot_bgcolor="white",
        showlegend=False,
    )

    # Add battle count annotations inside bars at the bottom
    for squad_flavor in available_flavors:
        row = ordered_br_delta.loc[squad_flavor]
        # Position annotation at the bottom of the bar (closer to zero)
        if row["avg_br_delta"] >= 0:
            y_position = 0.02  # Slightly above zero for positive bars
        else:
            y_position = row["avg_br_delta"] + 0.02  # Near the bottom of negative bars

        fig.add_annotation(
            x=squad_flavor,
            y=y_position,
            text=f"{int(row['battle_count'])} battle{'s' if row['battle_count'] != 1 else ''}",
            showarrow=False,
            font=dict(size=10, color="white"),
            xanchor="center",
        )

    return fig
