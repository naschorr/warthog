from src.replay_data_explorer.graphs.initialization import *


def create_bar_tier_distribution(player_performance_df: pd.DataFrame, *, player_name=None, country_filters=[]):
    """
    Create an interactive Plotly bar chart showing battle rating deltas by date, grouped by tier status.

    Args:
        player_performance_df: DataFrame with performance data
        player_name: Optional player name for title
        country_filters: List of countries to filter by

    Returns:
        Plotly figure object
    """
    if player_performance_df.empty:
        print("No data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = player_performance_df.copy()

    # Normalize BR delta from -1 to 0 scale to -0.5 to +0.5 scale
    df["player.battle_rating_delta_normalized"] = df["player.battle_rating_delta"] + 0.5
    df["player.battle_rating_delta_normalized"] = df["player.battle_rating_delta_normalized"].clip(-0.5, 0.5)

    # Ensure start_time is datetime type (in case it was serialized as string)
    if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
        df["start_time"] = pd.to_datetime(df["start_time"])

    # Extract date only (without time) for display
    df["date"] = df["start_time"].dt.date

    # Sort by timestamp to show battles in chronological order
    df = df.sort_values("start_time").reset_index(drop=True)

    # Create a sequential index for each battle (x-axis position)
    df["battle_index"] = range(len(df))

    # Create subset of battle indices for x-axis labels to avoid cluttering
    # Show labels at regular intervals but not too many
    total_battles = len(df)
    step = max(7, total_battles // 7)
    label_indices = list(range(0, total_battles, step))
    # Always include the last battle
    if label_indices[-1] != total_battles - 1 or label_indices[-1]:
        label_indices.append(total_battles - 1)

    # Create tick labels showing dates for the selected battles
    tickvals = [df.iloc[i]["battle_index"] for i in label_indices]
    ticktext = [str(df.iloc[i]["date"]) for i in label_indices]

    fig = go.Figure()

    # Get unique countries for filtering
    available_countries = sorted(df["player.country"].unique())

    # Create individual bars for each battle, grouped by country for legend filtering
    for country in available_countries:
        country_data = df[df["player.country"] == country]
        country_legend_created = False

        if not country_data.empty:
            # Create separate traces for each tier status within this country
            for tier_status in PLOTLY_BATTLE_RATING_TIER_STATUS_ORDER:
                tier_country_data = country_data[country_data["player.tier_status"] == tier_status]

                if len(tier_country_data) > 0:
                    tier_status_display = (
                        battle_rating_tier_display_builder.get_battle_rating_tier_display_from_battle_rating_tier(
                            tier_status
                        )
                    )

                    # Use tier status color but make it distinguishable by country
                    base_color = PLOTLY_BATTLE_RATING_TIER_STATUS_COLORS[tier_status]

                    fig.add_trace(
                        go.Bar(
                            x=tier_country_data["battle_index"],  # Use sequential battle index for positioning
                            y=tier_country_data["player.battle_rating_delta_normalized"],
                            name=f"{country}",  # Group by country for legend filtering
                            legendgroup=country,  # Group all tier statuses for this country
                            marker=dict(color=base_color, line=dict(color=base_color, width=0.5)),
                            width=0.5,  # Set consistent bar width
                            customdata=np.column_stack(
                                [
                                    tier_country_data["player.country"],
                                    tier_country_data["player.battle_rating_delta"],
                                    [tier_status_display] * len(tier_country_data),
                                    [str(date) for date in tier_country_data["date"]],
                                    tier_country_data["start_time"],
                                ]
                            ),
                            hovertemplate=(
                                "<b>%{customdata[0]}</b><br>"
                                + "Date: %{customdata[3]}<br>"
                                + "Time: %{customdata[4]}<br>"
                                + "BR Delta: %{customdata[1]:.2f}<br>"
                                + "Normalized: %{y:.2f}<br>"
                                + "Tier Status: %{customdata[2]}<br>"
                                + "<extra></extra>"
                            ),
                            showlegend=country_legend_created == False,  # Only show legend for first tier status
                        )
                    )

                    country_legend_created = True

    # Build the graph's title
    title_filters = OrderedDict()
    if player_name:
        title_filters["Player"] = player_name
    title_filters["Battles"] = len(df)
    title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
        [country.value for country in country_filters]
    )
    title = title_builder.build_title("Battle Rating Delta Over Time by Tier Status", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(
            title="Battle Timeline (Chronological Order)",
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False,
            tickangle=45 if len(tickvals) > 7 else 0,
            tickvals=tickvals,
            ticktext=ticktext,
            range=[-0.5, total_battles - 0.5],  # Show all battles with some padding
        ),
        yaxis=dict(
            title="Battle Rating Delta",
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=True,
            zerolinecolor="black",  # Highlight the zero line
            zerolinewidth=2,
            range=[-0.55, 0.55],  # Enforce the expected range
            tickvals=[-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            ticktext=["-0.5", "-0.4", "-0.3", "-0.2", "-0.1", "0.0", "0.1", "0.2", "0.3", "0.4", "0.5"],
        ),
        plot_bgcolor="white",
        width=1200,
        height=600,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            title="Countries",
            traceorder="normal",
        ),
        margin=dict(r=200),  # Add right margin for legend
        bargap=0.0,
        bargroupgap=0.0,
        hovermode="closest",
    )

    return fig
