"""
Regression test for parsed replay session 64a5fda000b358a.

Sources:
  - Raw replay:  #2026.03.14 17.52.35.wrpl
  - Battle log:  battle_log_64a5fda000b358a.txt

Ground truths:
  - BLK (results block) — authoritative for kill/death totals and team assignments.
  - Battle log — authoritative for kill/death attribution and awards.

Trust levels for kill/death details:
  - Replay author: fully trusted — hard assertions.
  - All other players: best-effort — marked xfail(strict=False) so failures are
    reported without failing the suite.

Notes:
  - BL coverage: ~22% of players (7/32) — partial. Only players visible in the BL
    have kill/death details populated.
  - The "set afire" event at 15:21 (Proto5510 → Ranol Pvkv II) is damage-only and
    does not generate a kill/death entry.
"""

from __future__ import annotations

import json
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

# ---------------------------------------------------------------------------
# Source-of-truth player list
# ---------------------------------------------------------------------------

PLAYERS: list[PlayerTruth] = [
    # --- Team 1 ---
    PlayerTruth(
        username="A2theizzy",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=3,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="BAtoloco",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=[],
        kill_details=[],
        death_details=[
            # 12:44 Ranol (SAV 20.12.48) destroyed BAtoloco (Pz.III L)
            DeathDetailTruth("germ_pzkpfw_III_ausf_L", "Ranol", "sw_sav_fm48", 764),
            # 15:17 Ranol (Pvkv II) destroyed BAtoloco (Sd.Kfz.251/21)
            DeathDetailTruth("germ_sdkfz_251_21", "Ranol", "sw_pvkv_II", 917),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Forrester_",
        team=1,
        kills_ground=7,
        kills_air=1,
        deaths_total=5,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="JeezeLouise1401",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=3,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="MAURILAZCANO",
        team=1,
        kills_ground=1,
        kills_air=1,
        deaths_total=3,
        awards=[],
        kill_details=[],
        death_details=[
            # 4:26 Ranol (⊙T-34) destroyed MAURILAZCANO (Sd.Kfz.234/2)
            DeathDetailTruth("germ_sdkfz_234_2", "Ranol", "sw_t_34_1941", 266),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="P1ls3n",
        team=1,
        kills_ground=4,
        kills_air=0,
        deaths_total=4,
        awards=[],
        kill_details=[
            # 8:03 P1ls3n (T-34) destroyed Ranol (⊙Pz.IV)
            KillDetailTruth("ussr_t_34_1942", "Ranol", "sw_pzkpfw_IV_ausf_J", 483),
        ],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Posine Loakan",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=3,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Proto5510",
        team=1,
        kills_ground=5,
        kills_air=0,
        deaths_total=6,
        awards=[],
        kill_details=[
            # 5:01 ^WWWG^ Proto5510 (Dicker Max) destroyed Ranol (⊙T-34)
            KillDetailTruth("germ_pzsfl_IVa_dickermax", "Ranol", "sw_t_34_1941", 301),
            # 13:34 ^WWWG^ Proto5510 (Sd.Kfz.234/2) destroyed Ranol (SAV 20.12.48)
            KillDetailTruth("germ_sdkfz_234_2", "Ranol", "sw_sav_fm48", 814),
        ],
        death_details=[
            # 2:52 Ranol (⊙T-34) destroyed Proto5510 (Jagdpanzer IV)
            DeathDetailTruth("germ_jgdpz_IV_L48", "Ranol", "sw_t_34_1941", 172),
            # 11:55 Ranol (SAV 20.12.48) destroyed Proto5510 (Ostwind)
            DeathDetailTruth("germ_flakpanzer_IV_Ostwind", "Ranol", "sw_sav_fm48", 715),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="SamuelNiqolas",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Ultrarated",
        team=1,
        kills_ground=9,
        kills_air=0,
        deaths_total=5,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Z0e0R0e0J",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="_17henrik117",
        team=1,
        kills_ground=6,
        kills_air=3,
        deaths_total=5,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="gallinitagarka",
        team=1,
        kills_ground=6,
        kills_air=0,
        deaths_total=4,
        awards=[],
        kill_details=[
            # 10:50 gallinitagarka (KV-1) destroyed Ranol (M24DK)
            KillDetailTruth("ussr_kv_1_L_11", "Ranol", "sw_m24_chaffee_dk", 650),
        ],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="irishship96",
        team=1,
        kills_ground=1,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="oeL",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="ray_tay-tay2208",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=[],
        kill_details=[],
        death_details=[
            # 4:38 Ranol (⊙T-34) destroyed ray_tay-tay2208 (Matilda III)
            DeathDetailTruth("uk_a_12_mk_2_matilda_2", "Ranol", "sw_t_34_1941", 278),
            # 8:32 Ranol (⊙Pz.IV) destroyed ray_tay-tay2208 (AEC AA)
            DeathDetailTruth("uk_armored_car_mk_2_aa", "Ranol", "sw_pzkpfw_IV_ausf_J", 512),
        ],
        is_author=False,
    ),
    # --- Team 2 ---
    PlayerTruth(
        username="B0L4CH44",
        team=2,
        kills_ground=3,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="BDSGaming",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Fred787878",
        team=2,
        kills_ground=6,
        kills_air=0,
        deaths_total=3,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Hold_My_Vodka",
        team=2,
        kills_ground=7,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="ItsOrange678",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=5,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Jean_xtz",
        team=2,
        kills_ground=3,
        kills_air=0,
        deaths_total=0,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Mazinger_Zero",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="PaunchyBear8094",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="Ranol",
        team=2,
        kills_ground=7,
        kills_air=0,
        deaths_total=4,
        awards=[],
        kill_details=[
            # 2:52 Ranol (⊙T-34) destroyed Proto5510 (Jagdpanzer IV)
            KillDetailTruth("sw_t_34_1941", "Proto5510", "germ_jgdpz_IV_L48", 172),
            # 4:26 Ranol (⊙T-34) destroyed MAURILAZCANO (Sd.Kfz.234/2)
            KillDetailTruth("sw_t_34_1941", "MAURILAZCANO", "germ_sdkfz_234_2", 266),
            # 4:38 Ranol (⊙T-34) destroyed ray_tay-tay2208 (Matilda III)
            KillDetailTruth("sw_t_34_1941", "ray_tay-tay2208", "uk_a_12_mk_2_matilda_2", 278),
            # 8:32 Ranol (⊙Pz.IV) destroyed ray_tay-tay2208 (AEC AA)
            KillDetailTruth("sw_pzkpfw_IV_ausf_J", "ray_tay-tay2208", "uk_armored_car_mk_2_aa", 512),
            # 11:55 Ranol (SAV 20.12.48) destroyed Proto5510 (Ostwind)
            KillDetailTruth("sw_sav_fm48", "Proto5510", "germ_flakpanzer_IV_Ostwind", 715),
            # 12:44 Ranol (SAV 20.12.48) destroyed BAtoloco (Pz.III L)
            KillDetailTruth("sw_sav_fm48", "BAtoloco", "germ_pzkpfw_III_ausf_L", 764),
            # 15:17 Ranol (Pvkv II) destroyed BAtoloco (Sd.Kfz.251/21)
            KillDetailTruth("sw_pvkv_II", "BAtoloco", "germ_sdkfz_251_21", 917),
        ],
        death_details=[
            # 5:01 Proto5510 (Dicker Max) destroyed Ranol (⊙T-34)
            DeathDetailTruth("sw_t_34_1941", "Proto5510", "germ_pzsfl_IVa_dickermax", 301),
            # 8:03 P1ls3n (T-34) destroyed Ranol (⊙Pz.IV)
            DeathDetailTruth("sw_pzkpfw_IV_ausf_J", "P1ls3n", "ussr_t_34_1942", 483),
            # 10:50 gallinitagarka (KV-1) destroyed Ranol (M24DK)
            DeathDetailTruth("sw_m24_chaffee_dk", "gallinitagarka", "ussr_kv_1_L_11", 650),
            # 13:34 Proto5510 (Sd.Kfz.234/2) destroyed Ranol (SAV 20.12.48)
            DeathDetailTruth("sw_sav_fm48", "Proto5510", "germ_sdkfz_234_2", 814),
        ],
        is_author=True,
    ),
    PlayerTruth(
        username="Taruwu",
        team=2,
        kills_ground=4,
        kills_air=0,
        deaths_total=4,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="commissarcarl",
        team=2,
        kills_ground=6,
        kills_air=6,
        deaths_total=4,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="genial_peace4",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=5,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="ikrammusacaliph",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="mrjingles_",
        team=2,
        kills_ground=8,
        kills_air=1,
        deaths_total=6,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="nsevers2017",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=3,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="sporty313",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=3,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
]

# ---------------------------------------------------------------------------
# Parsed-replay fixture
# ---------------------------------------------------------------------------

WRPL_PATH = Path(__file__).parent / "#2026.03.14 17.52.35.wrpl"


@pytest.fixture(scope="module")
def replay() -> dict[str, Any]:
    factory = ServiceFactory()
    parser = factory.get_replay_parser_service()
    parsed = parser.parse_replay_file(WRPL_PATH)
    return json.loads(parsed.model_dump_json())


@pytest.fixture(scope="module")
def players_by_name(replay: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["username"]: p for p in replay["players"]}


@pytest.fixture(scope="module")
def battle_start(replay: dict[str, Any]) -> datetime:
    """Battle start time as a UTC-aware datetime, parsed from the replay."""
    dt = datetime.fromisoformat(replay["start_time"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_session_id(self, replay: dict[str, Any]) -> None:
        assert replay["session_id"] == "64a5fda000b358a"

    def test_player_count(self, replay: dict[str, Any]) -> None:
        assert len(replay["players"]) == 32

    def test_author_username(self, replay: dict[str, Any]) -> None:
        author_truth = next(p for p in PLAYERS if p.is_author)
        assert replay["author"]["username"] == author_truth.username


# ---------------------------------------------------------------------------
# Per-player parametrized tests  (one invocation per PlayerTruth in PLAYERS)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("truth", PLAYERS, ids=lambda p: p.username)
class TestAllPlayers:

    def test_team(self, players_by_name: dict, truth: PlayerTruth) -> None:
        assert players_by_name[truth.username]["team"] == truth.team

    def test_kills_ground(self, players_by_name: dict, truth: PlayerTruth) -> None:
        assert players_by_name[truth.username]["kills"]["ground"] == truth.kills_ground

    def test_kills_air(self, players_by_name: dict, truth: PlayerTruth) -> None:
        assert players_by_name[truth.username]["kills"]["air"] == truth.kills_air

    def test_deaths_total(self, players_by_name: dict, truth: PlayerTruth) -> None:
        assert players_by_name[truth.username]["deaths"]["total"] == truth.deaths_total

    def test_awards_present(self, players_by_name: dict, truth: PlayerTruth) -> None:
        if not truth.awards:
            pytest.skip("no awards defined for this player")
        actual = players_by_name[truth.username]["awards"]
        for award_id in set(truth.awards):
            assert award_id in actual, f"{truth.username}: expected award '{award_id}'"

    def test_award_counts(self, players_by_name: dict, truth: PlayerTruth) -> None:
        if not truth.awards:
            pytest.skip("no awards defined for this player")
        actual_counts = Counter(players_by_name[truth.username]["awards"])
        for award_id, expected_min in Counter(truth.awards).items():
            actual = actual_counts[award_id]
            assert actual >= expected_min, (
                f"{truth.username}: expected at least {expected_min}x " f"'{award_id}', got {actual}"
            )

    def test_kill_details(self, players_by_name: dict, truth: PlayerTruth, battle_start: datetime) -> None:
        if not truth.kill_details:
            pytest.skip("no kill details defined for this player")
        kds = players_by_name[truth.username]["kills"]["vehicles"]
        not_found: list[KillDetailTruth] = []
        for kd_truth in truth.kill_details:
            match = find_kill(kds, kd_truth, battle_start)
            if match is None:
                if truth.is_author:
                    assert match is not None, (
                        f"{truth.username}: kill not found - "
                        f"killer_vehicle={kd_truth.killer_vehicle!r}, "
                        f"victim_username={kd_truth.victim_username!r}, "
                        f"victim_vehicle={kd_truth.victim_vehicle!r}"
                    )
                else:
                    not_found.append(kd_truth)
        if not_found:
            pytest.xfail(
                f"{truth.username}: {len(not_found)}/{len(truth.kill_details)} " f"kill detail(s) not resolved"
            )

    def test_death_details(self, players_by_name: dict, truth: PlayerTruth, battle_start: datetime) -> None:
        if not truth.death_details:
            pytest.skip("no death details defined for this player")
        dds = players_by_name[truth.username]["deaths"]["vehicles"]
        not_found: list[DeathDetailTruth] = []
        for dd_truth in truth.death_details:
            match = find_death(dds, dd_truth, battle_start)
            if match is None:
                if truth.is_author:
                    assert match is not None, (
                        f"{truth.username}: death not found - "
                        f"victim_vehicle={dd_truth.victim_vehicle!r}, "
                        f"killer_username={dd_truth.killer_username!r}, "
                        f"killer_vehicle={dd_truth.killer_vehicle!r}"
                    )
                else:
                    not_found.append(dd_truth)
        if not_found:
            pytest.xfail(
                f"{truth.username}: {len(not_found)}/{len(truth.death_details)} " f"death detail(s) not resolved"
            )
