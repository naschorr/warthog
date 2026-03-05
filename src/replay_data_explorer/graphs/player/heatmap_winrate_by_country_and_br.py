from src.replay_data_explorer.graphs.initialization import *


def create_heatmap_winrate_by_country_and_br(
    player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]
):
    """
    Create an interactive Plotly heatmap showing the player's win rate by country and battle rating.

    Win rate is calculated as: (wins / total games) * 100
    Battles where the player left early are excluded.

    Args:
        player_performance_df: DataFrame with performance data for the player
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

    # Filter out battles where player left early
    df = df[df["status"] != "left"]

    if df.empty:
        print("No data available after filtering out 'left' status")
        return None

    # Get unique countries and battle ratings
    available_countries = sorted(df["player.country"].unique(), reverse=True)
    available_brs = sorted(df["player.battle_rating"].unique())

    if len(available_countries) == 0 or len(available_brs) == 0:
        print("Insufficient data for heatmap")
        return None

    # Create win indicator (1 for win, 0 for loss)
    df["won"] = (df["status"] == "success").astype(int)

    # Group by country and player battle rating
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

    # Create pivot tables for heatmap
    winrate_pivot = grouped.pivot(index="player.country", columns="player.battle_rating", values="win_rate")
    appearances_pivot = grouped.pivot(index="player.country", columns="player.battle_rating", values="appearances")
    wins_pivot = grouped.pivot(index="player.country", columns="player.battle_rating", values="wins")

    # Ensure pivot tables have all countries and BRs
    winrate_pivot = winrate_pivot.reindex(index=available_countries, columns=available_brs)
    appearances_pivot = appearances_pivot.reindex(index=available_countries, columns=available_brs).fillna(0)
    wins_pivot = wins_pivot.reindex(index=available_countries, columns=available_brs).fillna(0)

    # Prepare data for the heatmap
    z_values = winrate_pivot.values
    x_values = [f"{br:.1f}" for br in available_brs]
    y_values = available_countries

    # Create custom hover text
    hover_text = []
    for i, country in enumerate(available_countries):
        row = []
        for j, br in enumerate(available_brs):
            win_rate = winrate_pivot.iloc[i, j]
            appearances = appearances_pivot.iloc[i, j]
            wins = wins_pivot.iloc[i, j]
            if pd.notna(win_rate) and appearances > 0:
                row.append(
                    f"Country: {country}<br>"
                    f"Battle Rating: {br:.1f}<br>"
                    f"Win Rate: {win_rate:.1f}%<br>"
                    f"Wins: {int(wins)}<br>"
                    f"Battles: {int(appearances)}"
                )
            else:
                row.append(f"Country: {country}<br>Battle Rating: {br:.1f}<br>No data")
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
            xgap=1,
            ygap=1,
        )
    )

    # Add text annotations showing win rates
    annotations = []
    for i, country in enumerate(available_countries):
        for j, br in enumerate(available_brs):
            win_rate = winrate_pivot.iloc[i, j]
            appearances = appearances_pivot.iloc[i, j]
            if pd.notna(win_rate) and appearances > 0:
                annotations.append(
                    dict(
                        x=j,
                        y=i,
                        text=f"{win_rate:.0f}%",
                        showarrow=False,
                        font=dict(color="white", size=10),
                        xanchor="center",
                        yanchor="middle",
                    )
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
    title = title_builder.build_title("Win Rate by Country and Battle Rating", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Battle Rating", side="bottom", tickangle=45 if len(available_brs) > 10 else 0),
        yaxis=dict(title="Country", side="left"),
        width=max(800, len(available_brs) * 40),
        height=max(400, len(available_countries) * 60),
        plot_bgcolor="white",
        margin=dict(l=100, r=100, t=80, b=100),
    )

    fig.update_layout(annotations=annotations)

    return fig
