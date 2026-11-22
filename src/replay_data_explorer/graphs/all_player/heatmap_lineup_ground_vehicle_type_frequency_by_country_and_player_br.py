from src.replay_data_explorer.graphs.initialization import *

GROUND_VEHICLE_TYPES = [
    VehicleType.LIGHT_TANK,
    VehicleType.MEDIUM_TANK,
    VehicleType.HEAVY_TANK,
    VehicleType.TANK_DESTROYER,
    VehicleType.ANTI_AIR,
]

GROUND_VEHICLE_TYPE_COLORS = {
    VehicleType.LIGHT_TANK.value: "#1f77b4",
    VehicleType.MEDIUM_TANK.value: "#ff7f0e",
    VehicleType.HEAVY_TANK.value: "#2ca02c",
    VehicleType.TANK_DESTROYER.value: "#d62728",
    VehicleType.ANTI_AIR.value: "#9467bd",
}


def create_heatmap_lineup_ground_vehicle_type_frequency_by_country_and_player_br(
    global_performance_df: pd.DataFrame,
    *,
    player_name: Optional[str] = None,
    display_player_name=None,
    country_filters=[],
    min_appearances: int = 10,
):
    """
    Create a grid of pie charts showing the frequency of ground vehicle types by country and player BR.

    Each cell is a pie chart representing the percentage of ground vehicle types used in player
    lineups for that country and player battle rating.
    """
    if global_performance_df.empty:
        print("No data available for plotting")
        return None

    df, _ = get_br_limited_graph_data(
        global_performance_df,
        [
            "status",
            "player.lineup",
            "player.country",
            "start_time",
            "session_id",
        ],
        battle_rating_column="player.battle_rating",
    )
    df = df[df["status"] != "left"]
    if df.empty:
        print("No data available after filtering out 'left' status")
        return None

    df = df[df["player.battle_rating"].notna()]
    df = df[df["player.lineup"].notna()]

    if country_filters:
        country_values = [c.value for c in country_filters]
        df = df[df["player.country"].isin(country_values)]

    if df.empty:
        print("No data available after filtering")
        return None

    # Normalize start_time for vehicle lookups
    if "start_time" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")

    vehicle_type_cache: dict[str, tuple[Optional[VehicleType], Optional[str]]] = {}

    def get_ground_vehicle_type_counts(lineup: object, player_country: str | None) -> dict[str, int]:
        counts = {vehicle_type.value: 0 for vehicle_type in GROUND_VEHICLE_TYPES}
        if not isinstance(lineup, list) or len(lineup) == 0:
            return counts

        for internal_name in lineup:
            if not internal_name:
                continue

            if internal_name in vehicle_type_cache:
                vehicle_type, vehicle_country = vehicle_type_cache[internal_name]
            else:
                vehicle = vehicle_service.get_vehicles_by_internal_name(internal_name)
                vehicle_type = vehicle.vehicle_type if vehicle is not None else None
                vehicle_country = vehicle.country.value if vehicle is not None else None
                vehicle_type_cache[internal_name] = (vehicle_type, vehicle_country)

            if vehicle_type in GROUND_VEHICLE_TYPES:
                if player_country is not None and vehicle_country != player_country:
                    continue
                counts[vehicle_type.value] += 1

        return counts

    def get_total_ground_vehicles(counts: dict[str, int]) -> int:
        return sum(counts.values())

    counts = []
    totals = []
    for _, row in df.iterrows():
        lineup = row.get("player.lineup", [])
        vehicle_counts = get_ground_vehicle_type_counts(lineup, row.get("player.country"))
        counts.append(vehicle_counts)
        totals.append(get_total_ground_vehicles(vehicle_counts))

    df = df.assign(_ground_vehicle_type_counts=counts, _ground_vehicle_total=totals)
    df = pd.concat(
        [df.drop(columns=["_ground_vehicle_type_counts"]), pd.DataFrame(df["_ground_vehicle_type_counts"].tolist(), index=df.index)],
        axis=1,
    )

    df = df[df["_ground_vehicle_total"] > 0]
    if df.empty:
        print("No ground vehicle lineup data available")
        return None

    grouped = (
        df.groupby(["player.country", "player.battle_rating"])
        .agg(
            **{vehicle_type.value: (vehicle_type.value, "sum") for vehicle_type in GROUND_VEHICLE_TYPES},
            appearances=("player.battle_rating", "count"),
            total_ground_vehicles=("_ground_vehicle_total", "sum"),
        )
        .reset_index()
    )

    if grouped.empty:
        print("No data available after grouping")
        return None

    annotation_types = [
        VehicleType.LIGHT_TANK.value,
        VehicleType.HEAVY_TANK.value,
        VehicleType.TANK_DESTROYER.value,
        VehicleType.ANTI_AIR.value,
    ]

    br_totals = grouped.groupby("player.battle_rating")["total_ground_vehicles"].sum()
    br_appearances = grouped.groupby("player.battle_rating")["appearances"].sum()
    valid_br_info = pd.DataFrame(
        {
            "total_ground_vehicles": br_totals,
            "appearances": br_appearances,
        }
    )

    annotation_brs = sorted(
        [
            br
            for br, row in valid_br_info.iterrows()
            if br >= 3.0 and row["appearances"] >= min_appearances and row["total_ground_vehicles"] > 0
        ]
    )

    visible_brs = sorted(
        set(
            grouped[
                (grouped["player.battle_rating"] >= 1.0)
                & (grouped["appearances"] >= min_appearances)
                & (grouped["total_ground_vehicles"] > 0)
            ]["player.battle_rating"]
        )
    )
    available_brs = visible_brs
    if not available_brs:
        print("No visible battle ratings available after country-level filtering")
        return None

    if annotation_brs:
        br_type_shares = (
            grouped[grouped["player.battle_rating"].isin(annotation_brs)]
            .groupby("player.battle_rating")[annotation_types]
            .sum()
            .div(br_totals.loc[annotation_brs], axis=0)
            .fillna(0)
        )
    else:
        br_type_shares = pd.DataFrame(columns=annotation_types)

    available_brs = visible_brs
    relative_threshold = 0.9
    max_highlighted_brs_per_type = 3
    max_share_by_type = br_type_shares.max() if not br_type_shares.empty else pd.Series({t: 0 for t in annotation_types})
    relative_share = br_type_shares.div(max_share_by_type, axis=0).fillna(0)

    highlight_type_candidates_by_br: dict[float, list[str]] = {}
    highlight_type_by_br: dict[float, str] = {}
    strong_br_by_type: dict[str, list[float]] = {}
    for vehicle_type_name in annotation_types:
        shares = br_type_shares[vehicle_type_name].sort_values(ascending=False)
        max_share = shares.max()
        if max_share <= 0:
            strong_br_by_type[vehicle_type_name] = []
            continue

        strong_brs = shares[shares >= max_share * relative_threshold].index.tolist()
        if len(strong_brs) < max_highlighted_brs_per_type:
            strong_brs = shares.nlargest(max_highlighted_brs_per_type).index.tolist()

        strong_br_by_type[vehicle_type_name] = strong_brs

    for vehicle_type_name, strong_brs in strong_br_by_type.items():
        for br in strong_brs:
            highlight_type_candidates_by_br.setdefault(br, []).append(vehicle_type_name)

    for br, candidates in highlight_type_candidates_by_br.items():
        best_type = max(candidates, key=lambda t: br_type_shares.loc[br, t])
        highlight_type_by_br[br] = best_type

    unique_countries = sorted(set(grouped["player.country"].unique()) - {"USA"})
    if "USA" in set(grouped["player.country"].unique()):
        unique_countries.append("USA")
    available_countries = unique_countries

    fig = go.Figure()

    # Add legend helper traces for each vehicle type so the legend shows the color mapping.
    # Use x/y None so the trace does not render a visible point in the figure.
    for vehicle_type in GROUND_VEHICLE_TYPES:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=GROUND_VEHICLE_TYPE_COLORS[vehicle_type.value], line=dict(color="white", width=1)),
                name=vehicle_type.value,
                showlegend=True,
                hoverinfo="none",
            )
        )

    num_brs = len(available_brs)
    num_countries = len(available_countries)
    cell_width = 1.0 / max(1, num_brs)
    cell_height = 1.0 / max(1, num_countries)

    def domain_fraction(index: int, total: int) -> float:
        return float(index) / float(total)

    annotations = []
    for row_index, country in enumerate(available_countries):
        for col_index, br in enumerate(available_brs):
            row_mask = (grouped["player.country"] == country) & (grouped["player.battle_rating"] == br)
            row_data = grouped[row_mask]
            x0 = domain_fraction(col_index, num_brs)
            x1 = domain_fraction(col_index + 1, num_brs)
            y0 = domain_fraction(num_countries - row_index - 1, num_countries)
            y1 = domain_fraction(num_countries - row_index, num_countries)
            if row_data.empty:
                continue

            appearances = int(row_data.iloc[0]["appearances"])
            total_ground_vehicles = int(row_data.iloc[0]["total_ground_vehicles"])
            if appearances < min_appearances or total_ground_vehicles == 0:
                continue

            values = []
            labels = []
            colors = []
            hovertext = []
            domain_padding_x = min(cell_width * 0.01, 0.01)
            domain_padding_y = min(cell_height * 0.1, 0.03)
            domain_x0 = x0 + domain_padding_x
            domain_x1 = x1 - domain_padding_x
            domain_y0 = y0 + domain_padding_y
            domain_y1 = y1 - domain_padding_y
            for vehicle_type in GROUND_VEHICLE_TYPES:
                label = vehicle_type.value
                count = int(row_data.iloc[0][label])
                if count > 0:
                    values.append(count)
                    labels.append(label)
                    colors.append(GROUND_VEHICLE_TYPE_COLORS[label])
                    hovertext.append(
                        "<b>"
                        + label
                        + "</b><br>"
                        + f"Count: {count}<br>"
                        + f"Percentage: {count / total_ground_vehicles:.1%}<br>"
                        + f"Country: {country}<br>"
                        + f"Player BR: {br:.1f}<br>"
                        + f"Lineups: {appearances}<br>"
                        + f"Vehicles: {total_ground_vehicles}"
                    )

            if not values:
                annotations.append(
                    dict(
                        x=(x0 + x1) / 2,
                        y=(y0 + y1) / 2,
                        xref="paper",
                        yref="paper",
                        text="No<br>ground<br>vehicles",
                        showarrow=False,
                        font=dict(size=10, color="gray"),
                        xanchor="center",
                        yanchor="middle",
                    )
                )
                continue

            fig.add_trace(
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors, line=dict(color="white", width=1)),
                    textinfo="none",
                    hoverinfo="text",
                    hovertext=hovertext,
                    domain={"x": [domain_x0, domain_x1], "y": [domain_y0, domain_y1]},
                    showlegend=False,
                    sort=False,
                    direction="clockwise",
                    legendgroup="ground_vehicle_type",
                )
            )

    for col_index, br in enumerate(available_brs):
        x0 = col_index * cell_width
        x1 = x0 + cell_width
        annotations.append(
            dict(
                x=(x0 + x1) / 2,
                y=1.06,
                xref="paper",
                yref="paper",
                text=f"{br:.1f}",
                showarrow=False,
                font=dict(size=10, color="black"),
                xanchor="center",
                yanchor="bottom",
            )
        )

    for row_index, country in enumerate(available_countries):
        y1 = 1.0 - row_index * cell_height
        y0 = y1 - cell_height
        annotations.append(
            dict(
                x=-0.02,
                y=(y0 + y1) / 2,
                xref="paper",
                yref="paper",
                text=country,
                showarrow=False,
                font=dict(size=10, color="black"),
                xanchor="right",
                yanchor="middle",
            )
        )

    title_filters = OrderedDict()
    title_filters["Min Appearances"] = str(min_appearances)
    annotations.append(
        dict(
            x=0.5,
            y=-0.02,
            xref="paper",
            yref="paper",
            text="Player Battle Rating",
            showarrow=False,
            font=dict(size=12, color="black"),
            xanchor="center",
            yanchor="top",
        )
    )
    annotations.append(
        dict(
            x=-0.09,
            y=0.5,
            xref="paper",
            yref="paper",
            text="Country",
            showarrow=False,
            font=dict(size=12, color="black"),
            xanchor="center",
            yanchor="middle",
            textangle=-90,
        )
    )
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [c.value for c in country_filters]
        )
    total_replays = df["session_id"].nunique()
    title_filters["Total Replays"] = str(total_replays)
    title_filters["Type Threshold"] = f"{int(relative_threshold * 100)}th percentile"
    title = title_builder.build_title(
        "Ground Vehicle Type Lineup Frequency by Country and Player Battle Rating",
        filters=title_filters,
    )

    shapes = []
    for col_index, br in enumerate(available_brs):
        candidates = highlight_type_candidates_by_br.get(br)
        if not candidates:
            continue
        x0 = col_index * cell_width
        total_candidates = len(candidates)
        band_width = cell_width / total_candidates
        for band_index, candidate_type in enumerate(candidates):
            shapes.append(
                dict(
                    type="rect",
                    xref="paper",
                    yref="paper",
                    x0=x0 + band_index * band_width,
                    x1=x0 + (band_index + 1) * band_width,
                    y0=0.0,
                    y1=1.0,
                    fillcolor=GROUND_VEHICLE_TYPE_COLORS[candidate_type],
                    opacity=1.0,
                    line_width=0,
                    layer="below",
                )
            )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        width=max(get_graph_width("heatmap"), int(len(available_brs) * 40)),
        height=max(420, int(len(available_countries) * 48)),
        margin=dict(l=80, r=120, t=140, b=70),
        plot_bgcolor="white",
        legend=dict(orientation="v", yanchor="top", y=0.95, xanchor="left", x=1.02),
        annotations=annotations,
        shapes=shapes,
        xaxis=dict(visible=False, showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(visible=False, showgrid=False, zeroline=False, showticklabels=False),
        legend_itemclick=False,
        legend_itemdoubleclick=False,
    )

    return fig
