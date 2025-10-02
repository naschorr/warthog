from src.replay_data_explorer.graphs.squad.common.squad_flavor import add_squad_flavor_column, SquadFlavor
from src.replay_data_explorer.graphs.initialization import *


def create_bar_squad_performance(
    global_performance_df: pd.DataFrame, *, player_name, display_player_name=None, country_filters=[]
):
    """
    Create an interactive Plotly bar chart showing average player score by squad size.

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

    # Calculate average score by squad flavor
    squad_performance = df.groupby("squad_flavor").agg({"player.score": ["mean", "count", "std"]}).round(1)

    # Flatten column names
    squad_performance.columns = ["avg_score", "battle_count", "std_dev"]

    # Create ordered list of squad flavors for consistent display
    squad_flavor_order = [flavor.value for flavor in SquadFlavor]
    available_flavors = [flavor for flavor in squad_flavor_order if flavor in squad_performance.index]

    if not available_flavors:
        print("No squad flavors found in data")
        return None

    # Reorder the data to match the desired order
    ordered_performance = squad_performance.reindex(available_flavors)

    # Create the bar chart
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=available_flavors,
            y=ordered_performance["avg_score"],
            name="Mean Score",
            marker=dict(color=PLOTLY_SINGLE_COLOR, line=dict(color="white", width=1)),
            text=ordered_performance["avg_score"],
            textposition="outside",
            texttemplate="%{text:.0f}",
            customdata=list(zip(ordered_performance["battle_count"], ordered_performance["std_dev"])),
            hovertemplate=(
                "<b>%{x}</b><br>"
                + "Mean Score: %{y:.0f}<br>"
                + "Battles: %{customdata[0]}<br>"
                + "Std Dev: %{customdata[1]:.1f}<br>"
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
    title = title_builder.build_title("Mean Score by Squad Type", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Squad Type", gridcolor="lightgray", gridwidth=1, type="category"),
        yaxis=dict(title="Mean Score", gridcolor="lightgray", gridwidth=1, zeroline=False),
        width=800,
        height=500,
        plot_bgcolor="white",
        showlegend=False,
    )

    # Add battle count annotations
    for squad_flavor in available_flavors:
        row = ordered_performance.loc[squad_flavor]
        fig.add_annotation(
            x=squad_flavor,
            y=row["avg_score"] - (row["avg_score"] * 0.05),  # Position slightly below top of bar
            text=f"{int(row['battle_count'])} battle{'s' if row['battle_count'] != 1 else ''}",
            showarrow=False,
            font=dict(size=10, color="white"),
            xanchor="center",
        )

    return fig
