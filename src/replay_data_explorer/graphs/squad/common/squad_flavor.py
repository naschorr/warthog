from enum import Enum

import pandas as pd


class SquadFlavor(str, Enum):
    SOLO = "Solo"
    SQUAD_2 = "Squad of 2"
    SQUAD_3 = "Squad of 3"
    SQUAD_4 = "Squad of 4"


def add_squad_flavor_column(global_performance_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a squad_flavor column to the DataFrame indicating the squad size for each player.

    Args:
        global_performance_df: DataFrame with player performance data

    Returns:
        DataFrame with added squad_flavor column
    """
    df = global_performance_df.copy()

    # Initialize squad_flavor column
    df["squad_flavor"] = SquadFlavor.SOLO.value

    # Handle players with valid squads (not auto-squad and not null/empty)
    valid_squad_mask = df["player.squad"].notna() & (df["player.squad"] != "") & (~df["player.auto_squad"])

    if valid_squad_mask.any():
        # For each unique combination of session, team and squad, calculate squad size
        squad_groups = df[valid_squad_mask].groupby(["session_id", "player.team", "player.squad"])

        for group_key, group in squad_groups:
            squad_size = len(group)
            indices = group.index

            if squad_size == 1:
                squad_flavor = SquadFlavor.SOLO.value
            elif squad_size == 2:
                squad_flavor = SquadFlavor.SQUAD_2.value
            elif squad_size == 3:
                squad_flavor = SquadFlavor.SQUAD_3.value
            elif squad_size == 4:
                squad_flavor = SquadFlavor.SQUAD_4.value
            else:
                # For squads larger than 4, cap at SQUAD_4
                squad_flavor = SquadFlavor.SQUAD_4.value

            df.loc[indices, "squad_flavor"] = squad_flavor

    return df
