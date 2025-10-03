from src.replay_data_explorer.enums import BattleRatingTier
from src.replay_data_grabber.models import Player, Replay


class BattleRatingTierClassifier:
    @staticmethod
    def get_battle_rating_tier_from_delta(delta: float) -> BattleRatingTier:
        """
        Get the battle rating tier for a player based on their battle rating and the match's battle rating.

        Tiers (for a 1.0 BR match):
        - Uptier: BR == 0
        - Partial Uptier: BR > 0 and BR < 0.4
        - Balanced: 0.4 >= BR <= 0.6
        - Partial Downtier: BR > 0.6 and BR < 1.0
        - Downtier: BR == 1.0
        """
        if delta >= 0:
            return BattleRatingTier.DOWNTIER
        elif 0 > delta > -0.4:
            return BattleRatingTier.PARTIAL_DOWNTIER
        elif -0.4 >= delta >= -0.6:
            return BattleRatingTier.BALANCED
        elif -0.6 > delta > -1.0:
            return BattleRatingTier.PARTIAL_UPTIER
        else:  # delta <= -1.0
            return BattleRatingTier.UPTIER

    @staticmethod
    def get_battle_rating_tier(player: Player, replay: Replay) -> BattleRatingTier:
        """
        Get the battle rating tier for a player based on their battle rating and the match's battle rating.

        Tiers (for a 1.0 BR match):
        - Uptier: BR == 0
        - Partial Uptier: BR > 0 and BR < 0.4
        - Balanced: 0.4 >= BR <= 0.6
        - Partial Downtier: BR > 0.6 and BR < 1.0
        - Downtier: BR == 1.0
        """
        delta = round(player.battle_rating - replay.battle_rating, 2)
        return BattleRatingTierClassifier.get_battle_rating_tier_from_delta(delta)
