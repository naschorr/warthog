"""Regression test for parsed replay session 6414f3f0024322e.

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
BATTLE_LOG_SOURCE_PATH = FIXTURE_DIR / "battle_log_6414f3f0024322e.txt"
REPLAY_TRUTHS_PATH = FIXTURE_DIR / "battle_log_event_truths_6414f3f0024322e.json"
SESSION_ID = "6414f3f0024322e"
_REPLAY_TRUTH_DATA = ReplayBattleLogAssertions.load_truth_data(REPLAY_TRUTHS_PATH)
# Trusted scalar ground truth copied from the parsed results block.
_PLAYER_SCALARS = [
    ("RT-7274", 2, 1, 0, 4),
    ("little_leaf_fox", 2, 5, 1, 5),
    ("Axolot56", 1, 2, 0, 5),
    ("night#12", 1, 1, 0, 3),
    ("Kiritouhu2#1", 1, 4, 0, 5),
    ("bramcracker7", 2, 15, 0, 1),
    ("Sgt_ Norris Doms", 2, 1, 1, 3),
    ("Ranol", 2, 5, 1, 5),
    ("GrahamCanada22", 1, 1, 0, 4),
    ("1550251896", 1, 3, 0, 6),
    ("CJQSNBB", 1, 2, 0, 2),
    ("matiz_cubista", 2, 1, 0, 3),
    ("gabrielzonhtmj", 1, 0, 0, 2),
    ("FullcaioDias", 1, 1, 0, 2),
    ("snakeeater1945", 2, 5, 0, 2),
    ("shawn32100", 1, 4, 1, 3),
    ("bearhntr", 1, 0, 0, 4),
    ("BaIIs", 1, 10, 1, 3),
    ("YoloRaptorK15222", 2, 0, 0, 3),
    ("yoncl", 2, 0, 0, 4),
    ("rebajas-bromista", 2, 8, 1, 3),
    ("crazyranger03", 1, 8, 0, 3),
    ("SQUEX6409", 2, 0, 0, 3),
    ("eyxio", 2, 4, 0, 6),
    ("AdrielElProfe", 1, 3, 2, 1),
    ("TakenCeiling338", 2, 1, 0, 2),
    ("Nahu_1207", 2, 0, 0, 2),
    ("Masteryoda6656", 2, 0, 0, 4),
    ("Palmetto_97", 1, 5, 0, 4),
    ("Kilrak_Bloodfang", 1, 0, 0, 4),
    ("ShadowWolf168", 2, 2, 0, 3),
    ("ThirtySeven", 1, 5, 0, 1),
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


WRPL_PATH = Path(__file__).parent / "#2026.03.07 20.01.11.wrpl"
