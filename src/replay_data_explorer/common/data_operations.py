import pandas as pd


def bayesian_smooth(
    leavers: "pd.Series",
    appearances: "pd.Series",
    smoothing_factor: int = 20,
) -> "pd.Series":
    """
    Apply additive (Laplace / Bayesian) smoothing to a proportion series.

    Each cell's raw rate is blended toward the global mean in proportion to
    how few observations it has:

        smoothed = (successes + α * prior) / (n + α)

    Args:
        leavers:          Per-cell success counts (e.g. one-death leavers).
        appearances:      Per-cell observation counts.
        smoothing_factor: Equivalent phantom observations at the prior rate (α).
                          Higher values pull sparse cells harder toward the mean.

    Returns:
        Series of smoothed proportions in the range [0, 1].
    """
    total_leavers = leavers.sum()
    total_appearances = appearances.sum()
    prior = total_leavers / total_appearances if total_appearances > 0 else 0.0
    return (leavers + smoothing_factor * prior) / (appearances + smoothing_factor)
