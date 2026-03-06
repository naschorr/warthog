from datetime import timedelta

from src.replay_data_explorer.graphs.initialization import *
from src.replay_data_explorer.configuration.configuration_models import TransactionPremiumAccount


def create_line_br_delta_over_time(
    player_performance_df: pd.DataFrame,
    *,
    player_name: Optional[str] = None,
    country_filters: list = [],
    transactions: list = [],
    rolling_window: int = 10,
):
    """
    Create a line graph showing rolling average battle rating delta over time.

    Plots a rolling mean BR delta (over the last N battles) and a cumulative
    mean BR delta. All battles are included regardless of outcome, since BR
    delta is available for every battle.

    BR delta is normalized to the –0.5 to +0.5 scale (matching the bar tier distribution
    graph): +0.5 = full downtier, 0 = balanced, –0.5 = full uptier.

    Transaction events from config are overlaid as vertical marker lines at their
    timestamps, colored by transaction flavor. TransactionPremiumAccount entries
    additionally render a transparent filled region spanning their duration.
    All transaction flavors are independently toggleable via the legend.

    Args:
        player_performance_df: DataFrame with player performance data.
        player_name: Optional name used in the graph title.
        country_filters: Optional list of Country enums for filtering.
        transactions: Optional list of AnyTransaction objects to overlay.
        rolling_window: Number of battles used for the rolling mean (default 10).

    Returns:
        Plotly Figure object.
    """
    if player_performance_df.empty:
        print("No performance data available for plotting")
        return go.Figure()

    df = player_performance_df.copy()

    # Ensure start_time is tz-naive datetime
    if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
        df["start_time"] = pd.to_datetime(df["start_time"])
    if df["start_time"].dt.tz is not None:
        df["start_time"] = df["start_time"].dt.tz_localize(None)

    df = df.sort_values("start_time").reset_index(drop=True)
    df["battle_index"] = range(len(df))
    df["date"] = df["start_time"].dt.date

    # Normalize BR delta from -1 to 0 scale to -0.5 to +0.5 scale, matching bar_tier_distribution
    df["player.battle_rating_delta_normalized"] = (df["player.battle_rating_delta"] + 0.5).clip(-0.5, 0.5)

    df["rolling_br_delta"] = (
        df["player.battle_rating_delta_normalized"].rolling(window=rolling_window, min_periods=1).mean()
    )
    df["cumulative_br_delta"] = df["player.battle_rating_delta_normalized"].expanding().mean()

    # --- Sparse date tick labels --------------------------------------------
    total_battles = len(df)
    step = max(7, total_battles // 7)
    label_indices = list(range(0, total_battles, step))
    if label_indices[-1] != total_battles - 1:
        label_indices.append(total_battles - 1)
    tickvals = [df.iloc[i]["battle_index"] for i in label_indices]
    ticktext = [str(df.iloc[i]["date"]) for i in label_indices]

    # --- Y range for layout and transaction fills ---------------------------
    y_min = -0.55
    y_max = 0.55

    fig = go.Figure()

    # --- Rolling BR delta line ----------------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df["battle_index"],
            y=df["rolling_br_delta"],
            mode="lines+markers",
            name=f"Rolling ({rolling_window} battles)",
            line=dict(color=PLOTLY_SINGLE_COLOR, width=2),
            marker=dict(size=4, color=PLOTLY_SINGLE_COLOR),
            customdata=df[["date", "player.battle_rating_delta_normalized", "player.battle_rating_delta"]],
            hovertemplate=(
                "<b>Rolling BR Delta</b><br>"
                "Date: %{customdata[0]}<br>"
                "Rolling Mean: %{y:.3f}<br>"
                "This Battle: %{customdata[1]:.3f} (raw: %{customdata[2]:.3f})<extra></extra>"
            ),
        )
    )

    # --- Cumulative BR delta line -------------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df["battle_index"],
            y=df["cumulative_br_delta"],
            mode="lines",
            name="Cumulative",
            line=dict(color="#808080", width=1.5, dash="dot"),
            customdata=df[["date"]],
            hovertemplate=(
                "<b>Cumulative BR Delta</b><br>" "Date: %{customdata[0]}<br>" "Cumulative Mean: %{y:.3f}<extra></extra>"
            ),
        )
    )

    # --- Reference lines ---------------------------------------------------
    fig.add_hline(y=0, line_color="lightgray", line_width=1)

    # --- Transaction overlays -----------------------------------------------
    # Map timestamps to the nearest battle index so overlays align with the
    # sequential x axis rather than a time axis.
    flavor_legend_shown: set[str] = set()

    for transaction in transactions:
        flavor = transaction.flavor.value
        color = PLOTLY_TRANSACTION_COLORS.get(flavor, "#FF8C00")
        display_name = PLOTLY_TRANSACTION_DISPLAY.get(flavor, flavor.replace("_", " ").title())
        ts = pd.Timestamp(transaction.timestamp).tz_localize(None)
        show_legend = flavor not in flavor_legend_shown

        # Find the first battle at or after the transaction timestamp
        after = df[df["start_time"] >= ts]
        if after.empty:
            start_idx = total_battles - 1
        else:
            start_idx = int(after.iloc[0]["battle_index"])

        # PremiumAccount: fill the region covering all battles within its duration
        if isinstance(transaction, TransactionPremiumAccount):
            end_ts = ts + timedelta(days=transaction.duration_days)
            within = df[df["start_time"] <= end_ts]
            end_idx = int(within.iloc[-1]["battle_index"]) if not within.empty else start_idx
            fig.add_trace(
                go.Scatter(
                    x=[start_idx, end_idx, end_idx, start_idx, start_idx],
                    y=[y_min, y_min, y_max, y_max, y_min],
                    mode="none",
                    fill="toself",
                    fillcolor=hex_to_rgba(color, 0.12),
                    name=display_name,
                    legendgroup=f"transaction_{flavor}",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # Vertical marker line at the transaction battle index
        fig.add_trace(
            go.Scatter(
                x=[start_idx, start_idx],
                y=[y_min, y_max],
                mode="lines",
                line=dict(color=color, dash="dot", width=2),
                name=display_name,
                legendgroup=f"transaction_{flavor}",
                showlegend=show_legend,
                hovertemplate=(f"<b>{display_name}</b><br>Date: {ts.strftime('%Y-%m-%d')}<extra></extra>"),
            )
        )

        flavor_legend_shown.add(flavor)

    # --- Title --------------------------------------------------------------
    title_filters: OrderedDict[str, str | None] = OrderedDict()
    if player_name:
        title_filters["Player"] = player_name
    title_filters["Battles"] = str(total_battles)
    if country_filters:
        label = "Country" if len(country_filters) == 1 else "Countries"
        title_filters[label] = ", ".join(c.value for c in country_filters)
    title = title_builder.build_title("Battle Rating Delta Over Time", filters=title_filters)

    # --- Layout -------------------------------------------------------------
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=16)),
        xaxis=dict(
            title="Battle Timeline (Chronological Order)",
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False,
            tickangle=45 if len(tickvals) > 7 else 0,
            tickvals=tickvals,
            ticktext=ticktext,
            range=[-0.5, total_battles - 0.5],
        ),
        yaxis=dict(
            title="Battle Rating Delta (Normalized)",
            gridcolor="lightgray",
            gridwidth=1,
            range=[y_min, y_max],
            zeroline=False,
            tickmode="array",
            tickvals=[-0.5, -0.4, -0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.4, 0.5],
        ),
        plot_bgcolor="white",
        width=get_graph_width(),
        height=500,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(r=150),
        hovermode="closest",
    )

    return fig
