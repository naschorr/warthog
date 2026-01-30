from src.replay_data_explorer.graphs.initialization import *


def create_bar_score_vs_common_squadmates(
    global_performance_df: pd.DataFrame,
    *,
    player_name,
    display_player_name=None,
    country_filters=[],
    min_battles_threshold=5,
):
    """
    Create an interactive Plotly bar chart showing mean scores by squadmate combinations.

    Shows how the player performs when playing solo, with specific squadmates, or with
    combinations of squadmates.

    Args:
        global_performance_df: DataFrame with performance data
        player_name: Player name to analyze
        display_player_name: Optional display name for title (defaults to player_name)
        country_filters: List of countries to filter by
        min_battles_threshold: Minimum number of battles together to be considered a "common" squadmate

    Returns:
        Plotly figure object
    """
    display_player_name = display_player_name or player_name

    if global_performance_df.empty:
        print("No performance data available for plotting")
        return None

    # Get a copy of the data to avoid modifying the original
    df = global_performance_df.copy()

    # Filter for the author's data
    author_df = df[df["player.username"] == player_name].copy()

    if author_df.empty:
        print(f"No data available for player {player_name}")
        return None

    # Find common squadmates
    common_squadmates = _identify_common_squadmates(df, player_name, min_battles_threshold)

    if not common_squadmates:
        print(f"No common squadmates found for {player_name} (min {min_battles_threshold} battles together)")
        return None

    # Calculate scores for different squadmate combinations
    squadmate_scores = _calculate_squadmate_combination_scores(df, player_name, common_squadmates)

    if not squadmate_scores:
        print("No squadmate combination data available")
        return None

    # Sort by mean score for better visualization
    squadmate_scores_sorted = sorted(squadmate_scores, key=lambda x: x["mean_score"])

    # Extract data for plotting
    labels = [item["label"] for item in squadmate_scores_sorted]
    mean_scores = [item["mean_score"] for item in squadmate_scores_sorted]
    battle_counts = [item["battle_count"] for item in squadmate_scores_sorted]
    std_devs = [item["std_dev"] for item in squadmate_scores_sorted]

    # Create the horizontal bar chart
    fig = go.Figure(
        data=go.Bar(
            x=mean_scores,
            y=labels,
            orientation="h",
            marker=dict(
                color=PLOTLY_SINGLE_COLOR,
                line=dict(color="white", width=1),
            ),
            hovertemplate="<b>%{y}</b><br>"
            + "Mean Score: %{x:.0f}<br>"
            + "Battles: %{customdata[0]}<br>"
            + "Std Dev: %{customdata[1]:.1f}<extra></extra>",
            customdata=list(zip(battle_counts, std_devs)),
        )
    )

    # Calculate overall statistics for the author
    overall_mean = author_df["player.score"].mean()

    # Add overall mean line
    fig.add_vline(
        x=overall_mean,
        line_dash="dot",
        line_color="black",
        annotation_text=f"Overall Mean: {overall_mean:.0f}",
        annotation_position="top right",
        annotation=dict(yshift=15),
    )

    # Build the graph's title
    title_filters = OrderedDict()
    title_filters["Player"] = display_player_name
    title_filters["Battles"] = len(author_df)
    title_filters["Min Battles Together"] = min_battles_threshold
    if country_filters:
        title_filters[f"Countr{'y' if len(country_filters) == 1 else 'ies'}"] = ", ".join(
            [country.value for country in country_filters]
        )
    title = title_builder.build_title("Mean Score by Squadmate Combination", filters=title_filters)

    # Update layout
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 16}},
        xaxis=dict(
            title=f"Mean Score of {display_player_name}",
            side="bottom",
            gridcolor="lightgray",
            gridwidth=1,
            zeroline=False,
        ),
        yaxis=dict(
            title="Squadmate Combination",
            side="left",
            gridcolor="lightgray",
            gridwidth=1,
        ),
        width=800,
        height=max(400, len(labels) * 40),  # Dynamic height based on number of combinations
        plot_bgcolor="white",
        margin=dict(l=200, r=80, t=80, b=100),  # Extra left margin for labels
        hovermode="closest",
    )

    # Add battle count annotations at the end of each bar
    for i, (label, score, count) in enumerate(zip(labels, mean_scores, battle_counts)):
        fig.add_annotation(
            x=score,
            y=label,
            text=f"{int(count)} battle{'s' if count != 1 else ''}",
            showarrow=False,
            font=dict(size=10, color="white"),
            xanchor="right",
            xshift=-5,  # Shift left from the end of the bar
        )

    return fig


