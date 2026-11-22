from src.replay_data_explorer.graphs.initialization import *
from src.replay_data_explorer.enums import BattleRatingTier


def create_heatmap_tier_frequency_by_country_and_player_br(
    global_performance_df: pd.DataFrame,
    *,
    country_filters: Optional[list[Country]] = None,
    min_appearances: int = 10,
):
    """Create a tier-frequency grid capped at each replay's BR."""
    if global_performance_df.empty:
        print("No performance data available for plotting")
        return None

    df, max_replay_br = get_br_limited_graph_data(
        global_performance_df,
        [
            "session_id",
            "player.username",
            "player.country",
            "player.tier_status",
        ],
        battle_rating_column="player.battle_rating",
        require_valid_br_delta=True,
    )
    df = df.drop(columns=["battle_rating"])
    df = df[
        df["player.country"].notna()
        & df["player.battle_rating"].notna()
        & df["player.tier_status"].notna()
    ]
    if country_filters:
        df = df[
            df["player.country"].isin([country.value for country in country_filters])
        ]

    if df.empty:
        print("No tier data available after filtering")
        return None

    def get_tier_value(value: object) -> str:
        tier = value if isinstance(value, BattleRatingTier) else BattleRatingTier(value)
        return tier.value

    df["_tier_status"] = df["player.tier_status"].map(get_tier_value)
    tier_order = [tier.value for tier in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER]
    grouped = (
        df.groupby(["player.country", "player.battle_rating", "_tier_status"])
        .size()
        .unstack("_tier_status", fill_value=0)
        .reindex(columns=tier_order, fill_value=0)
    )

    appearances_by_country_br = df.groupby(
        ["player.country", "player.battle_rating"]
    ).size()
    battle_ratings = sorted(
        {
            battle_rating
            for (_, battle_rating), appearances in appearances_by_country_br.items()
            if battle_rating >= 1.0 and appearances >= min_appearances
        }
    )
    countries = sorted(set(df["player.country"].unique()) - {"USA"})
    if "USA" in df["player.country"].values:
        countries.append("USA")

    if not countries or not battle_ratings:
        print("No visible battle ratings available after country-level filtering")
        return None

    tier_labels = {
        tier.value: battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(
            tier
        )
        for tier in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER
    }

    fig = go.Figure()
    for tier in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(
                    size=10,
                    color=PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier],
                    line=dict(color="white", width=1),
                ),
                name=tier_labels[tier.value],
                showlegend=True,
                hoverinfo="skip",
            )
        )

    num_brs = len(battle_ratings)
    num_countries = len(countries)
    cell_width = 1.0 / num_brs
    cell_height = 1.0 / num_countries
    annotations = []

    for row_index, country in enumerate(countries):
        y1 = 1.0 - row_index * cell_height
        y0 = y1 - cell_height
        for col_index, battle_rating in enumerate(battle_ratings):
            x0 = col_index * cell_width
            x1 = x0 + cell_width
            group_key = (country, battle_rating)
            if (
                group_key not in grouped.index
                or appearances_by_country_br.get(group_key, 0) < min_appearances
            ):
                continue

            counts = grouped.loc[group_key].reindex(tier_order, fill_value=0)
            counts = counts[counts > 0]
            total = int(counts.sum())
            if not total:
                continue

            labels = [tier_labels[tier] for tier in counts.index]
            values = [int(count) for count in counts]
            colors = [
                PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[BattleRatingTier(tier)]
                for tier in counts.index
            ]
            hovertext = [
                "<b>"
                + label
                + "</b><br>"
                + f"Players: {count}<br>"
                + f"Frequency: {count / total:.1%}<br>"
                + f"Country: {country}<br>"
                + f"Player BR: {battle_rating:.1f}<br>"
                + "Tier baseline: replay max BR"
                for label, count in zip(labels, values)
            ]

            padding_x = min(cell_width * 0.01, 0.01)
            padding_y = min(cell_height * 0.1, 0.03)
            fig.add_trace(
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors, line=dict(color="white", width=1)),
                    textinfo="none",
                    hoverinfo="text",
                    hovertext=hovertext,
                    domain={
                        "x": [x0 + padding_x, x1 - padding_x],
                        "y": [y0 + padding_y, y1 - padding_y],
                    },
                    showlegend=False,
                    sort=False,
                    direction="clockwise",
                )
            )

    for col_index, battle_rating in enumerate(battle_ratings):
        x0 = col_index * cell_width
        annotations.append(
            dict(
                x=x0 + cell_width / 2,
                y=1.06,
                xref="paper",
                yref="paper",
                text=f"{battle_rating:.1f}",
                showarrow=False,
                font=dict(size=10, color="black"),
                xanchor="center",
                yanchor="bottom",
            )
        )

    for row_index, country in enumerate(countries):
        y1 = 1.0 - row_index * cell_height
        annotations.append(
            dict(
                x=-0.02,
                y=y1 - cell_height / 2,
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
    if max_replay_br is not None:
        title_filters["Max Replay BR"] = f"{max_replay_br:.1f}"
    title_filters["Min Appearances"] = str(min_appearances)
    title_filters["Players"] = str(len(df))
    title_filters["Unique Players"] = str(df["player.username"].nunique())
    title_filters["Total Replays"] = str(df["session_id"].nunique())
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = (
            ", ".join(country.value for country in country_filters)
        )
    title = title_builder.build_title(
        "Tier Frequency by Country and Player Battle Rating", filters=title_filters
    )
    annotations.extend(
        [
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
            ),
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
            ),
        ]
    )

    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        width=max(get_graph_width("heatmap"), int(num_brs * 40)),
        height=max(420, int(num_countries * 48)),
        margin=dict(l=80, r=120, t=140, b=70),
        plot_bgcolor="white",
        legend=dict(orientation="v", yanchor="top", y=0.95, xanchor="left", x=1.02),
        annotations=annotations,
        xaxis=dict(visible=False, showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(visible=False, showgrid=False, zeroline=False, showticklabels=False),
        legend_itemclick=False,
        legend_itemdoubleclick=False,
    )
    return fig
