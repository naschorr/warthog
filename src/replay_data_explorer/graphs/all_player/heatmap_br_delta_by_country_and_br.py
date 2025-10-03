from src.replay_data_explorer.graphs.initialization import *


def create_heatmap_br_delta_by_country_and_br(
    global_performance_df: pd.DataFrame, *, author_name: Optional[str] = None, country_filters=[]
):
    """
    Create an interactive Plotly heatmap showing mean battle rating delta for all players by country and battle rating.

    Args:
        global_performance_df: DataFrame with global player performance data
        author_name: Name of the author, if provided the battle ratings will be capped to the author's max BR.
        country_filters: List of countries to filter by

    Returns:
        Plotly figure object
    """
    if global_performance_df.empty:
        print("No performance data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = global_performance_df.copy()

    # Get unique countries and battle ratings
    available_countries = sorted(df["player.country"].unique(), reverse=True)
    available_brs = sorted(df["player.battle_rating"].unique())

    # If author_name is provided, filter battle ratings to the author's max BR
    if author_name:
        author_data = df[df["player.username"] == author_name]
        if not author_data.empty:
            author_max_br = author_data["player.battle_rating"].max()
            available_brs = [br for br in available_brs if br <= author_max_br]
            # Also filter the dataframe to only include BRs up to author's max
            df = df[df["player.battle_rating"] <= author_max_br]
        else:
            print(f"Warning: Author '{author_name}' not found in data")

    if len(available_countries) == 0 or len(available_brs) == 0:
        print("Insufficient data for heatmap")
        return None

    # Create a pivot table for mean BR delta with minimum instance threshold
    heatmap_data = (
        df.groupby(["player.country", "player.battle_rating"])["player.battle_rating_delta"]
        .agg(["mean", "count"])
        .reset_index()
    )

    # Filter out cells with insufficient data
    heatmap_data = heatmap_data[heatmap_data["count"] >= MINIMUM_ITEMS_FOR_PLOTTING]

    # Create pivot table for the heatmap
    delta_pivot = heatmap_data.pivot(index="player.country", columns="player.battle_rating", values="mean")
    count_pivot = heatmap_data.pivot(index="player.country", columns="player.battle_rating", values="count")

    # Fill NaN values with None for better visualization
    delta_pivot = delta_pivot.reindex(index=available_countries, columns=available_brs)
    count_pivot = count_pivot.reindex(index=available_countries, columns=available_brs).fillna(0)

    # Prepare data for the heatmap
    z_values = delta_pivot.values
    x_values = [f"{br:.1f}" for br in available_brs]
    y_values = available_countries

    # Create custom hover text with count information
    hover_text = []
    for i, country in enumerate(available_countries):
        row_text = []
        for j, br in enumerate(available_brs):
            delta = delta_pivot.iloc[i, j]
            count = count_pivot.iloc[i, j]
            if pd.isna(delta) or count < MINIMUM_ITEMS_FOR_PLOTTING:
                row_text.append(
                    f"Country: {country}<br>"
                    + f"Battle Rating: {br:.1f}<br>"
                    + f"Insufficient data (< {MINIMUM_ITEMS_FOR_PLOTTING} players)"
                )
            else:
                tier_status_display = battle_rating_tier_display_builder.get_battle_rating_tier_display_from_delta(
                    delta
                )
                row_text.append(
                    f"Country: {country}<br>"
                    + f"Battle Rating: {br:.1f}<br>"
                    + f"Mean BR Delta: {delta:.2f}<br>"
                    + f"Tier Status: {tier_status_display}<br>"
                    + f"Total Players: {int(count)}"
                )
        hover_text.append(row_text)

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
            colorbar=dict(title=dict(text="Mean BR Delta", font=dict(size=12)), tickfont=dict(size=10)),
            zmin=-1,  # Set minimum to -1 (full downtier)
            zmax=0,  # Set maximum to 0 (uptier/same tier)
            zmid=-0.5,  # Center the colorscale at -0.5
        )
    )

    # Build the graph's title
    title_filters = OrderedDict()
    title_filters["Total Players"] = str(len(df))
    unique_players = set(df["player.username"])
    title_filters["Unique Players"] = str(len(unique_players))
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [country.value for country in country_filters]
        )
    title = title_builder.build_title("Global Mean BR Delta by Country and Battle Rating", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Battle Rating", side="bottom", tickangle=45 if len(available_brs) > 10 else 0),
        yaxis=dict(title="Country", side="left"),
        width=max(800, len(available_brs) * 40),  # Dynamic width based on BR count
        height=max(400, len(available_countries) * 60),  # Dynamic height based on country count
        plot_bgcolor="white",
        margin=dict(l=100, r=100, t=80, b=100),
    )

    # Add text annotations showing mean BR delta (only for cells with sufficient data)
    annotations = []
    for i, country in enumerate(available_countries):
        for j, br in enumerate(available_brs):
            delta = delta_pivot.iloc[i, j]
            count = count_pivot.iloc[i, j]
            if not pd.isna(delta) and count >= MINIMUM_ITEMS_FOR_PLOTTING:
                annotations.append(
                    dict(
                        x=j,  # Use index for proper centering
                        y=i,  # Use index for proper centering
                        text=f"{delta:.2f}",
                        showarrow=False,
                        font=dict(color="white", size=10),
                        xanchor="center",  # Center horizontally
                        yanchor="middle",  # Center vertically
                    )
                )

    fig.update_layout(annotations=annotations)

    return fig
