from src.replay_data_explorer.graphs.initialization import *


def create_heatmap_premium_br_delta_by_country_and_br(
    global_performance_df: pd.DataFrame, *, author_name: Optional[str] = None, country_filters=[]
):
    """
    Create an interactive Plotly heatmap showing BR delta difference between premium and non-premium players by country and battle rating.

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
        author_mask = df["player.username"] == author_name
        author_data = df[author_mask]
        if len(author_data) > 0:
            author_max_br = author_data["player.battle_rating"].max()
            available_brs = [br for br in available_brs if br <= author_max_br]
            # Also filter the dataframe to only include BRs up to author's max
            br_mask = df["player.battle_rating"] <= author_max_br
            df = df[br_mask]
        else:
            print(f"Warning: Author '{author_name}' not found in data")

    if len(available_countries) == 0 or len(available_brs) == 0:
        print("Insufficient data for heatmap")
        return None

    # Calculate mean BR deltas for premium and non-premium players separately
    # Split the data to avoid type inference issues
    premium_mask = df["player.is_premium"] == True
    premium_subset = df.loc[premium_mask]
    premium_data = (
        premium_subset.groupby(["player.country", "player.battle_rating"])["player.battle_rating_delta"]
        .agg(["mean", "count"])
        .reset_index()
    )
    premium_data.columns = ["player.country", "player.battle_rating", "premium_br_delta_mean", "premium_count"]

    non_premium_mask = df["player.is_premium"] == False
    non_premium_subset = df.loc[non_premium_mask]
    non_premium_data = (
        non_premium_subset.groupby(["player.country", "player.battle_rating"])["player.battle_rating_delta"]
        .agg(["mean", "count"])
        .reset_index()
    )
    non_premium_data.columns = [
        "player.country",
        "player.battle_rating",
        "non_premium_br_delta_mean",
        "non_premium_count",
    ]

    # Merge the data
    heatmap_data = pd.merge(
        premium_data, non_premium_data, on=["player.country", "player.battle_rating"], how="outer"
    ).fillna(0)

    # Calculate BR delta difference (premium - non_premium) only where both have sufficient data
    heatmap_data["premium_br_delta_diff"] = None
    heatmap_data["total_count"] = heatmap_data["premium_count"] + heatmap_data["non_premium_count"]

    # Only calculate difference where both premium and non-premium have sufficient data
    valid_mask = (heatmap_data["premium_count"] >= MINIMUM_ITEMS_FOR_PLOTTING) & (
        heatmap_data["non_premium_count"] >= MINIMUM_ITEMS_FOR_PLOTTING
    )
    heatmap_data.loc[valid_mask, "premium_br_delta_diff"] = (
        heatmap_data.loc[valid_mask, "premium_br_delta_mean"]
        - heatmap_data.loc[valid_mask, "non_premium_br_delta_mean"]
    )

    # Filter out cells with insufficient total data
    heatmap_data = heatmap_data[heatmap_data["total_count"] >= MINIMUM_ITEMS_FOR_PLOTTING * 2]

    # Create pivot tables for the heatmap
    delta_diff_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="premium_br_delta_diff"
    )
    premium_count_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="premium_count"
    )
    non_premium_count_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="non_premium_count"
    )
    premium_br_delta_mean_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="premium_br_delta_mean"
    )
    non_premium_br_delta_mean_pivot = heatmap_data.pivot(
        index="player.country", columns="player.battle_rating", values="non_premium_br_delta_mean"
    )

    # Fill NaN values with None for better visualization
    delta_diff_pivot = delta_diff_pivot.reindex(index=available_countries, columns=available_brs)
    premium_count_pivot = premium_count_pivot.reindex(index=available_countries, columns=available_brs).fillna(0)
    non_premium_count_pivot = non_premium_count_pivot.reindex(index=available_countries, columns=available_brs).fillna(
        0
    )
    premium_br_delta_mean_pivot = premium_br_delta_mean_pivot.reindex(index=available_countries, columns=available_brs)
    non_premium_br_delta_mean_pivot = non_premium_br_delta_mean_pivot.reindex(
        index=available_countries, columns=available_brs
    )

    # Prepare data for the heatmap
    z_values = delta_diff_pivot.values
    x_values = [f"{br:.1f}" for br in available_brs]
    y_values = available_countries

    # Create custom hover text with detailed information
    hover_text = []
    for i, country in enumerate(available_countries):
        row_text = []
        for j, br in enumerate(available_brs):
            delta_diff = delta_diff_pivot.iloc[i, j]
            premium_count = premium_count_pivot.iloc[i, j]
            non_premium_count = non_premium_count_pivot.iloc[i, j]
            premium_br_delta_mean = premium_br_delta_mean_pivot.iloc[i, j]
            non_premium_br_delta_mean = non_premium_br_delta_mean_pivot.iloc[i, j]

            if (
                pd.isna(delta_diff)
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
                    + f"BR Delta Difference: {delta_diff:.3f}<br>"
                    + f"Premium Mean BR Delta: {premium_br_delta_mean:.3f} ({int(premium_count)} players)<br>"
                    + f"Non-Premium Mean BR Delta: {non_premium_br_delta_mean:.3f} ({int(non_premium_count)} players)"
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
            colorbar=dict(title=dict(text="BR Delta", font=dict(size=12)), tickfont=dict(size=10)),
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
        "Premium vs Non-Premium BR Delta Difference by Country and Battle Rating", filters=title_filters
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

    # Add text annotations showing BR delta difference (only for cells with sufficient data)
    annotations = []
    for i, country in enumerate(available_countries):
        for j, br in enumerate(available_brs):
            delta_diff = delta_diff_pivot.iloc[i, j]
            premium_count = premium_count_pivot.iloc[i, j]
            non_premium_count = non_premium_count_pivot.iloc[i, j]

            if (
                not pd.isna(delta_diff)
                and premium_count >= MINIMUM_ITEMS_FOR_PLOTTING
                and non_premium_count >= MINIMUM_ITEMS_FOR_PLOTTING
            ):
                annotations.append(
                    dict(
                        x=j,  # Use index for proper centering
                        y=i,  # Use index for proper centering
                        text=f"{delta_diff:.2f}",
                        showarrow=False,
                        font=dict(color="white", size=10),
                        xanchor="center",  # Center horizontally
                        yanchor="middle",  # Center vertically
                    )
                )

    fig.update_layout(annotations=annotations)

    return fig
