"""
Shared dataclasses and helpers for replay regression tests.

Provides:
  - ``KillDetailTruth`` / ``DeathDetailTruth`` – expected kill/death records.
  - ``PlayerTruth`` – per-player ground-truth bundle.
  - ``find_kill`` / ``find_death`` – matchers that compare truth against parsed
    replay JSON output.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Source-of-truth dataclasses
# ---------------------------------------------------------------------------

DEFAULT_TIMESTAMP_TOLERANCE_S = (
    5  # ±seconds when matching time_utc against battle-log timestamps
)


@dataclass
class KillDetailTruth:
    """A kill that must be matchable, optionally without a resolved killer vehicle."""

    killer_vehicle: str | None = None
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
    # Compare the complete award multiset instead of asserting minimum counts.
    awards_exact: bool = False


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
        if (
            truth.killer_vehicle is not None
            and kd.get("killer_vehicle") != truth.killer_vehicle
        ):
            continue
        if (
            truth.victim_username is not None
            and kd.get("victim_username") != truth.victim_username
        ):
            continue
        if (
            truth.victim_vehicle is not None
            and kd.get("victim_vehicle") != truth.victim_vehicle
        ):
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
        if (
            truth.killer_username is not None
            and dd.get("killer_username") != truth.killer_username
        ):
            continue
        if (
            truth.killer_vehicle is not None
            and dd.get("killer_vehicle") != truth.killer_vehicle
        ):
            continue
        if truth.time_seconds is not None and battle_start is not None:
            et = elapsed_seconds(dd.get("time_utc"), battle_start)
            if et is not None and abs(et - truth.time_seconds) > tolerance:
                continue
        return dd
    return None


def assert_awards_present(
    actual_awards: list[str], expected_awards: list[str], username: str
) -> None:
    """Assert every award in *expected_awards* is present (with minimum counts)."""
    for award_id in set(expected_awards):
        assert award_id in actual_awards, f"{username}: expected award '{award_id}'"


def assert_award_counts(
    actual_awards: list[str], expected_awards: list[str], username: str
) -> None:
    """Assert minimum occurrence counts for each expected award."""
    actual_counts = Counter(actual_awards)
    for award_id, expected_min in Counter(expected_awards).items():
        actual = actual_counts[award_id]
        assert (
            actual >= expected_min
        ), f"{username}: expected at least {expected_min}x '{award_id}', got {actual}"


def assert_exact_kills(
    actual: list[dict],
    expected: list[KillDetailTruth],
    username: str,
    battle_start: datetime,
) -> None:
    """Assert a complete kill-detail list matches its battle-log truths."""
    unmatched = list(actual)
    for truth in expected:
        matched = find_kill(unmatched, truth, battle_start)
        assert matched is not None, f"{username}: battle-log kill not found: {truth}"
        unmatched.remove(matched)
    assert not unmatched, f"{username}: unexpected parsed kill details: {unmatched}"


def assert_exact_deaths(
    actual: list[dict],
    expected: list[DeathDetailTruth],
    username: str,
    battle_start: datetime,
) -> None:
    """Assert a complete death-detail list matches its battle-log truths."""
    unmatched = list(actual)
    for truth in expected:
        matched = find_death(unmatched, truth, battle_start)
        assert matched is not None, f"{username}: battle-log death not found: {truth}"
        unmatched.remove(matched)
    assert not unmatched, f"{username}: unexpected parsed death details: {unmatched}"


class ReplayBattleLogAssertions:
    """Shared fixture loading, mapping, and source-coverage assertions."""

    BATTLE_LOG_PATH: Path
    REPLAY_TRUTH_DATA: dict[str, Any]
    REQUIRE_MUNITION_LINES = False

    _MUNITION_TARGET_PATTERN = re.compile(
        r"\b(?:\d+(?:[.,]\d+)?\s*(?:lbs?|kgs?|pounds?|kilograms?)\b|"
        r"(?:bomb|rocket|missile|torpedo|mine|shell|projectile|grenade)s?\b)",
        re.IGNORECASE,
    )

    @staticmethod
    def load_truth_data(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def build_event_truths(
        event_data: dict[str, Any], player_names: list[str]
    ) -> tuple[dict[str, list[KillDetailTruth]], dict[str, list[DeathDetailTruth]]]:
        kills = {name: [] for name in player_names}
        deaths = {name: [] for name in player_names}
        for event in event_data["events"]:
            killer = event["killer_username"]
            victim = event["victim_username"]
            elapsed = (
                event["time_seconds"] if event.get("time_matchable", True) else None
            )
            killer_vehicle = event["killer_vehicle"]
            victim_vehicle = event["victim_vehicle"]
            kills[killer].append(
                KillDetailTruth(
                    killer_vehicle,
                    victim_username=victim,
                    victim_vehicle=victim_vehicle,
                    time_seconds=elapsed,
                )
            )
            if victim is not None and victim_vehicle is not None:
                deaths[victim].append(
                    DeathDetailTruth(
                        victim_vehicle,
                        killer_username=killer,
                        killer_vehicle=killer_vehicle,
                        time_seconds=elapsed,
                    )
                )

        for entries in (*kills.values(), *deaths.values()):
            entries.sort(
                key=lambda truth: (
                    truth.time_seconds if truth.time_seconds is not None else -1
                )
            )
        return kills, deaths

    @staticmethod
    def build_players(
        scalars: list[tuple[str, int, int, int, int]],
        author_username: str,
        truth_data: dict[str, Any],
    ) -> list[PlayerTruth]:
        player_names = [name for name, *_ in scalars]
        kills_by_player, deaths_by_player = (
            ReplayBattleLogAssertions.build_event_truths(truth_data, player_names)
        )
        awards_by_player = truth_data["awards"]
        exact_award_counts = set(truth_data["exact_award_counts"])
        unknown_award_players = set(awards_by_player) - set(player_names)
        unknown_exact_players = exact_award_counts - set(player_names)
        if unknown_award_players or unknown_exact_players:
            raise ValueError(
                "Award truths reference players absent from scalar truths: "
                f"{sorted(unknown_award_players | unknown_exact_players)}"
            )

        return [
            PlayerTruth(
                username=name,
                team=team,
                kills_ground=ground,
                kills_air=air,
                deaths_total=deaths,
                awards=awards_by_player.get(name, []),
                awards_exact=name in exact_award_counts,
                kill_details=kills_by_player[name],
                death_details=deaths_by_player[name],
                is_author=name == author_username,
            )
            for name, team, ground, air, deaths in scalars
        ]

    @classmethod
    def is_munition_destruction_line(cls, line: str) -> bool:
        match = re.search(r"\bdestroyed\s+(.+)$", line, re.IGNORECASE)
        return bool(match and cls._MUNITION_TARGET_PATTERN.search(match.group(1)))

    def test_battle_log_event_truths_cover_all_event_lines(self) -> None:
        source_lines = [
            line
            for line in self.BATTLE_LOG_PATH.read_text(encoding="utf-8").splitlines()
            if re.match(r"^\d+:\d+\s+", line)
            and ("destroyed" in line or "shot down" in line)
        ]
        source_line_counts = Counter(source_lines)
        truth_lines = Counter(
            event["source_line"] for event in self.REPLAY_TRUTH_DATA["events"]
        )
        munition_lines = Counter(
            line for line in source_lines if self.is_munition_destruction_line(line)
        )
        if self.REQUIRE_MUNITION_LINES:
            assert munition_lines
        assert source_line_counts == truth_lines + munition_lines


class ReplayMetadataAssertions:
    """Shared metadata assertions for parsed replay regression tests."""

    SESSION_ID: str
    PLAYERS: list[PlayerTruth]
    PLAYER_COUNT = 32

    def test_session_id(self, replay: dict[str, Any]) -> None:
        assert replay["session_id"] == self.SESSION_ID

    def test_player_count(self, replay: dict[str, Any]) -> None:
        assert len(replay["players"]) == self.PLAYER_COUNT

    def test_author_username(self, replay: dict[str, Any]) -> None:
        author_truth = next(player for player in self.PLAYERS if player.is_author)
        assert replay["author"]["username"] == author_truth.username


class ReplayPlayerAssertions:
    """Shared scalar, award, and event assertions for each replay's players."""

    COMPLETE_KILL_DETAILS: set[str] = set()
    COMPLETE_DEATH_DETAILS: set[str] = set()

    def test_team(
        self, players_by_name: dict[str, dict[str, Any]], truth: PlayerTruth
    ) -> None:
        assert players_by_name[truth.username]["team"] == truth.team

    def test_kills_ground(
        self, players_by_name: dict[str, dict[str, Any]], truth: PlayerTruth
    ) -> None:
        assert players_by_name[truth.username]["kills"]["ground"] == truth.kills_ground

    def test_kills_air(
        self, players_by_name: dict[str, dict[str, Any]], truth: PlayerTruth
    ) -> None:
        assert players_by_name[truth.username]["kills"]["air"] == truth.kills_air

    def test_deaths_total(
        self, players_by_name: dict[str, dict[str, Any]], truth: PlayerTruth
    ) -> None:
        assert players_by_name[truth.username]["deaths"]["total"] == truth.deaths_total

    def test_awards_present(
        self, players_by_name: dict[str, dict[str, Any]], truth: PlayerTruth
    ) -> None:
        if not truth.awards:
            pytest.skip("no awards defined for this player")
        actual = players_by_name[truth.username]["awards"]
        assert_awards_present(actual, truth.awards, truth.username)

    def test_award_counts(
        self, players_by_name: dict[str, dict[str, Any]], truth: PlayerTruth
    ) -> None:
        if not truth.awards:
            pytest.skip("no awards defined for this player")
        actual = players_by_name[truth.username]["awards"]
        if truth.awards_exact:
            assert Counter(actual) == Counter(
                truth.awards
            ), f"{truth.username}: award counts differ from expected"
            return
        assert_award_counts(actual, truth.awards, truth.username)

    def test_kill_details(
        self,
        players_by_name: dict[str, dict[str, Any]],
        truth: PlayerTruth,
        battle_start: datetime,
    ) -> None:
        if not truth.kill_details:
            pytest.skip("no battle-log kill events for this player")
        actual = players_by_name[truth.username]["kills"]["vehicles"]
        if truth.is_author or truth.username in self.COMPLETE_KILL_DETAILS:
            assert_exact_kills(actual, truth.kill_details, truth.username, battle_start)
            return
        missing = [
            event
            for event in truth.kill_details
            if find_kill(actual, event, battle_start) is None
        ]
        if missing:
            pytest.xfail(
                f"{truth.username}: {len(missing)}/{len(truth.kill_details)} "
                "kill detail(s) not resolved"
            )

    def test_death_details(
        self,
        players_by_name: dict[str, dict[str, Any]],
        truth: PlayerTruth,
        battle_start: datetime,
    ) -> None:
        if not truth.death_details:
            pytest.skip("no battle-log death events for this player")
        actual = players_by_name[truth.username]["deaths"]["vehicles"]
        if truth.is_author or truth.username in self.COMPLETE_DEATH_DETAILS:
            assert_exact_deaths(
                actual, truth.death_details, truth.username, battle_start
            )
            return
        missing = [
            event
            for event in truth.death_details
            if find_death(actual, event, battle_start) is None
        ]
        if missing:
            pytest.xfail(
                f"{truth.username}: {len(missing)}/{len(truth.death_details)} "
                "death detail(s) not resolved"
            )