def _identify_common_squadmates(df: pd.DataFrame, player_name: str, min_battles_threshold: int) -> set:
    """
    Identify squadmates who frequently play with the author.

    Args:
        df: Global performance DataFrame
        player_name: Author's username
        min_battles_threshold: Minimum number of battles together to be considered common

    Returns:
        Set of common squadmate usernames
    """
    # Track squadmate co-occurrences
    squadmate_counts = Counter()

    # Get all sessions where the author participated
    author_sessions = df.loc[
        df["player.username"] == player_name, ["session_id", "player.team", "player.squad", "player.auto_squad"]
    ].copy()

    # For each session the author participated in
    for _, author_row in author_sessions.iterrows():
        session_id = author_row["session_id"]
        author_team = author_row["player.team"]
        author_squad = author_row["player.squad"]
        author_auto_squad = author_row["player.auto_squad"]

        # Skip if author was auto-squadded or not in a squad
        if author_auto_squad or pd.isna(author_squad) or author_squad == "":
            continue

        # Find other players in the same squad in this session
        squad_mask = (
            (df["session_id"] == session_id)
            & (df["player.team"] == author_team)
            & (df["player.squad"] == author_squad)
            & (df["player.username"] != player_name)
        )
        squad_members = df.loc[squad_mask, "player.username"].unique()

        # Count co-occurrences
        for squadmate in squad_members:
            squadmate_counts[squadmate] += 1

    # Filter to only squadmates with minimum threshold
    common_squadmates = {squadmate for squadmate, count in squadmate_counts.items() if count >= min_battles_threshold}

    return common_squadmates


def _calculate_squadmate_combination_scores(df: pd.DataFrame, player_name: str, common_squadmates: set) -> list[dict]:
    """
    Calculate mean scores for different squadmate combinations.

    Args:
        df: Global performance DataFrame
        player_name: Author's username
        common_squadmates: Set of common squadmate usernames

    Returns:
        List of dictionaries with squadmate combination statistics
    """
    # Track scores for each combination
    combination_scores = defaultdict(list)

    # Get all sessions where the author participated
    author_sessions = df.loc[
        df["player.username"] == player_name,
        ["session_id", "player.team", "player.squad", "player.score", "player.auto_squad"],
    ].copy()

    # For each session the author participated in
    for _, author_row in author_sessions.iterrows():
        session_id = author_row["session_id"]
        author_team = author_row["player.team"]
        author_squad = author_row["player.squad"]
        author_score = author_row["player.score"]
        author_auto_squad = author_row["player.auto_squad"]

        # Check if author was auto-squadded or not in a real squad
        if author_auto_squad or pd.isna(author_squad) or author_squad == "":
            # Solo / Auto-squad play
            combination_scores[frozenset()].append(author_score)

        else:
            # Find other players in the same squad in this session
            squad_mask = (
                (df["session_id"] == session_id)
                & (df["player.team"] == author_team)
                & (df["player.squad"] == author_squad)
                & (df["player.username"] != player_name)
            )
            squad_members = df.loc[squad_mask, "player.username"].unique()

            # Filter to only common squadmates
            common_members_in_squad = [m for m in squad_members if m in common_squadmates]

            # If none of the squad members are in the common list, treat as solo
            # (random squad up with non-common players)
            if not common_members_in_squad:
                combination_scores[frozenset()].append(author_score)
            else:
                # Create a frozenset of the common squadmates in this battle
                combination = frozenset(common_members_in_squad)
                combination_scores[combination].append(author_score)

    # Calculate statistics for each combination
    results = []
    for combination, scores in combination_scores.items():
        if not scores:
            continue

        # Create a readable label
        if not combination:
            label = "Solo / Random Squad"
        else:
            sorted_members = sorted(combination, key=str.lower)
            label = " + ".join(sorted_members)

        results.append(
            {
                "label": label,
                "mean_score": np.mean(scores),
                "std_dev": np.std(scores) if len(scores) > 1 else 0.0,
                "battle_count": len(scores),
                "squadmates": combination,
            }
        )

    return results
