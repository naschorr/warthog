from src.replay_data_explorer.graphs.initialization import *


def create_bar_score_vs_map(player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]):
    """
    Create an interactive Plotly bar chart showing mean scores by map.

    Args:
        player_performance_df: DataFrame with performance data
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

    # Get unique maps
    available_maps = sorted(df["level"].unique())

    if len(available_maps) == 0:
        print("Insufficient data for bar chart")
        return None

    # Transform map names: remove "avg_" prefix, split on underscores, and capitalize
    def transform_map_name(map_name):
        # Remove "avg_" prefix if present
        cleaned_name = map_name.replace("avg_", "", 1) if map_name.startswith("avg_") else map_name
        # Split on underscores and capitalize each part
        parts = cleaned_name.split("_")
        # Minor formatting for conditions
        if parts[-1] == "snow":
            parts[-1] = f"({parts[-1]})"
        return " ".join(part.capitalize() for part in parts)

    # Apply transformation to map names
    df["level_display"] = df["level"].apply(transform_map_name)

    # Aggregate data by map to calculate mean scores and battle counts
    map_stats = df.groupby(["level", "level_display"])["player.score"].agg(["mean", "count", "std"]).reset_index()
    map_stats = map_stats.sort_values("mean", ascending=True)  # Sort by mean score for better visualization

    # Create the horizontal bar chart
    fig = go.Figure(
        data=go.Bar(
            x=map_stats["mean"],
            y=map_stats["level_display"],
            orientation="h",  # Horizontal bars
            width=0.6,  # Make bars thinner
            marker=dict(
                color=PLOTLY_SINGLE_COLOR,  # Use project's standard single color
                line=dict(color="white", width=1),
            ),
            hovertemplate="<b>%{y}</b><br>"
            + "Mean Score: %{x:.0f}<br>"
            + "Battles: %{customdata[0]}<br>"
            + "Std Dev: %{customdata[1]:.1f}<extra></extra>",
            customdata=list(zip(map_stats["count"], map_stats["std"])),
        )
    )

    # Calculate overall statistics
    mean_score = df["player.score"].mean()
    median_score = df["player.score"].median()

    # Determine annotation positions to avoid overlap
    if mean_score < median_score:
        mean_position = "top left"
        median_position = "top right"
    else:
        mean_position = "top right"
        median_position = "top left"

    # Add mean line
    fig.add_vline(
        x=mean_score,
        line_dash="dot",
        line_color="black",
        annotation_text=f"Overall Mean: {mean_score:.0f}",
        annotation_position=mean_position,
        annotation=dict(yshift=15),  # Move annotation up from the line
    )

    # Add median line
    fig.add_vline(
        x=median_score,
        line_dash="dash",
        line_color="black",
        annotation_text=f"Overall Median: {median_score:.0f}",
        annotation_position=median_position,
        annotation=dict(yshift=15),  # Move annotation up from the line
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
    title = title_builder.build_title("Mean Score by Map", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(
            title="Mean Score",
            side="bottom",
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False,
        ),
        yaxis=dict(
            title="Map",
            side="left",
            gridcolor="lightgray",
            gridwidth=1,
        ),
        width=800,
        height=max(400, len(available_maps) * 30),  # Dynamic height based on map count
        plot_bgcolor="white",
        margin=dict(l=150, r=80, t=80, b=100),  # Extra left margin for map names
        hovermode="closest",
    )

    return fig
