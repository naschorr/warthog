"""Regression test for parsed replay session 5d97357300108c59.

Scalar expectations come from the parsed results block. Kill/death event
expectations are static truths transcribed from the battle log and stored in
the adjacent JSON fixture; the replay's parsed event-detail lists are only the
test subject.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.replay_test_helpers import (
    PlayerTruth,
    ReplayBattleLogAssertions,
    ReplayMetadataAssertions,
    ReplayPlayerAssertions,
)

FIXTURE_DIR = Path(__file__).parent
WRPL_PATH = FIXTURE_DIR / "#2026.11.15 10.55.46.wrpl"
BATTLE_LOG_SOURCE_PATH = FIXTURE_DIR / "battle_log_5d97357300108c59.txt"
REPLAY_TRUTHS_PATH = FIXTURE_DIR / "battle_log_event_truths_5d97357300108c59.json"
SESSION_ID = "5d97357300108c59"
_REPLAY_TRUTH_DATA = ReplayBattleLogAssertions.load_truth_data(REPLAY_TRUTHS_PATH)
# Trusted scalar ground truth copied from the parsed results block.
_PLAYER_SCALARS = [
    ("Harimizu", 1, 3, 0, 2),
    ("rfonseca138", 2, 0, 0, 4),
    ("CASPER-KILLER-08", 1, 0, 0, 2),
    ("danny_gt", 2, 5, 0, 4),
    ("stinkyfeet678", 1, 1, 0, 1),
    ("Perez0506106", 1, 0, 0, 3),
    ("SeuBob", 2, 0, 0, 3),
    ("tom24121998", 1, 0, 0, 1),
    ("EvilNasa", 2, 3, 0, 2),
    ("xSHiZZY", 1, 5, 0, 2),
    ("Ranol", 2, 4, 0, 3),
    ("TrueJackal", 2, 1, 0, 2),
    ("11MM", 1, 0, 0, 2),
    ("PAT615", 2, 0, 1, 4),
    ("FAUCON-987-69", 2, 2, 0, 4),
    ("scsmrcw", 2, 3, 0, 4),
    ("Reaver63782", 1, 6, 0, 1),
    ("BiggestBertha", 1, 10, 1, 2),
    ("Твoй Oтчим", 1, 6, 3, 1),
    ("Матье__Балл", 1, 1, 0, 1),
    ("KINGMETROE", 2, 0, 0, 2),
    ("gennsgems", 1, 8, 0, 2),
    ("Conqueftador379", 2, 1, 0, 4),
    ("GL Heli0s", 2, 1, 0, 3),
    ("MauroZedong", 2, 1, 0, 5),
    ("Batushka1324", 1, 3, 0, 2),
    ("DeividBv", 1, 2, 0, 1),
    ("Blegoman_", 2, 2, 0, 3),
    ("Amplespore", 1, 1, 0, 3),
    ("maseaneabaghira", 2, 5, 0, 2),
    ("克海_", 2, 0, 1, 2),
    ("christiah007", 1, 2, 1, 3),
]


# These players have complete battle-log truths with enough detail to compare
# the full parsed lists, rather than only checking that expected events exist.
_COMPLETE_KILL_DETAILS = {
    "Harimizu",
    "danny_gt",
    "stinkyfeet678",
    "TrueJackal",
    "FAUCON-987-69",
    "GL Heli0s",
    "MauroZedong",
    "Batushka1324",
    "DeividBv",
    "Blegoman_",
    "Amplespore",
    "christiah007",
    "PAT615",
}
_COMPLETE_DEATH_DETAILS = {
    "Ranol",
    "Harimizu",
    "stinkyfeet678",
    "tom24121998",
    "Batushka1324",
    "DeividBv",
    "christiah007",
}


PLAYERS: list[PlayerTruth] = ReplayBattleLogAssertions.build_players(
    _PLAYER_SCALARS, "Ranol", _REPLAY_TRUTH_DATA
)


class TestMetadata(ReplayMetadataAssertions, ReplayBattleLogAssertions):
    SESSION_ID = SESSION_ID
    PLAYERS = PLAYERS
    BATTLE_LOG_PATH = BATTLE_LOG_SOURCE_PATH
    REPLAY_TRUTH_DATA = _REPLAY_TRUTH_DATA
    REQUIRE_MUNITION_LINES = True


@pytest.mark.parametrize("truth", PLAYERS, ids=lambda truth: truth.username)
class TestAllPlayers(ReplayPlayerAssertions):
    COMPLETE_KILL_DETAILS = _COMPLETE_KILL_DETAILS
    COMPLETE_DEATH_DETAILS = _COMPLETE_DEATH_DETAILS
