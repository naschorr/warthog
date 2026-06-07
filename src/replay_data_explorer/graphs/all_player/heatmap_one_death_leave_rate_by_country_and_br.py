from src.replay_data_explorer.common import bayesian_smooth
from src.replay_data_explorer.graphs.initialization import *


def create_heatmap_one_death_leave_rate_by_country_and_br(
    global_performance_df: pd.DataFrame,
    *,
    player_name: Optional[str] = None,
    display_player_name=None,
    country_filters=[],
    min_appearances: int = 3,
    smoothing_factor: int = 20,
):
    """
    Create an interactive Plotly heatmap showing the percentage of players who leave after exactly one death.

    Sparse cells are regularised with Bayesian (additive) smoothing rather than blanked out.
    The smoothed rate for each (country, BR) cell is:

        smoothed = (leavers + smoothing_factor * global_prior) / (appearances + smoothing_factor) * 100

    where global_prior is the overall one-death leave rate across all cells.  Cells with fewer
    than min_appearances observations are still hidden (NaN) as they carry essentially no signal
    even after smoothing.

    Args:
        global_performance_df: DataFrame with performance data (should include player.*, session_id columns)
        player_name: Player name (unused for global view, kept for consistency)
        display_player_name: Display name (unused for global view, kept for consistency)
        country_filters: List of countries to filter by (if empty, shows all countries)
        min_appearances: Minimum observations required to display a cell (default: 3)
        smoothing_factor: Equivalent phantom observations at the global prior rate (default: 20).
                          Higher values pull sparse cells harder toward the global mean.

    Returns:
        Plotly figure object
    """
    if global_performance_df.empty:
        print("No data available for plotting")
        return None

    df = global_performance_df.copy()

    df = df[df["battle_rating"].notna()]
    df = df[df["player.country"].notna()]
    df = df[df["player.deaths"].notna()]

    if country_filters:
        country_values = [country.value for country in country_filters]
        df = df[df["player.country"].isin(country_values)]

    if df.empty:
        print("No data available after filtering")
        return None

    df["player.deaths.total"] = df["player.deaths"].apply(
        lambda value: value.get("total") if isinstance(value, dict) else value
    )
    df["left_after_one_death"] = ((df["status"] == "left") & (df["player.deaths.total"] == 1)).astype(int)

    grouped = (
        df.groupby(["player.country", "battle_rating"])
        .agg(
            one_death_leavers=("left_after_one_death", "sum"),
            appearances=("left_after_one_death", "count"),
        )
        .reset_index()
    )

    grouped["one_death_leave_rate"] = (grouped["one_death_leavers"] / grouped["appearances"]) * 100

    grouped["smoothed_rate"] = (
        bayesian_smooth(grouped["one_death_leavers"], grouped["appearances"], smoothing_factor) * 100
    )

    if grouped.empty:
        print("No data available after grouping")
        return None

    available_countries = sorted(grouped["player.country"].unique(), reverse=True)
    available_brs = sorted(grouped["battle_rating"].unique())

    rate_pivot = grouped.pivot(index="player.country", columns="battle_rating", values="one_death_leave_rate")
    smoothed_pivot = grouped.pivot(index="player.country", columns="battle_rating", values="smoothed_rate")
    appearances_pivot = grouped.pivot(index="player.country", columns="battle_rating", values="appearances")
    leavers_pivot = grouped.pivot(index="player.country", columns="battle_rating", values="one_death_leavers")

    rate_pivot = rate_pivot.reindex(index=available_countries, columns=available_brs)
    smoothed_pivot = smoothed_pivot.reindex(index=available_countries, columns=available_brs)
    appearances_pivot = appearances_pivot.reindex(index=available_countries, columns=available_brs)
    leavers_pivot = leavers_pivot.reindex(index=available_countries, columns=available_brs)

    # Build z_values from smoothed rates; blank only truly empty cells (below min_appearances).
    z_values = smoothed_pivot.copy().values
    for i in range(len(available_countries)):
        for j in range(len(available_brs)):
            appearances = appearances_pivot.iloc[i, j]
            if pd.isna(appearances) or appearances < min_appearances:
                z_values[i, j] = np.nan

    x_values = [f"{br:.1f}" for br in available_brs]
    y_values = available_countries

    hover_text = []
    for i, country in enumerate(available_countries):
        row = []
        for j, br in enumerate(available_brs):
            raw_rate = rate_pivot.iloc[i, j]
            smoothed = smoothed_pivot.iloc[i, j]
            appearances = appearances_pivot.iloc[i, j]
            one_death_leavers = leavers_pivot.iloc[i, j]
            if pd.notna(appearances) and appearances >= min_appearances:
                confidence = "High" if appearances >= 50 else ("Medium" if appearances >= 20 else "Low")
                row.append(
                    f"Country: {country}<br>"
                    f"Battle Rating: {br:.1f}<br>"
                    f"Smoothed Leave Rate: {smoothed:.1f}%<br>"
                    f"Raw Leave Rate: {raw_rate:.1f}%<br>"
                    f"One-Death Leavers: {int(one_death_leavers)}<br>"
                    f"Appearances: {int(appearances)}<br>"
                    f"Confidence: {confidence} (prior α={smoothing_factor})"
                )
            else:
                row.append(
                    f"Country: {country}<br>"
                    f"Battle Rating: {br:.1f}<br>"
                    f"Insufficient data (< {min_appearances} appearances)"
                )
        hover_text.append(row)

    valid_z_values = z_values[~np.isnan(z_values)]
    heatmap_kwargs = {}
    if valid_z_values.size > 0:
        zmin = float(valid_z_values.min())
        zmax = float(valid_z_values.max())
        if zmin == zmax:
            # Ensure a visible color range when all values are identical.
            padding = 0.5 if zmin == 0 else abs(zmin) * 0.05
            zmin -= padding
            zmax += padding
        heatmap_kwargs["zmin"] = zmin
        heatmap_kwargs["zmax"] = zmax

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=x_values,
            y=y_values,
            colorscale=PLOTLY_COLOR_SCALE,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
            showscale=True,
            colorbar=dict(
                title=dict(text="One-Death Leave Rate (%)", font=dict(size=12)),
                tickfont=dict(size=10),
            ),
            **heatmap_kwargs,
        )
    )

    annotations = []
    for i, country in enumerate(available_countries):
        for j, br in enumerate(available_brs):
            smoothed = smoothed_pivot.iloc[i, j]
            appearances = appearances_pivot.iloc[i, j]
            if pd.notna(appearances) and appearances >= min_appearances:
                label = f"~{smoothed:.0f}%" if appearances < 20 else f"{smoothed:.0f}%"
                annotations.append(
                    dict(
                        x=j,
                        y=i,
                        text=label,
                        showarrow=False,
                        font=dict(color="white", size=10),
                        xanchor="center",
                        yanchor="middle",
                    )
                )

    title_filters = OrderedDict()
    title_filters["Smoothing Factor"] = str(smoothing_factor)
    title_filters["Min Appearances"] = str(min_appearances)
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [country.value for country in country_filters]
        )
    title_filters["Total Replays"] = str(df["session_id"].nunique())
    title = title_builder.build_title("One-Death Leave Rate by Country and Battle Rating", filters=title_filters)

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(title="Battle Rating", side="bottom", tickangle=45 if len(available_brs) > 10 else 0),
        yaxis=dict(title="Country", side="left"),
        width=max(get_graph_width("heatmap"), len(available_brs) * 40),
        height=max(400, len(available_countries) * 60),
        plot_bgcolor="white",
        margin=dict(l=100, r=100, t=80, b=100),
        annotations=annotations,
    )

    return fig
