from src.replay_data_explorer.services.battle_rating_tier_classifier import BattleRatingTierClassifier
from src.replay_data_explorer.enums import BattleRatingTier, BattleRatingTierDisplay


class BattleRatingTierDisplayBuilder:
    @staticmethod
    def get_battle_rating_tier_display_from_battle_rating_tier(tier: BattleRatingTier) -> str:
        """
        Get the display text for a battle rating tier.

        Args:
            tier: The BattleRatingTier enum value.

        Returns:
            A string representing the display text of the battle rating tier.
        """
        for key in BattleRatingTierDisplay.__members__.keys():
            if BattleRatingTier[key] == tier:
                return BattleRatingTierDisplay[key].value

        raise ValueError(f"Invalid BattleRatingTier: {tier}")

    @staticmethod
    def get_battle_rating_tier_display_from_delta(delta: float) -> str:
        """
        Get the display text for a battle rating tier based on the delta value.

        Args:
            delta: The difference between the player's battle rating and the match's battle rating.

        Returns:
            A string representing the display text of the battle rating tier.
        """
        tier = BattleRatingTierClassifier.get_battle_rating_tier_from_delta(delta)
        return BattleRatingTierDisplayBuilder.get_battle_rating_tier_display_from_battle_rating_tier(tier)
