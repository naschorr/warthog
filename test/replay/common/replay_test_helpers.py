"""
Shared dataclasses and helpers for replay regression tests.

Provides:
  - ``KillDetailTruth`` / ``DeathDetailTruth`` – expected kill/death records.
  - ``PlayerTruth`` – per-player ground-truth bundle.
  - ``find_kill`` / ``find_death`` – matchers that compare truth against parsed
    replay JSON output.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Source-of-truth dataclasses
# ---------------------------------------------------------------------------

DEFAULT_TIMESTAMP_TOLERANCE_S = 5  # ±seconds when matching time_utc against battle-log timestamps


@dataclass
class KillDetailTruth:
    """A kill that must be matchable in the player's kills.vehicles list."""

    killer_vehicle: str
    victim_username: str | None = None
    victim_vehicle: str | None = None
    # Elapsed seconds from battle start, derived from the battle log timestamp.
    # When the parsed record also carries time_utc, matching is constrained to
    # ±tolerance seconds.
    time_seconds: int | None = None


@dataclass
class DeathDetailTruth:
    """A death that must be matchable in the player's deaths.vehicles list."""

    victim_vehicle: str
    killer_username: str | None = None
    killer_vehicle: str | None = None
    # Elapsed seconds from battle start, derived from the battle log timestamp.
    time_seconds: int | None = None


@dataclass
class PlayerTruth:
    username: str
    team: int  # 1 or 2  (from BLK)
    kills_ground: int  # from BLK
    kills_air: int  # from BLK
    deaths_total: int  # from BLK
    # Award IDs as they appear in the parsed output.  Duplicates encode expected
    # minimum counts (e.g. listing "defender_tank" 3 times asserts count >= 3).
    awards: list[str] = field(default_factory=list)
    # Individual kill / death records that must be findable in the parsed lists.
    kill_details: list[KillDetailTruth] = field(default_factory=list)
    death_details: list[DeathDetailTruth] = field(default_factory=list)
    # True only for the player who recorded the replay.  Their kill/death detail
    # assertions are hard failures; all others are xfail(strict=False).
    is_author: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def elapsed_seconds(time_utc_str: str | None, battle_start: datetime) -> float | None:
    """Convert a time_utc ISO string to elapsed seconds from *battle_start*."""
    if time_utc_str is None:
        return None
    dt = datetime.fromisoformat(time_utc_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - battle_start).total_seconds()


def find_kill(
    kills: list[dict],
    truth: KillDetailTruth,
    battle_start: datetime | None = None,
    tolerance: float = DEFAULT_TIMESTAMP_TOLERANCE_S,
) -> dict | None:
    """Return the first kill detail matching all non-None fields of *truth*."""
    for kd in kills:
        if kd.get("killer_vehicle") != truth.killer_vehicle:
            continue
        if truth.victim_username is not None and kd.get("victim_username") != truth.victim_username:
            continue
        if truth.victim_vehicle is not None and kd.get("victim_vehicle") != truth.victim_vehicle:
            continue
        if truth.time_seconds is not None and battle_start is not None:
            et = elapsed_seconds(kd.get("time_utc"), battle_start)
            if et is not None and abs(et - truth.time_seconds) > tolerance:
                continue
        return kd
    return None


def find_death(
    deaths: list[dict],
    truth: DeathDetailTruth,
    battle_start: datetime | None = None,
    tolerance: float = DEFAULT_TIMESTAMP_TOLERANCE_S,
) -> dict | None:
    """Return the first death detail matching all non-None fields of *truth*."""
    for dd in deaths:
        if dd.get("victim_vehicle") != truth.victim_vehicle:
            continue
        if truth.killer_username is not None and dd.get("killer_username") != truth.killer_username:
            continue
        if truth.killer_vehicle is not None and dd.get("killer_vehicle") != truth.killer_vehicle:
            continue
        if truth.time_seconds is not None and battle_start is not None:
            et = elapsed_seconds(dd.get("time_utc"), battle_start)
            if et is not None and abs(et - truth.time_seconds) > tolerance:
                continue
        return dd
    return None


def assert_awards_present(actual_awards: list[str], expected_awards: list[str], username: str) -> None:
    """Assert every award in *expected_awards* is present (with minimum counts)."""
    for award_id in set(expected_awards):
        assert award_id in actual_awards, f"{username}: expected award '{award_id}'"


def assert_award_counts(actual_awards: list[str], expected_awards: list[str], username: str) -> None:
    """Assert minimum occurrence counts for each expected award."""
    actual_counts = Counter(actual_awards)
    for award_id, expected_min in Counter(expected_awards).items():
        actual = actual_counts[award_id]
        assert actual >= expected_min, f"{username}: expected at least {expected_min}x '{award_id}', got {actual}"
