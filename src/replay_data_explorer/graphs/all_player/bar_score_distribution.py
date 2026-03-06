from src.replay_data_explorer.graphs.initialization import *


def create_all_player_bar_score_distribution(
    global_performance_df: pd.DataFrame,
    *,
    author_name: Optional[str] = None,
    country_filters: list = [],
):
    """
    Create an interactive Plotly bar chart showing the score distribution across all players.

    Each bar represents a score bin and its height is the total number of battles
    falling in that range. Mean and median lines are overlaid. No outcome stacking —
    this shows the overall population distribution.

    Args:
        global_performance_df: DataFrame with all-player performance data.
        author_name: Optional name used in the graph title.
        country_filters: Optional list of Country enums for filtering.

    Returns:
        Plotly Figure object.
    """
    if global_performance_df.empty:
        print("No performance data available for plotting")
        return go.Figure()

    df = global_performance_df.copy()

    # --- Score bins ---------------------------------------------------------
    bin_width = 100
    min_score = 0
    max_score = df["player.score"].max()

    bin_edges = list(range(int(min_score), int(max_score) + bin_width, bin_width))
    if len(bin_edges) < 2:
        bin_edges = [int(min_score), int(max_score) + 1]

    hist_counts, _ = np.histogram(df["player.score"], bins=bin_edges)
    bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]

    # --- Figure -------------------------------------------------------------
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=bin_centers,
            y=hist_counts,
            name="All Players",
            marker=dict(
                color=PLOTLY_SINGLE_COLOR,
                opacity=0.8,
                line=dict(color="white", width=1),
            ),
            width=bin_width * 0.8,
            hovertemplate="Score Range: %{x:.0f}±" + f"{bin_width // 2}<br>" + "Count: %{y}<extra></extra>",
        )
    )

    # --- Statistics lines ---------------------------------------------------
    mean_score = df["player.score"].mean()
    median_score = df["player.score"].median()
    std_score = df["player.score"].std()

    fig.add_vline(
        x=mean_score,
        line_dash="dot",
        line_color="black",
        annotation_text=f"Mean: {mean_score:.0f}",
        annotation_position="top",
    )
    fig.add_vline(
        x=median_score,
        line_dash="dash",
        line_color="black",
    )
    fig.add_annotation(
        x=median_score,
        y=-0.1,
        xref="x",
        yref="paper",
        text=f"Median: {median_score:.0f}",
        showarrow=False,
        font=dict(size=12),
    )

    # --- Stats annotation box -----------------------------------------------
    unique_players = df["player.username"].nunique()
    total_battles = len(df)

    stats_text = (
        f"Mean: {mean_score:.0f}<br>"
        f"Median: {median_score:.0f}<br>"
        f"Std Dev: {std_score:.0f}<br>"
        f"Min: {df['player.score'].min()}<br>"
        f"Max: {df['player.score'].max()}"
    )

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

    # --- Title --------------------------------------------------------------
    title_filters: OrderedDict[str, str | None] = OrderedDict()
    if country_filters:
        label = "Country" if len(country_filters) == 1 else "Countries"
        title_filters[label] = ", ".join(c.value for c in country_filters)
    title_filters["Total Players"] = str(total_battles)
    title_filters["Unique Players"] = str(unique_players)

    title = title_builder.build_title("Score Distribution", filters=title_filters)

    # --- Layout -------------------------------------------------------------
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16)),
        xaxis=dict(title="Score", gridcolor="lightgray", gridwidth=1, zeroline=False),
        yaxis=dict(title="Frequency", gridcolor="lightgray", gridwidth=1, zeroline=False),
        plot_bgcolor="white",
        width=get_graph_width(),
        height=600,
        showlegend=False,
        margin=dict(b=60),
        hovermode="closest",
    )

    return fig
