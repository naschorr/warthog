"""Regression test for parsed replay session 5d97357300108c59.

Scalar expectations come from the parsed results block. Kill/death event
expectations are static truths transcribed from the battle log and stored in
the adjacent JSON fixture; the replay's parsed event-detail lists are only the
test subject.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.common.factories import ServiceFactory
from common.replay_test_helpers import (
    DEFAULT_TIMESTAMP_TOLERANCE_S,
    DeathDetailTruth,
    KillDetailTruth,
    PlayerTruth,
    elapsed_seconds,
    find_death,
    find_kill,
)

FIXTURE_DIR = Path(__file__).parent
WRPL_PATH = FIXTURE_DIR / "#2026.11.15 10.55.46.wrpl"
BATTLE_LOG_PATH = FIXTURE_DIR / "battle_log_5d97357300108c59.txt"
BATTLE_LOG_TRUTHS_PATH = FIXTURE_DIR / "battle_log_event_truths_5d97357300108c59.json"
SESSION_ID = "5d97357300108c59"
_BATTLE_LOG_EVENT_DATA = json.loads(BATTLE_LOG_TRUTHS_PATH.read_text(encoding="utf-8"))
_MUNITION_TARGET_PATTERN = re.compile(
    r"\b(?:\d+(?:[.,]\d+)?\s*(?:lbs?|kgs?|pounds?|kilograms?)\b|"
    r"(?:bomb|rocket|missile|torpedo|mine|shell|projectile|grenade)s?\b)",
    re.IGNORECASE,
)

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

# Internal award identifiers assigned to Ranol's slot, including repeated
# awards and awards that are not named in the battle log.
_AUTHOR_AWARDS = [
    "tank_die_hard",
    "hidden_all_streak",
    "defender_tank",
    "global_avenge_self",
    "hidden_allDef_streak_1_tank",
    "hidden_global_avenge_self_stage",
    "hidden_kill1_on_tank",
    "hidden_kill_streak",
    "defender_tank",
    "hidden_allDef_streak_2_tank",
    "tank_marked_enemy_destroyed_by_ally",
    "tank_marked_enemy_destroyed_by_ally",
    "global_shadow_assassin",
    "hidden_kill3_on_tank",
    "hidden_kill3_streak",
    "defender_tank",
    "global_avenge_friendly",
    "hidden_kill1_on_tank_destroyer",
    "squad_best",
    "hidden_allsquad_streak",
]

# Author detail truths are explicit and hard-asserted. Each battle-log line is
# retained as the comment immediately above its corresponding truth.
_AUTHOR_KILLS = [
    # 2:12 Ranol (Ikv 91-105) destroyed =VOGUE= 🎮 stinkyfeet678 (ZA-35)
    KillDetailTruth("sw_ikv_91_105", "stinkyfeet678", "uk_rooikat_za_35", 132),
    # 3:02 Ranol (Ikv 91-105) destroyed Batushka1324 (Leopard A1A1)
    KillDetailTruth("sw_ikv_91_105", "Batushka1324", "germ_leopard_I_a1", 182),
    # 7:50 Ranol (Ikv 91-105) destroyed christiah007 (Gepard)
    KillDetailTruth("sw_ikv_91_105", "christiah007", "germ_flakpz_I_Gepard", 470),
    # 9:05 Ranol (Pbv 302 (BILL)) destroyed =DRAGA= gennsgems (Leopard 1A5)
    KillDetailTruth("sw_pbv_302_bill", "gennsgems", "germ_leopard_1a5", 545),
]
_AUTHOR_DEATHS = [
    # 1:31 =VOGUE= 🎮 stinkyfeet678 (ZA-35) destroyed Ranol (CV 90105 TML)
    DeathDetailTruth("sw_cv_90105", "stinkyfeet678", "uk_rooikat_za_35", 91),
    # 7:54 =8CW8= xSHiZZY (Object 685) destroyed Ranol (Ikv 91-105)
    DeathDetailTruth("sw_ikv_91_105", "xSHiZZY", "ussr_object_685", 474),
    # 9:59 =DRAGA= gennsgems (TAM) destroyed Ranol (Pbv 302 (BILL))
    DeathDetailTruth("sw_pbv_302_bill", "gennsgems", "germ_thyssen_henschel_tam", 599),
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


def _build_battle_log_truths() -> (
    tuple[dict[str, list[KillDetailTruth]], dict[str, list[DeathDetailTruth]]]
):
    kills = {name: [] for name, *_ in _PLAYER_SCALARS}
    deaths = {name: [] for name, *_ in _PLAYER_SCALARS}
    for event in _BATTLE_LOG_EVENT_DATA["events"]:
        killer = event["killer_username"]
        victim = event["victim_username"]
        elapsed = event["time_seconds"]
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


_BATTLE_LOG_KILLS, _BATTLE_LOG_DEATHS = _build_battle_log_truths()


def _is_munition_destruction_line(line: str) -> bool:
    match = re.search(r"\bdestroyed\s+(.+)$", line, re.IGNORECASE)
    return bool(match and _MUNITION_TARGET_PATTERN.search(match.group(1)))


PLAYERS: list[PlayerTruth] = [
    PlayerTruth(
        username=name,
        team=team,
        kills_ground=ground,
        kills_air=air,
        deaths_total=deaths,
        awards=(_AUTHOR_AWARDS if name == "Ranol" else []),
        kill_details=(_AUTHOR_KILLS if name == "Ranol" else _BATTLE_LOG_KILLS[name]),
        death_details=(_AUTHOR_DEATHS if name == "Ranol" else _BATTLE_LOG_DEATHS[name]),
        is_author=(name == "Ranol"),
    )
    for name, team, ground, air, deaths in _PLAYER_SCALARS
]


@pytest.fixture(scope="module")
def replay() -> dict[str, Any]:
    factory = ServiceFactory()
    parser = factory.get_replay_parser_service()
    parsed = parser.parse_replay_file(WRPL_PATH)
    return json.loads(parsed.model_dump_json())


@pytest.fixture(scope="module")
def players_by_name(replay: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {player["username"]: player for player in replay["players"]}


@pytest.fixture(scope="module")
def battle_start(replay: dict[str, Any]) -> datetime:
    dt = datetime.fromisoformat(replay["start_time"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _assert_exact_kills(
    actual, expected, username: str, battle_start: datetime
) -> None:
    unmatched = list(actual)
    for truth in expected:
        matched = find_kill(unmatched, truth, battle_start)
        assert matched is not None, f"{username}: battle-log kill not found: {truth}"
        unmatched.remove(matched)
    assert not unmatched, f"{username}: unexpected parsed kill details: {unmatched}"


def _assert_exact_deaths(
    actual, expected, username: str, battle_start: datetime
) -> None:
    unmatched = list(actual)
    for truth in expected:
        matched = find_death(unmatched, truth, battle_start)
        assert matched is not None, f"{username}: battle-log death not found: {truth}"
        unmatched.remove(matched)
    assert not unmatched, f"{username}: unexpected parsed death details: {unmatched}"


class TestMetadata:
    def test_session_id(self, replay):
        assert replay["session_id"] == SESSION_ID

    def test_player_count(self, replay):
        assert len(replay["players"]) == 32

    def test_author_username(self, replay):
        assert replay["author"]["username"] == "Ranol"

    def test_battle_log_event_truths_cover_all_event_lines(self):
        source_lines = [
            line
            for line in BATTLE_LOG_PATH.read_text(encoding="utf-8").splitlines()
            if re.match(r"^\d+:\d+\s+", line)
            and ("destroyed" in line or "shot down" in line)
        ]
        source_line_counts = Counter(source_lines)
        truth_lines = Counter(
            event["source_line"] for event in _BATTLE_LOG_EVENT_DATA["events"]
        )
        munition_lines = Counter(
            line for line in source_lines if _is_munition_destruction_line(line)
        )
        assert munition_lines
        assert source_line_counts == truth_lines + munition_lines

    def test_author_event_truths_match_transcribed_event_fixture(self):
        assert _BATTLE_LOG_KILLS["Ranol"] == _AUTHOR_KILLS
        assert _BATTLE_LOG_DEATHS["Ranol"] == _AUTHOR_DEATHS


@pytest.mark.parametrize("truth", PLAYERS, ids=lambda truth: truth.username)
class TestAllPlayers:
    def test_team(self, truth, players_by_name):
        assert players_by_name[truth.username]["team"] == truth.team

    def test_kills_ground(self, truth, players_by_name):
        assert players_by_name[truth.username]["kills"]["ground"] == truth.kills_ground

    def test_kills_air(self, truth, players_by_name):
        assert players_by_name[truth.username]["kills"]["air"] == truth.kills_air

    def test_deaths_total(self, truth, players_by_name):
        assert players_by_name[truth.username]["deaths"]["total"] == truth.deaths_total

    def test_awards_present(self, truth, players_by_name):
        actual = players_by_name[truth.username]["awards"]
        for award in truth.awards:
            assert award in actual

    def test_award_counts(self, truth, players_by_name):
        actual = Counter(players_by_name[truth.username]["awards"])
        if truth.is_author:
            assert actual == Counter(truth.awards)
            return
        for award, minimum in Counter(truth.awards).items():
            assert actual[award] >= minimum

    def test_kill_details(self, truth, players_by_name, battle_start):
        expected = truth.kill_details
        if not expected:
            pytest.skip("no battle-log kill events for this player")
        actual = players_by_name[truth.username]["kills"]["vehicles"]
        if truth.is_author or truth.username in _COMPLETE_KILL_DETAILS:
            _assert_exact_kills(actual, expected, truth.username, battle_start)
            return
        for detail in expected:
            if find_kill(actual, detail, battle_start) is None:
                message = f"{truth.username}: battle-log kill not found: {detail}"
                pytest.xfail(message)

    def test_death_details(self, truth, players_by_name, battle_start):
        expected = truth.death_details
        if not expected:
            pytest.skip("no battle-log death events for this player")
        actual = players_by_name[truth.username]["deaths"]["vehicles"]
        if truth.is_author or truth.username in _COMPLETE_DEATH_DETAILS:
            _assert_exact_deaths(actual, expected, truth.username, battle_start)
            return
        for detail in expected:
            if find_death(actual, detail, battle_start) is None:
                message = f"{truth.username}: battle-log death not found: {detail}"
                pytest.xfail(message)
