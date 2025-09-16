from src.replay_data_explorer.enums import BattleRatingTier
from src.replay_data_grabber.models import Player, Replay


class BattleRatingTierClassifier:
    @staticmethod
    def get_battle_rating_tier(player: Player, replay: Replay) -> BattleRatingTier:
        """
        Get the battle rating tier for a player based on their battle rating and the match's battle rating.

        Tiers (for a 1.0 BR match):
        - Downtier: BR == 0
        - Partial Downtier: BR > 0 and BR < 0.4
        - Balanced: 0.4 >= BR <= 0.6
        - Partial Uptier: BR > 0.6 and BR < 1.0
        - Uptier: BR == 1.0
        """
        delta = round(replay.battle_rating - player.battle_rating, 2)

        if delta <= 0:
            return BattleRatingTier.UPTIER
        elif 0 < delta < 0.4:
            return BattleRatingTier.PARTIAL_UPTIER
        elif 0.4 <= delta <= 0.6:
            return BattleRatingTier.BALANCED
        elif 0.6 < delta < 1.0:
            return BattleRatingTier.PARTIAL_DOWNTIER
        else:  # delta >= 1.0
            return BattleRatingTier.DOWNTIER
