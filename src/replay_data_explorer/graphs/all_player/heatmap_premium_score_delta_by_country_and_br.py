from src.replay_data_explorer.graphs.initialization import *


def create_heatmap_premium_score_delta_by_country_and_br(global_performance_df: pd.DataFrame, *, country_filters=[]):
    """
    Create an interactive Plotly heatmap showing score delta between premium and non-premium players by country and battle rating.

    Args:
        global_performance_df: DataFrame with global player performance data
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

    if len(available_countries) == 0 or len(available_brs) == 0:
        print("Insufficient data for heatmap")
        return None

    # Calculate mean scores for premium and non-premium players separately
    premium_data = (
        df[df["player.is_premium"] == True]
        .groupby(["player.country", "player.battle_rating"])["player.score"]
        .agg(["mean", "count"])
        .reset_index()
    )
    premium_data.columns = ["player.country", "player.battle_rating", "premium_mean", "premium_count"]

    non_premium_data = (
        df[df["player.is_premium"] == False]
        .groupby(["player.country", "player.battle_rating"])["player.score"]
        .agg(["mean", "count"])
        .reset_index()
    )
    non_premium_data.columns = ["player.country", "player.battle_rating", "non_premium_mean", "non_premium_count"]

    # Merge the data
    heatmap_data = pd.merge(
        premium_data, non_premium_data, on=["player.country", "player.battle_rating"], how="outer"
    ).fillna(0)

    # Calculate score delta (premium - non_premium) only where both have sufficient data
    heatmap_data["premium_delta"] = None
    heatmap_data["total_count"] = heatmap_data["premium_count"] + heatmap_data["non_premium_count"]

    # Only calculate delta where both premium and non-premium have sufficient data
    valid_mask = (heatmap_data["premium_count"] >= MINIMUM_ITEMS_FOR_PLOTTING) & (
        heatmap_data["non_premium_count"] >= MINIMUM_ITEMS_FOR_PLOTTING
    )
    heatmap_data.loc[valid_mask, "premium_delta"] = (
        heatmap_data.loc[valid_mask, "premium_mean"] - heatmap_data.loc[valid_mask, "non_premium_mean"]
    )

    # Filter out cells with insufficient total data
    heatmap_data = heatmap_data[heatmap_data["total_count"] >= MINIMUM_ITEMS_FOR_PLOTTING * 2]

    # Create pivot tables for the heatmap
    delta_pivot = heatmap_data.pivot(index="player.country", columns="player.battle_rating", values="premium_delta")
    premium_count_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="premium_count"
    )
    non_premium_count_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="non_premium_count"
    )
    premium_mean_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="premium_mean"
    )
    non_premium_mean_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="non_premium_mean"
    )

    # Fill NaN values with None for better visualization
    delta_pivot = delta_pivot.reindex(index=available_countries, columns=available_brs)
    premium_count_pivot = premium_count_pivot.reindex(index=available_countries, columns=available_brs).fillna(0)
    non_premium_count_pivot = non_premium_count_pivot.reindex(index=available_countries, columns=available_brs).fillna(
        0
    )
    premium_mean_pivot = premium_mean_pivot.reindex(index=available_countries, columns=available_brs)
    non_premium_mean_pivot = non_premium_mean_pivot.reindex(index=available_countries, columns=available_brs)

    # Prepare data for the heatmap
    z_values = delta_pivot.values
    x_values = [f"{br:.1f}" for br in available_brs]
    y_values = available_countries

    # Create custom hover text with detailed information
    hover_text = []
    for i, country in enumerate(available_countries):
        row_text = []
        for j, br in enumerate(available_brs):
            delta = delta_pivot.iloc[i, j]
            premium_count = premium_count_pivot.iloc[i, j]
            non_premium_count = non_premium_count_pivot.iloc[i, j]
            premium_mean = premium_mean_pivot.iloc[i, j]
            non_premium_mean = non_premium_mean_pivot.iloc[i, j]

            if (
                pd.isna(delta)
                or premium_count < MINIMUM_ITEMS_FOR_PLOTTING
                or non_premium_count < MINIMUM_ITEMS_FOR_PLOTTING
            ):
                row_text.append(
                    f"Country: {country}<br>"
                    + f"Battle Rating: {br:.1f}<br>"
                    + f"Insufficient data<br>"
                    + f"Premium players: {int(premium_count)}<br>"
                    + f"Non-premium players: {int(non_premium_count)}<br>"
                    + f"(Need ≥{MINIMUM_ITEMS_FOR_PLOTTING} each)"
                )
            else:
                row_text.append(
                    f"Country: {country}<br>"
                    + f"Battle Rating: {br:.1f}<br>"
                    + f"Score Delta: {delta:.0f}<br>"
                    + f"Premium Mean: {premium_mean:.0f} ({int(premium_count)} players)<br>"
                    + f"Non-Premium Mean: {non_premium_mean:.0f} ({int(non_premium_count)} players)"
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
            colorbar=dict(title=dict(text="Score Delta", font=dict(size=12)), tickfont=dict(size=10)),
        )
    )

    # Build the graph's title
    title_filters = OrderedDict()
    title_filters["Total Players"] = str(len(df))
    title_filters["Premium Players"] = str(len(df[df["player.is_premium"] == True]))
    title_filters["Non-Premium Players"] = str(len(df[df["player.is_premium"] == False]))
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [country.value for country in country_filters]
        )
    title = title_builder.build_title(
        "Premium vs Non-Premium Score Delta by Country and Battle Rating", filters=title_filters
    )

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

    # Add text annotations showing score delta (only for cells with sufficient data)
    annotations = []
    for i, country in enumerate(available_countries):
        for j, br in enumerate(available_brs):
            delta = delta_pivot.iloc[i, j]
            premium_count = premium_count_pivot.iloc[i, j]
            non_premium_count = non_premium_count_pivot.iloc[i, j]

            if (
                not pd.isna(delta)
                and premium_count >= MINIMUM_ITEMS_FOR_PLOTTING
                and non_premium_count >= MINIMUM_ITEMS_FOR_PLOTTING
            ):
                annotations.append(
                    dict(
                        x=j,  # Use index for proper centering
                        y=i,  # Use index for proper centering
                        text=f"{delta:.0f}",
                        showarrow=False,
                        font=dict(color="white", size=10),
                        xanchor="center",  # Center horizontally
                        yanchor="middle",  # Center vertically
                    )
                )

    fig.update_layout(annotations=annotations)

    return fig
