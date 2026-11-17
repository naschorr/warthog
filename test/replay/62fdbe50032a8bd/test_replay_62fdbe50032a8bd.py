"""Regression test for parsed replay session 62fdbe50032a8bd.

Scalar expectations come from the parsed results block. Kill/death event and
award expectations are stored in the adjacent replay truth fixture.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


import pytest

from common.replay_test_helpers import (
    PlayerTruth,
    ReplayBattleLogAssertions,
    elapsed_seconds,
    find_kill,
    ReplayMetadataAssertions,
    ReplayPlayerAssertions,
)

FIXTURE_DIR = Path(__file__).parent
BATTLE_LOG_SOURCE_PATH = FIXTURE_DIR / "battle_log_62fdbe50032a8bd.txt"
REPLAY_TRUTHS_PATH = FIXTURE_DIR / "battle_log_event_truths_62fdbe50032a8bd.json"
SESSION_ID = "62fdbe50032a8bd"
_REPLAY_TRUTH_DATA = ReplayBattleLogAssertions.load_truth_data(REPLAY_TRUTHS_PATH)
# Trusted scalar ground truth copied from the parsed results block.
_PLAYER_SCALARS = [
    ("xK1NGSH0TZx", 1, 1, 0, 2),
    ("Zonney0007", 1, 6, 0, 6),
    ("Ranol", 1, 17, 0, 6),
    ("Siran2007YT", 1, 2, 0, 1),
    ("HayHay9797", 1, 0, 0, 2),
    ("obsidianwolf13", 1, 2, 0, 3),
    ("Pawin_Krittayamo", 1, 2, 1, 6),
    ("Metarou", 1, 6, 2, 5),
    ("bosco3202", 1, 6, 0, 2),
    ("oliveshellhound", 1, 2, 2, 6),
    ("PinCushion45", 1, 2, 0, 2),
    ("Evokekirby", 1, 1, 3, 3),
    ("InDommWeTrust", 1, 0, 0, 1),
    ("Thorkell_83", 1, 2, 0, 5),
    ("b1 Val", 1, 0, 0, 4),
    ("KlutzyObject6", 1, 0, 0, 4),
    ("_06254039349256", 2, 3, 0, 5),
    ("No-X1m-", 2, 9, 3, 4),
    ("FAN_Falcon", 2, 3, 0, 5),
    ("XanDerJacK_guNna", 2, 1, 0, 1),
    ("Zam__", 2, 1, 0, 4),
    ("marcosilvavil45", 2, 3, 3, 7),
    ("HASBU___", 2, 1, 1, 4),
    ("alexEC", 2, 0, 0, 2),
    ("Sophia 87208673", 2, 3, 0, 1),
    ("kodiak par", 2, 0, 0, 2),
    ("StubblyStew310", 2, 1, 0, 3),
    ("Ribacio", 2, 3, 3, 6),
    ("Yogui78", 2, 0, 0, 4),
    ("alpha_overcoat0", 2, 0, 0, 2),
    ("Toxic85828", 2, 6, 0, 6),
    ("Perjuro", 2, 11, 0, 5),
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
    / "62fdbe50032a8bd"
    / "2026.02.22 14.49.18.wrpl"
)


class TestReplay62StreamTiming:
    def test_ranol_btr_kill_retains_stream_record_time(
        self, players_by_name: dict, battle_start: datetime
    ) -> None:
        author_truth = next(player for player in PLAYERS if player.is_author)
        btr_kill_truth = next(
            detail
            for detail in author_truth.kill_details
            if detail.victim_vehicle == "ussr_btr_152a"
        )
        event = find_kill(players_by_name["Ranol"]["kills"]["vehicles"], btr_kill_truth)

        assert event is not None
        assert elapsed_seconds(event.get("time_utc"), battle_start) == pytest.approx(
            1290.813, abs=0.001
        )
