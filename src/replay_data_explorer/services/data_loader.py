import json
from pathlib import Path
from typing import Optional

import pandas as pd

from src.common.enums import Country
from src.replay_data_grabber.models import Replay, Player
from src.replay_data_grabber.services import ReplayManagerService
from src.replay_data_explorer.services import BattleRatingTierClassifier


class DataLoaders:
    """
    Convenience class to handle loading stored data into pandas DataFrames for analysis.
    """

    # Lifecycle

    def __init__(self, replay_manager_service: ReplayManagerService):
        self._replay_manager_service = replay_manager_service

        self.battle_rating_tier_classifier = BattleRatingTierClassifier()

    def get_player_performance_data(
        self, player_name: Optional[str] = None, country_filters: list[Country] = []
    ) -> pd.DataFrame:
        """
        Process replay data for a specific player.

        Args:
            replay_manager: ReplayManagerService instance
            player_name: Name of specific player to analyze (if None, uses author)
            country_filters: List of countries to filter by

        Returns:
            DataFrame with processed replay data for the target player
        """
        data = []
        loaded_replays = self._replay_manager_service.loaded_replays

        replay: Replay
        for replay_file_path, replay in loaded_replays.items():
            try:
                # Get target player
                target_player = None
                if player_name:
                    # Find specific player by name
                    for player in replay.players:
                        if player.username == player_name:
                            target_player = player
                            break
                else:
                    # Use author if no specific player name provided
                    target_player = replay.author

                if target_player is None:
                    continue

                if country_filters and target_player.country not in country_filters:
                    continue

                if not target_player.country:
                    print(f"Skipping player with no country in replay {Path(replay_file_path).name}")
                    continue

                # Keep the shape of the replay data, but normalize it to a flat structure
                # TODO: the replay and player models need a to_dict or maybe to_dataframe?
                replay_data = json.loads(replay.to_json())
                player_data = json.loads(target_player.to_json())

                # Remove the players array from replay data
                if "players" in replay_data:
                    del replay_data["players"]

                # Calculate additional player metrics
                battle_rating_delta = round(target_player.battle_rating - replay.battle_rating, 2)
                player_data["battle_rating_delta"] = battle_rating_delta
                player_data["tier_status"] = self.battle_rating_tier_classifier.get_battle_rating_tier_from_delta(
                    battle_rating_delta
                )

                # Flatten the structure by prefixing player fields
                flattened_datum = replay_data.copy()
                for key, value in player_data.items():
                    flattened_datum[f"player.{key}"] = value

                data.append(flattened_datum)

            except Exception as e:
                print(f"Error processing {Path(replay_file_path).name}: {e}")
                continue

        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_global_performance_data(self, country_filters: list[Country] = []) -> pd.DataFrame:
        """
        Process replay data for a all players.

        Args:
            replay_manager: ReplayManagerService instance
            country_filters: List of countries to filter by

        Returns:
            DataFrame with processed replay data for all players
        """
        data = []
        loaded_replays = self._replay_manager_service.loaded_replays

        replay: Replay
        for replay_file_path, replay in loaded_replays.items():
            try:
                # Get replay data once for this replay
                replay_data = json.loads(replay.to_json())

                # Remove the players array from replay data
                if "players" in replay_data:
                    del replay_data["players"]

                # Process each player in the replay
                for player in replay.players:
                    if country_filters and player.country not in country_filters:
                        continue

                    player_data = json.loads(player.to_json())

                    # Calculate additional player metrics
                    battle_rating_delta = round(player.battle_rating - replay.battle_rating, 2)
                    player_data["battle_rating_delta"] = battle_rating_delta
                    player_data["tier_status"] = self.battle_rating_tier_classifier.get_battle_rating_tier_from_delta(
                        battle_rating_delta
                    )

                    # Flatten the structure by prefixing player fields
                    flattened_datum = replay_data.copy()
                    for key, value in player_data.items():
                        flattened_datum[f"player.{key}"] = value

                    data.append(flattened_datum)

            except Exception as e:
                print(f"Error processing {Path(replay_file_path).name}: {e}")
                continue

        return pd.DataFrame(data) if data else pd.DataFrame()
