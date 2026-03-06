from datetime import timedelta

from src.replay_data_explorer.graphs.initialization import *
from src.replay_data_explorer.configuration.configuration_models import TransactionPremiumAccount


def create_line_win_rate_over_time(
    player_performance_df: pd.DataFrame,
    *,
    player_name: Optional[str] = None,
    country_filters: list = [],
    transactions: list = [],
    rolling_window: int = 10,
):
    """
    Create a line graph showing player win rate over time.

    Plots a rolling win rate (over the last N non-left battles) and a cumulative
    win rate. 'Left Early' battles are excluded from the win rate denominator.

    Transaction events from config are overlaid as vertical marker lines at their
    timestamps, colored by transaction flavor. TransactionPremiumAccount entries
    additionally render a transparent filled region spanning their duration.
    All transaction flavors are independently toggleable via the legend.

    Args:
        player_performance_df: DataFrame with player performance data.
        player_name: Optional name used in the graph title.
        country_filters: Optional list of Country enums for filtering.
        transactions: Optional list of AnyTransaction objects to overlay.
        rolling_window: Number of battles used for the rolling win rate (default 10).

    Returns:
        Plotly Figure object.
    """
    if player_performance_df.empty:
        print("No performance data available for plotting")
        return go.Figure()

    df = player_performance_df.copy()

    # Ensure start_time is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["start_time"]):
        df["start_time"] = pd.to_datetime(df["start_time"])

    df = df.sort_values("start_time").reset_index(drop=True)

    # --- Win rate calculation ------------------------------------------------
    # Exclude "left" battles; they don't count as wins or losses
    df_counted = df[df["status"].isin(["success", "fail"])].copy()

    if df_counted.empty:
        print("No win/loss data available for plotting")
        return go.Figure()

    df_counted = df_counted.reset_index(drop=True)
    df_counted["battle_index"] = range(len(df_counted))
    df_counted["date"] = df_counted["start_time"].dt.date
    df_counted["is_win"] = (df_counted["status"] == "success").astype(int)
    df_counted["rolling_win_rate"] = df_counted["is_win"].rolling(window=rolling_window, min_periods=1).mean() * 100
    df_counted["cumulative_win_rate"] = df_counted["is_win"].expanding().mean() * 100

    # --- Sparse date tick labels (same pattern as bar_tier_distribution) ----
    total_battles = len(df_counted)
    step = max(7, total_battles // 7)
    label_indices = list(range(0, total_battles, step))
    if label_indices[-1] != total_battles - 1:
        label_indices.append(total_battles - 1)
    tickvals = [df_counted.iloc[i]["battle_index"] for i in label_indices]
    ticktext = [str(df_counted.iloc[i]["date"]) for i in label_indices]

    fig = go.Figure()

    # --- Rolling win rate ---------------------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df_counted["battle_index"],
            y=df_counted["rolling_win_rate"],
            mode="lines+markers",
            name=f"Rolling ({rolling_window} battles)",
            line=dict(color=PLOTLY_SINGLE_COLOR, width=2),
            marker=dict(size=4, color=PLOTLY_SINGLE_COLOR),
            customdata=df_counted[["date", "start_time"]],
            hovertemplate=(
                "<b>Rolling Win Rate</b><br>" "Date: %{customdata[0]}<br>" "Win Rate: %{y:.1f}%<extra></extra>"
            ),
        )
    )

    # --- Cumulative win rate ------------------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df_counted["battle_index"],
            y=df_counted["cumulative_win_rate"],
            mode="lines",
            name="Cumulative",
            line=dict(color="#808080", width=1.5, dash="dot"),
            customdata=df_counted[["date"]],
            hovertemplate=(
                "<b>Cumulative Win Rate</b><br>" "Date: %{customdata[0]}<br>" "Win Rate: %{y:.1f}%<extra></extra>"
            ),
        )
    )

    # --- 50% reference line -------------------------------------------------
    fig.add_hline(y=50, line_dash="dash", line_color="lightgray", line_width=1)

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

        # Find the index of the first battle at or after the transaction timestamp
        after = df_counted[df_counted["start_time"] >= ts]
        if after.empty:
            start_idx = total_battles - 1
        else:
            start_idx = int(after.iloc[0]["battle_index"])

        # PremiumAccount: fill the region covering all battles within its duration
        if isinstance(transaction, TransactionPremiumAccount):
            end_ts = ts + timedelta(days=transaction.duration_days)
            within = df_counted[df_counted["start_time"] <= end_ts]
            end_idx = int(within.iloc[-1]["battle_index"]) if not within.empty else start_idx
            fig.add_trace(
                go.Scatter(
                    x=[start_idx, end_idx, end_idx, start_idx, start_idx],
                    y=[0, 0, 100, 100, 0],
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
                y=[0, 100],
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
    title = title_builder.build_title("Win Rate Over Time", filters=title_filters)

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
            title="Win Rate (%)",
            gridcolor="lightgray",
            gridwidth=1,
            range=[0, 100],
            ticksuffix="%",
            zeroline=False,
        ),
        plot_bgcolor="white",
        width=get_graph_width(),
        height=500,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(r=150),
        hovermode="closest",
    )

    return fig
