from pathlib import Path

import pandas as pd

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

    def get_performance_data(self, country_filters=None, player_name=None) -> pd.DataFrame:
        """
        Process replay data for a specific player.

        Args:
            replay_manager: ReplayManagerService instance
            country_filters: List of countries to filter by
            player_name: Name of specific player to analyze (if None, uses author)

        Returns:
            DataFrame with processed replay data
        """
        data = []
        loaded_replays = self._replay_manager_service.loaded_replays

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

                data.append(
                    {
                        "battle_rating": target_player.battle_rating,
                        "score": target_player.score,
                        "country": target_player.country.value,
                        "player_name": target_player.username,
                        "replay_file": Path(replay_file_path).name,
                        "timestamp": replay.start_time,
                        "status": replay.status,
                        "team": target_player.team,
                        "squad": target_player.squad,
                        "auto_squad": target_player.auto_squad,
                        "players": replay.players,
                    }
                )

            except Exception as e:
                print(f"Error processing {Path(replay_file_path).name}: {e}")
                continue

        return pd.DataFrame(data) if data else pd.DataFrame()

    def get_tier_data(self, country_filters=None, player_name=None):
        """
        Calculate tier status (uptier/downtier) for each battle.

        Args:
            replay_manager: ReplayManagerService instance
            country_filters: List of countries to filter by
            player_name: Name of specific player to analyze (if None, uses author)

        Returns:
            DataFrame with tier status information for each replay
        """
        tier_data = []
        loaded_replays = self._replay_manager_service.loaded_replays

        for replay_file_path, replay in loaded_replays.items():
            try:
                # Get target player
                target_player = None
                if player_name:
                    for player in replay.players:
                        if player.username == player_name:
                            target_player = player
                            break
                else:
                    target_player = replay.author

                if target_player is None:
                    continue

                if country_filters and target_player.country not in country_filters:
                    continue

                tier_data.append(
                    {
                        "replay_file": Path(replay_file_path).name,
                        "player_br": target_player.battle_rating,
                        "br_delta": target_player.battle_rating - replay.battle_rating,
                        "tier_status": self.battle_rating_tier_classifier.get_battle_rating_tier(target_player, replay),
                    }
                )

            except Exception as e:
                print(f"Error processing tier data for {Path(replay_file_path).name}: {e}")
                continue

        return pd.DataFrame(tier_data) if tier_data else pd.DataFrame()
