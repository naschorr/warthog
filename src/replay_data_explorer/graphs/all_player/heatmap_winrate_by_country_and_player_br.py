from src.replay_data_explorer.graphs.initialization import *


def create_heatmap_winrate_by_country_and_player_br(
    global_performance_df: pd.DataFrame,
    *,
    player_name: Optional[str] = None,
    display_player_name=None,
    country_filters=[],
    min_appearances: int = 10,
):
    """
    Create an interactive Plotly heatmap showing win rates for all players by country and player battle rating.

    Win rate is calculated as: (wins / total games) * 100
    Cells with fewer appearances than min_appearances show "Insufficient data" in hover.

    Args:
        global_performance_df: DataFrame with performance data (should include player.*, session_id columns)
        player_name: Player name (unused for global view, kept for consistency)
        display_player_name: Display name (unused for global view, kept for consistency)
        country_filters: List of countries to filter by (if empty, shows all countries)
        min_appearances: Minimum number of appearances to show win rate (default: 10)

    Returns:
        Plotly figure object
    """
    if global_performance_df.empty:
        print("No data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = global_performance_df.copy()

    # Filter out battles where player left early
    df = df[df["status"] != "left"]

    if df.empty:
        print("No data available after filtering out 'left' status")
        return None

    # Filter by player BR (only battles where the player BR is present)
    df = df[df["player.battle_rating"].notna()]

    # Apply country filters if provided
    if country_filters:
        # Convert Country enums to their values for filtering
        country_values = [c.value for c in country_filters]
        df = df[df["player.country"].isin(country_values)]

    if df.empty:
        print("No data available after filtering")
        return None

    # Create win indicator (1 for win, 0 for loss)
    df["won"] = (df["status"] == "success").astype(int)

    # Group by country and player battle rating
    # Calculate win rate and appearance count
    grouped = (
        df.groupby(["player.country", "player.battle_rating"])
        .agg(wins=("won", "sum"), appearances=("won", "count"))
        .reset_index()
    )

    # Calculate win rate percentage
    grouped["win_rate"] = (grouped["wins"] / grouped["appearances"]) * 100

    if grouped.empty:
        print("No data available after grouping")
        return None

    # Get available countries and BRs
    available_countries = sorted(grouped["player.country"].unique(), reverse=True)
    available_brs = sorted(grouped["player.battle_rating"].unique())

    # Create pivot tables for heatmap
    winrate_pivot = grouped.pivot(index="player.country", columns="player.battle_rating", values="win_rate")
    appearances_pivot = grouped.pivot(index="player.country", columns="player.battle_rating", values="appearances")
    wins_pivot = grouped.pivot(index="player.country", columns="player.battle_rating", values="wins")

    # Ensure pivot tables have all countries and BRs
    winrate_pivot = winrate_pivot.reindex(index=available_countries, columns=available_brs)
    appearances_pivot = appearances_pivot.reindex(index=available_countries, columns=available_brs)
    wins_pivot = wins_pivot.reindex(index=available_countries, columns=available_brs)

    # Prepare data for the heatmap
    # Mask cells with insufficient data so they don't get colored
    z_values = winrate_pivot.copy().values
    for i in range(len(available_countries)):
        for j in range(len(available_brs)):
            appearances = appearances_pivot.iloc[i, j]
            if pd.isna(appearances) or appearances < min_appearances:
                z_values[i, j] = np.nan

    x_values = [f"{br:.1f}" for br in available_brs]
    y_values = available_countries

    # Create custom hover text with win rate and appearance count
    hover_text = []
    for i, country in enumerate(available_countries):
        row = []
        for j, br in enumerate(available_brs):
            win_rate = winrate_pivot.iloc[i, j]
            appearances = appearances_pivot.iloc[i, j]
            wins = wins_pivot.iloc[i, j]
            if pd.notna(appearances) and appearances >= min_appearances:
                row.append(
                    f"Country: {country}<br>"
                    f"Player BR: {br}<br>"
                    f"Win Rate: {win_rate:.3f}%<br>"
                    f"Wins: {int(wins)}<br>"
                    f"Appearances: {int(appearances)}"
                )
            elif pd.notna(appearances) and appearances > 0:
                row.append(
                    f"Country: {country}<br>"
                    f"Player BR: {br}<br>"
                    f"Insufficient data (< {min_appearances} appearances)<br>"
                    f"Wins: {int(wins)}<br>"
                    f"Appearances: {int(appearances)}"
                )
            else:
                # Empty cells (no appearances)
                row.append(
                    f"Country: {country}<br>"
                    f"Player BR: {br}<br>"
                    f"Insufficient data (< {min_appearances} appearances)<br>"
                    f"Wins: 0<br>"
                    f"Appearances: 0"
                )
        hover_text.append(row)

    # Create the heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=x_values,
            y=y_values,
            colorscale=PLOTLY_COLOR_SCALE,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
            showscale=True,
            colorbar=dict(title=dict(text="Win Rate (%)", font=dict(size=12)), tickfont=dict(size=10)),
        )
    )

    # Add text annotations showing win rates (only for cells with sufficient data)
    annotations = []
    for i, country in enumerate(available_countries):
        for j, br in enumerate(available_brs):
            win_rate = winrate_pivot.iloc[i, j]
            appearances = appearances_pivot.iloc[i, j]
            if pd.notna(appearances) and appearances >= min_appearances:
                annotations.append(
                    dict(
                        x=j,  # Use index for proper centering
                        y=i,  # Use index for proper centering
                        text=f"{win_rate:.0f}%",
                        showarrow=False,
                        font=dict(color="white", size=10),
                        xanchor="center",  # Center horizontally
                        yanchor="middle",  # Center vertically
                    )
                )

    # Build the graph's title
    title_filters = OrderedDict()
    title_filters["Min Appearances"] = str(min_appearances)
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [c.value for c in country_filters]
        )
    # Count unique replays (session_id)
    total_replays = df["session_id"].nunique()
    title_filters["Total Replays"] = str(total_replays)
    title = title_builder.build_title("Win Rate by Country and Player Battle Rating", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Player Battle Rating", side="bottom", tickangle=45 if len(available_brs) > 10 else 0),
        yaxis=dict(title="Country", side="left"),
        width=max(get_graph_width("heatmap"), len(available_brs) * 40),  # Dynamic width based on BR count
        height=max(400, len(available_countries) * 60),  # Dynamic height based on country count
        plot_bgcolor="white",
        margin=dict(l=100, r=100, t=80, b=100),
    )

    # Add the annotations
    fig.update_layout(annotations=annotations)

    return fig
