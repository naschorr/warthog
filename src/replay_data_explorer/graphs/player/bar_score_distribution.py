from src.replay_data_explorer.graphs.initialization import *


def create_bar_score_distribution(player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]):
    """
    Create an interactive Plotly stacked bar chart showing score distribution by battle outcome.

    Args:
        player_performance_df: DataFrame with performance data including tier status
        player_name: Optional player name for filtering
        country_filters: Optional list of Country enums for filtering

    Returns:
        Plotly figure object
    """
    if player_performance_df.empty:
        print("No performance data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = player_performance_df.copy()

    # Create score bins
    min_score = 0
    max_score = df["player.score"].max()
    bin_width = 100  # Steps of 100 score

    # Create bin edges
    bin_edges = list(range(int(min_score), int(max_score) + bin_width, bin_width))
    if len(bin_edges) < 2:
        bin_edges = [int(min_score), int(max_score) + 1]

    # Create the figure
    fig = go.Figure()

    # Define status order for stacking (bottom to top in the order they're added)
    status_order = ["left", "fail", "success"]

    # Map status values to display names and conclusion colors
    status_mapping = {"success": "Victory", "fail": "Defeat", "left": "Left"}

    # Map status to conclusion color keys
    status_color_mapping = {
        "success": "good",  # Victory -> green
        "fail": "bad",  # Defeat -> red
        "left": "neutral",  # Left -> gray
    }

    # Add stacked bars for each status
    for status in status_order:
        status_data = df[df["status"] == status]
        if not status_data.empty:
            hist_counts, _ = np.histogram(status_data["player.score"], bins=bin_edges)

            # Create bin centers for x-axis
            bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]

            # Get the appropriate color
            color_key = status_color_mapping.get(status, "neutral")
            color = PLOTLY_CONCLUSION_COLORS.get(color_key, "#888888")

            fig.add_trace(
                go.Bar(
                    x=bin_centers,
                    y=hist_counts,
                    name=status_mapping.get(status, status.title()),
                    marker=dict(color=color, opacity=0.8, line=dict(color="white", width=1)),
                    width=bin_width * 0.8,
                    hovertemplate=f"<b>{status_mapping.get(status, status.title())}</b><br>"
                    + "Score Range: %{x}±"
                    + f"{bin_width//2}<br>"
                    + "Count: %{y}<extra></extra>",
                )
            )

    # Calculate overall statistics
    mean_score = df["player.score"].mean()
    median_score = df["player.score"].median()
    std_score = df["player.score"].std()

    # Determine annotation positions to avoid overlap
    # If mean and median are close (within 5% of the range), offset them
    score_range = max_score - min_score
    values_close = abs(mean_score - median_score) < (score_range * 0.05)

    if values_close:
        # Position mean annotation higher and median lower
        mean_position = "top"
        median_position = "bottom"
        mean_y_offset = 10  # Pixels above the line
        median_y_offset = -10  # Pixels below the line
    else:
        # Use default positioning
        mean_position = "top"
        median_position = "top"
        mean_y_offset = 0
        median_y_offset = 0

    # Add mean line with offset annotation
    fig.add_vline(
        x=mean_score,
        line_dash="dot",
        line_color="black",
        annotation_text=f"Mean: {mean_score:.0f}",
        annotation_position=mean_position,
        annotation=dict(
            yshift=mean_y_offset,
        ),
    )

    # Add median line with offset annotation
    fig.add_vline(
        x=median_score,
        line_dash="dash",
        line_color="black",
        annotation_text=f"Median: {median_score:.0f}",
        annotation_position=median_position,
        annotation=dict(yshift=median_y_offset),
    )

    # Build title with filters
    title_filters = OrderedDict()
    if player_name:
        title_filters["Player"] = player_name
    if country_filters:
        country_names = [country.value for country in country_filters]
        title_filters["Countries"] = ", ".join(country_names)
    title_filters["Replays"] = len(df)
    title = title_builder.build_title("Score Distribution by Battle Outcome", filters=title_filters)

    # Add statistics text
    stats_text = (
        f"Mean: {mean_score:.0f}<br>"
        f"Median: {median_score:.0f}<br>"
        f"Std Dev: {std_score:.0f}<br>"
        f"Min: {df['player.score'].min()}<br>"
        f"Max: {df['player.score'].max()}<br><br>"
        f"<b>Battle Outcomes:</b><br>"
    )

    # Calculate status counts for statistics (show in logical order)
    status_counts = df["status"].value_counts()

    for status in reversed(status_order):
        if status in status_counts:
            status_name = status_mapping.get(status, status.title())
            count = status_counts[status]
            percentage = (count / len(df)) * 100
            stats_text += f"{status_name}: {count} ({percentage:.1f}%)<br>"

    fig.add_annotation(
        x=0.98,
        y=0.98,
        xref="paper",
        yref="paper",
        text=stats_text,
        showarrow=False,
        align="left",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="gray",
        borderwidth=1,
        font=dict(size=12),
    )

    # Update layout
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16)),
        xaxis=dict(title="Score", gridcolor="lightgray", gridwidth=1, zeroline=False),
        yaxis=dict(title="Frequency", gridcolor="lightgray", gridwidth=1, zeroline=False),
        plot_bgcolor="white",
        width=1000,
        height=600,
        barmode="stack",  # Enable stacking
        hovermode="closest",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            # Reverse the legend order to match visual stacking (top item first)
            traceorder="reversed",
        ),
        margin=dict(r=150),  # Add right margin for legend
    )

    return fig
