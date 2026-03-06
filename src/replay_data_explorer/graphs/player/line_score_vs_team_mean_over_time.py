from datetime import timedelta

from src.replay_data_explorer.graphs.initialization import *
from src.replay_data_explorer.graphs.player.scatter_score_vs_team_mean import _calculate_team_avg_scores
from src.replay_data_explorer.configuration.configuration_models import TransactionPremiumAccount


def create_line_score_vs_team_mean_over_time(
    player_performance_df: pd.DataFrame,
    global_performance_df: pd.DataFrame,
    *,
    player_name: Optional[str] = None,
    country_filters: list = [],
    transactions: list = [],
    rolling_window: int = 10,
):
    """
    Create a line graph showing the player's score relative to their team mean over time.

    Y = 0 means the player scored exactly the team average. Positive values
    mean the player outperformed their team; negative values mean they
    underperformed. A rolling mean and cumulative mean are both plotted on a
    sequential battle index X axis with sparse date tick labels.

    Transaction events from config are overlaid as vertical marker lines at their
    timestamps, colored by transaction flavor. TransactionPremiumAccount entries
    additionally render a transparent filled region spanning their duration.
    All transaction flavors are independently toggleable via the legend.

    Args:
        player_performance_df: DataFrame with per-battle player performance data.
        global_performance_df: DataFrame with all-player performance data (used
            to compute team averages).
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

    # --- Compute score relative to team mean --------------------------------
    team_avg_scores = _calculate_team_avg_scores(df, global_performance_df)
    df["team_avg_score"] = team_avg_scores
    df = df.dropna(subset=["team_avg_score"]).reset_index(drop=True)

    if df.empty:
        print("No valid team average data available for plotting")
        return go.Figure()

    df["score_diff"] = df["player.score"] - df["team_avg_score"]
    df["battle_index"] = range(len(df))
    df["date"] = df["start_time"].dt.date

    df["rolling_score_diff"] = df["score_diff"].rolling(window=rolling_window, min_periods=1).mean()
    df["cumulative_score_diff"] = df["score_diff"].expanding().mean()

    # --- Sparse date tick labels --------------------------------------------
    total_battles = len(df)
    step = max(7, total_battles // 7)
    label_indices = list(range(0, total_battles, step))
    if label_indices[-1] != total_battles - 1:
        label_indices.append(total_battles - 1)
    tickvals = [df.iloc[i]["battle_index"] for i in label_indices]
    ticktext = [str(df.iloc[i]["date"]) for i in label_indices]

    # --- Y range (based on plotted lines, not raw per-battle values) --------
    data_min = min(df["rolling_score_diff"].min(), df["cumulative_score_diff"].min())
    data_max = max(df["rolling_score_diff"].max(), df["cumulative_score_diff"].max())
    pad = max(5, (data_max - data_min) * 0.08)
    y_min = data_min - pad
    y_max = data_max + pad

    fig = go.Figure()

    # --- Rolling score diff line --------------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df["battle_index"],
            y=df["rolling_score_diff"],
            mode="lines+markers",
            name=f"Rolling ({rolling_window} battles)",
            line=dict(color=PLOTLY_SINGLE_COLOR, width=2),
            marker=dict(size=4, color=PLOTLY_SINGLE_COLOR),
            customdata=df[["date", "score_diff", "player.score", "team_avg_score"]],
            hovertemplate=(
                "<b>Rolling Score Diff</b><br>"
                "Date: %{customdata[0]}<br>"
                "Rolling Mean: %{y:.0f}<br>"
                "This Battle: %{customdata[1]:.0f} "
                "(scored %{customdata[2]:.0f} vs team mean %{customdata[3]:.0f})"
                "<extra></extra>"
            ),
        )
    )

    # --- Cumulative score diff line -----------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df["battle_index"],
            y=df["cumulative_score_diff"],
            mode="lines",
            name="Cumulative",
            line=dict(color="#808080", width=1.5, dash="dot"),
            customdata=df[["date"]],
            hovertemplate=(
                "<b>Cumulative Score Diff</b><br>"
                "Date: %{customdata[0]}<br>"
                "Cumulative Mean: %{y:.0f}<extra></extra>"
            ),
        )
    )

    # --- 0 reference line ---------------------------------------------------
    fig.add_hline(y=0, line_color="lightgray", line_width=1)

    # --- Transaction overlays -----------------------------------------------
    flavor_legend_shown: set[str] = set()

    for transaction in transactions:
        flavor = transaction.flavor.value
        color = PLOTLY_TRANSACTION_COLORS.get(flavor, "#FF8C00")
        display_name = PLOTLY_TRANSACTION_DISPLAY.get(flavor, flavor.replace("_", " ").title())
        ts = pd.Timestamp(transaction.timestamp).tz_localize(None)
        show_legend = flavor not in flavor_legend_shown

        after = df[df["start_time"] >= ts]
        if after.empty:
            start_idx = total_battles - 1
        else:
            start_idx = int(after.iloc[0]["battle_index"])

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
    title = title_builder.build_title("Score vs Team Mean Over Time", filters=title_filters)

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
            title="Score Relative to Team Mean",
            gridcolor="lightgray",
            gridwidth=1,
            range=[y_min, y_max],
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
