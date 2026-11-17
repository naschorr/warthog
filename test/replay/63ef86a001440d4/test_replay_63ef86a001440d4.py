"""Regression test for parsed replay session 63ef86a001440d4.

Scalar expectations come from the parsed results block. Kill/death event and
award expectations are stored in the adjacent replay truth fixture.
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
BATTLE_LOG_SOURCE_PATH = FIXTURE_DIR / "battle_log_63ef86a001440d4.txt"
REPLAY_TRUTHS_PATH = FIXTURE_DIR / "battle_log_event_truths_63ef86a001440d4.json"
SESSION_ID = "63ef86a001440d4"
_REPLAY_TRUTH_DATA = ReplayBattleLogAssertions.load_truth_data(REPLAY_TRUTHS_PATH)
# Trusted scalar ground truth copied from the parsed results block.
_PLAYER_SCALARS = [
    ("LMEESH35", 2, 0, 0, 3),
    ("Trember", 1, 4, 0, 3),
    ("MGrizzB", 2, 9, 0, 4),
    ("Pro_Gamer_20000", 2, 2, 0, 4),
    ("IBecameTheAmmo", 1, 5, 0, 2),
    ("_SP23", 1, 4, 0, 3),
    ("Лейтенант Ебонов", 2, 2, 0, 1),
    ("autumn1196", 1, 0, 4, 5),
    ("ZaddyLongStyle", 2, 3, 0, 2),
    ("LarryErkniq", 2, 0, 0, 2),
    ("ACCTGU 145", 2, 1, 0, 2),
    ("Ranol", 1, 7, 1, 6),
    ("StealthCookie", 2, 3, 0, 4),
    ("Wiggle#6", 1, 0, 1, 5),
    ("ql toxic lp", 1, 2, 0, 3),
    ("SCHNOOKUMSPRIME", 2, 2, 0, 3),
    ("Jandamarra", 2, 0, 0, 2),
    ("channdro", 2, 10, 0, 4),
    ("Late Noon", 1, 8, 0, 1),
    ("ChasingRapture", 1, 2, 2, 5),
    ("USS_Liberty_K1K3", 1, 3, 0, 2),
    ("Laughing Hawk", 1, 2, 2, 4),
    ("Starka228", 1, 0, 0, 3),
    ("ExtremistMagpie", 2, 2, 0, 4),
    ("Bymemory", 2, 12, 0, 3),
    ("ooxxaa", 1, 3, 0, 1),
    ("Undertaker1134", 1, 0, 0, 3),
    ("DARKLORD574699", 2, 0, 0, 4),
    ("i_Scorched", 1, 1, 0, 4),
    ("C DESTROYER26", 2, 2, 0, 5),
    ("Darkcart 8430", 2, 2, 0, 4),
    ("Stampedinbuny420", 1, 0, 0, 2),
]


PLAYERS: list[PlayerTruth] = ReplayBattleLogAssertions.build_players(
    _PLAYER_SCALARS, "Ranol", _REPLAY_TRUTH_DATA
)


class TestMetadata(ReplayMetadataAssertions, ReplayBattleLogAssertions):
    SESSION_ID = SESSION_ID
    PLAYERS = PLAYERS
    BATTLE_LOG_PATH = BATTLE_LOG_SOURCE_PATH
    REPLAY_TRUTH_DATA = _REPLAY_TRUTH_DATA


@pytest.mark.parametrize("truth", PLAYERS, ids=lambda truth: truth.username)
class TestAllPlayers(ReplayPlayerAssertions):
    pass


WRPL_PATH = (
    Path(__file__).resolve().parents[2]
    / "replay_data_grabber"
    / "fixtures"
    / "63ef86a001440d4"
    / "#2026.03.06 01.16.49.wrpl"
)
