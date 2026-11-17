"""Regression test for parsed replay session 64a5fda000b358a.

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
BATTLE_LOG_SOURCE_PATH = FIXTURE_DIR / "battle_log_64a5fda000b358a.txt"
REPLAY_TRUTHS_PATH = FIXTURE_DIR / "battle_log_event_truths_64a5fda000b358a.json"
SESSION_ID = "64a5fda000b358a"
_REPLAY_TRUTH_DATA = ReplayBattleLogAssertions.load_truth_data(REPLAY_TRUTHS_PATH)
# Trusted scalar ground truth copied from the parsed results block.
_PLAYER_SCALARS = [
    ("A2theizzy", 1, 0, 0, 3),
    ("BAtoloco", 1, 0, 0, 4),
    ("Forrester_", 1, 7, 1, 5),
    ("JeezeLouise1401", 1, 0, 0, 3),
    ("MAURILAZCANO", 1, 1, 1, 3),
    ("P1ls3n", 1, 4, 0, 4),
    ("Posine Loakan", 1, 2, 0, 3),
    ("Proto5510", 1, 5, 0, 6),
    ("SamuelNiqolas", 1, 0, 0, 2),
    ("Ultrarated", 1, 9, 0, 5),
    ("Z0e0R0e0J", 1, 0, 0, 2),
    ("_17henrik117", 1, 6, 3, 5),
    ("gallinitagarka", 1, 6, 0, 4),
    ("irishship96", 1, 1, 0, 2),
    ("oeL", 1, 2, 0, 2),
    ("ray_tay-tay2208", 1, 0, 0, 4),
    ("B0L4CH44", 2, 3, 0, 2),
    ("BDSGaming", 2, 1, 0, 2),
    ("Fred787878", 2, 6, 0, 3),
    ("Hold_My_Vodka", 2, 7, 0, 2),
    ("ItsOrange678", 2, 0, 0, 5),
    ("Jean_xtz", 2, 3, 0, 0),
    ("Mazinger_Zero", 2, 0, 0, 2),
    ("PaunchyBear8094", 2, 0, 0, 2),
    ("Ranol", 2, 7, 0, 4),
    ("Taruwu", 2, 4, 0, 4),
    ("commissarcarl", 2, 6, 6, 4),
    ("genial_peace4", 2, 1, 0, 5),
    ("ikrammusacaliph", 2, 0, 0, 2),
    ("mrjingles_", 2, 8, 1, 6),
    ("nsevers2017", 2, 1, 0, 3),
    ("sporty313", 2, 2, 0, 3),
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


WRPL_PATH = Path(__file__).parent / "#2026.03.14 17.52.35.wrpl"
