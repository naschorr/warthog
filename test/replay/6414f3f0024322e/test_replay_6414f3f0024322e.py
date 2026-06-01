"""
Regression test for parsed replay session 6414f3f0024322e.

Sources:
  - Raw replay:  #2026.03.07 20.01.11.wrpl
  - Battle log:  battle_log_6414f3f0024322e.txt

Ground truths:
  - BLK (results block) - authoritative for kill/death totals and team assignments.
  - Battle log - authoritative for kill/death attribution and awards.

Trust levels for kill/death details:
  - Replay author: fully trusted - hard assertions.
  - All other players: best-effort - marked xfail(strict=False) so failures are
    reported without failing the suite.
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

WRPL_PATH = Path(__file__).parent / "#2026.03.07 20.01.11.wrpl"


@pytest.fixture(scope="module")
def replay() -> dict[str, Any]:
    factory = ServiceFactory()
    parser = factory.get_replay_parser_service()
    parsed_replay = parser.parse_replay_file(WRPL_PATH)
    return json.loads(parsed_replay.model_dump_json())


@pytest.fixture(scope="module")
def players_by_name(replay: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["username"]: p for p in replay["players"]}


@pytest.fixture(scope="module")
def battle_start(replay: dict[str, Any]) -> datetime:
    dt = datetime.fromisoformat(replay["start_time"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


PLAYERS: list[PlayerTruth] = [
    PlayerTruth(
        username="RT-7274",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=4,
        awards=[
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "hidden_base_capturer",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "squad_kill",
            "hidden_squad_streaks_2_stage",
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
            "squad_best",
        ],
        kill_details=[
            KillDetailTruth("germ_pzkpfw_IV_ausf_H", "1550251896", "us_m4a2_sherman", 499),
        ],
        death_details=[
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "Axolot56", "ussr_t_34_1942", 537),
            DeathDetailTruth("germ_pzkpfw_IV_ausf_F2", "crazyranger03", "us_m24_chaffee", 701),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="little_leaf_fox",
        team=2,
        kills_ground=5,
        kills_air=1,
        deaths_total=5,
        awards=[
            "hidden_base_capturer",
            "first_blood",
            "hidden_all_streak",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "global_shadow_assassin",
            "hidden_allDef_streak_1_tank",
            "hidden_battlepass_season_22_challenge_7_kill3_without_death",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_allMulty_streak",
            "defender_ground",
            "global_avenge_self",
            "global_destroy_enemy_marked_by_ally",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_fighter",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_marks_1_aircraft",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_kill1_on_tank_destroyer",
            "marks_5_tanks",
            "hidden_all_streak_tank",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("fr_amx_13_fl_11", "night#12", "cn_m24_chaffee", 253),
            KillDetailTruth("f6f-5_france", "GrahamCanada22", "us_m4a1_1942_sherman", 400),
            KillDetailTruth("fr_amx_vtt_dca", "BaIIs", "ki_61_1a_otsu", 633),
            KillDetailTruth("fr_m10", "BaIIs", "jp_type_5_na_to", 1026),
        ],
        death_details=[
            DeathDetailTruth("fr_amx_13_fl_11", "GrahamCanada22", "us_m4a1_1942_sherman", 296),
            DeathDetailTruth("f6f-5_france", "BaIIs", "ki_61_1a_otsu", 458),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Axolot56",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=5,
        awards=[
            "tank_help_with_repairing",
            "tank_die_hard",
            "hidden_all_streak",
            "hidden_base_capturer",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_2_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_tank_destroyer",
            "marks_killed_plane_10_ranks_higher",
        ],
        kill_details=[
            KillDetailTruth("ussr_t_34_1942", "RT-7274", "germ_pzkpfw_IV_ausf_H", 537),
            KillDetailTruth("ussr_su_122", "Ranol", "sw_pzkpfw_IV_ausf_J", 884),
        ],
        death_details=[
            DeathDetailTruth("ussr_su_122", "bramcracker7", "germ_stug_III_ausf_G", 422),
            DeathDetailTruth("ussr_t_34_1942", "Ranol", "sw_pzkpfw_IV_ausf_J", 748),
            DeathDetailTruth("ussr_su_122", "bramcracker7", "germ_sdkfz_234_2", 995),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="night#12",
        team=1,
        kills_ground=1,
        kills_air=0,
        deaths_total=3,
        awards=[
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
        ],
        kill_details=[],
        death_details=[
            DeathDetailTruth("cn_m24_chaffee", "little_leaf_fox", "fr_amx_13_fl_11", 253),
            DeathDetailTruth("cn_m10", "Ranol", "sw_sav_fm48", 453),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Kiritouhu2#1",
        team=1,
        kills_ground=4,
        kills_air=0,
        deaths_total=5,
        awards=[
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "squad_kill",
            "hidden_squad_streaks_2_stage",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_2_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_tank_destroyer",
            "hidden_base_capturer",
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill3_streak",
            "defender_tank",
            "global_shadow_assassin",
            "hidden_kill3_on_tank_destroyer",
            "tank_die_hard",
            "hidden_all_streak",
        ],
        kill_details=[
            KillDetailTruth("us_m4a1_1942_sherman", "Ranol", "sw_t_34_1941", 299),
            KillDetailTruth("us_m44", "bramcracker7", "germ_stug_III_ausf_G", 511),
            KillDetailTruth("us_m44", "Ranol", "sw_pvkv_II", 595),
            KillDetailTruth("us_m44", "Sgt_ Norris Doms", "germ_infanterie_kampfpanzer_churchill", 649),
        ],
        death_details=[
            DeathDetailTruth("us_m44", "bramcracker7", "germ_stug_III_ausf_G", 258),
            DeathDetailTruth("us_m4a1_1942_sherman", "bramcracker7", "germ_stug_III_ausf_G", 399),
            DeathDetailTruth("us_m44", "eyxio", "sw_m24_chaffee_dk", 704),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="bramcracker7",
        team=2,
        kills_ground=15,
        kills_air=0,
        deaths_total=1,
        awards=[
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "global_shadow_assassin",
            "hidden_kill3_on_tank_destroyer",
            "hidden_kill3_streak",
            "multi_kill_air",
            "tank_kill_without_fail",
            "global_shadow_assassin",
            "defender_tank",
            "global_kills_without_death",
            "global_shadow_assassin",
            "hidden_allDef_streak_2_tank",
            "marks_5_tanks",
            "hidden_all_streak_tank",
            "global_kills_without_death",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_kill_without_fail",
            "defender_tank",
            "global_kills_without_death",
            "multi_kill_air",
            "tank_kill_without_fail",
            "defender_tank",
            "global_kills_without_death",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_kill1_on_tank",
            "fr_volunteer_cross_streak",
            "hidden_base_capturer",
            "tank_die_hard",
            "hidden_all_streak",
            "marks_10_tanks",
            "tank_marked_enemy_destroyed_by_ally",
            "defender_tank",
            "hidden_kill3_on_tank",
            "defender_tank",
            "tank_kill_without_fail",
            "defender_tank",
            "global_kills_without_death",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_kill_without_fail",
            "defender_tank",
            "global_avenge_friendly",
            "global_kills_without_death",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_kill_without_fail",
            "tank_marked_enemy_destroyed_by_ally",
            "global_kills_without_death",
            "global_shadow_assassin",
            "tank_kill_without_fail",
            "fr_fighter_cross_streak",
            "heroic_tankman",
            "hidden_allHeroic_streak",
            "hidden_allHeroic_streak_tank",
            "hidden_allNearHeroic_streak",
            "hidden_allNearHeroic_streak_tank",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("germ_stug_III_ausf_G", "Kilrak_Bloodfang", "us_m19", 223),
            KillDetailTruth("germ_stug_III_ausf_G", "FullcaioDias", "ussr_kv_1_zis_5", 250),
            KillDetailTruth("germ_stug_III_ausf_G", "Kiritouhu2#1", "us_m44", 258),
            KillDetailTruth("germ_stug_III_ausf_G", "AdrielElProfe", "us_m4a2_sherman", 363),
            KillDetailTruth("germ_stug_III_ausf_G", "Kiritouhu2#1", "us_m4a1_1942_sherman", 399),
            KillDetailTruth("germ_stug_III_ausf_G", "Axolot56", "ussr_su_122", 422),
            KillDetailTruth("germ_sdkfz_234_2", "Kilrak_Bloodfang", "us_m42_duster", 663),
            KillDetailTruth("germ_sdkfz_234_2", "GrahamCanada22", "us_m24_chaffee", 876),
            KillDetailTruth("germ_sdkfz_234_2", "Palmetto_97", "ussr_kv_1_L_11", 932),
            KillDetailTruth("germ_sdkfz_234_2", "Axolot56", "ussr_su_122", 995),
            KillDetailTruth("germ_sdkfz_234_2", "Palmetto_97", "ussr_su_122", 1023),
        ],
        death_details=[
            DeathDetailTruth("germ_stug_III_ausf_G", "Kiritouhu2#1", "us_m44", 511),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Sgt_ Norris Doms",
        team=2,
        kills_ground=1,
        kills_air=1,
        deaths_total=3,
        awards=[
            "tank_marked_enemy_destroyed_by_ally",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "hidden_marks_1_aircraft",
            "tank_marked_enemy_destroyed_by_ally",
            "tank_die_hard",
            "hidden_all_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_2_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_heavy_tank",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "row_air_assist",
            "fr_volunteer_cross_streak",
            "heroic_wingman",
            "hidden_allHeroic_streak",
            "hidden_allHeroic_streak_air",
            "hidden_allHeroic_streak_tank",
            "hidden_allNearHeroic_streak",
            "hidden_allNearHeroic_streak_air",
            "hidden_allNearHeroic_streak_tank",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("germ_infanterie_kampfpanzer_churchill", "Palmetto_97", "ussr_t_34_1941_l_11", 605),
        ],
        death_details=[
            DeathDetailTruth("germ_sdkfz_234_2", "Palmetto_97", "ussr_t_34_1941_l_11", 490),
            DeathDetailTruth("germ_infanterie_kampfpanzer_churchill", "Kiritouhu2#1", "us_m44", 649),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Ranol",
        team=2,
        ## Note that the kills/deaths come from the replay's summary BLK section, not the replay decoder.
        ## The kills_ground is incorrect in this case, as it seems to be double counting a posthumous artillery kill.
        ## So this value is incorrect for reality, but correct in terms of what the replay says.
        kills_ground=5,
        kills_air=1,
        deaths_total=5,
        awards=[
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "squad_assist",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill3_streak",
            "hidden_marks_1_aircraft",
            "tank_kill_without_fail",
            "global_shadow_assassin",
            "global_shadow_assassin",
            "hidden_kill3_on_tank_destroyer",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "defender_tank",
            "global_destroy_enemy_marked_by_ally",
            "hidden_allDef_streak_1_tank",
            "hidden_kill3_on_tank",
            "marks_5_tanks",
            "tank_kill_without_fail",
            "hidden_all_streak_tank",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("sw_t_34_1941", "Palmetto_97", "ussr_su_152", 212),
            ## Artillery kill, called in with the T-34 but the kill happened after the next spawn.
            KillDetailTruth("sw_t_34_1941", "Kilrak_Bloodfang", "us_m19", 321),
            KillDetailTruth("sw_sav_fm48", "FullcaioDias", "i-15_1934", 373),
            KillDetailTruth("sw_sav_fm48", "night#12", "cn_m10", 453),
            KillDetailTruth("sw_pzkpfw_IV_ausf_J", "Axolot56", "ussr_t_34_1942", 748),
        ],
        death_details=[
            DeathDetailTruth("sw_t_34_1941", "Kiritouhu2#1", "us_m4a1_1942_sherman", 299),
            DeathDetailTruth("sw_sav_fm48", "CJQSNBB", "us_m4_sherman", 461),
            DeathDetailTruth("sw_pvkv_II", "Kiritouhu2#1", "us_m44", 595),
            DeathDetailTruth("sw_m24_chaffee_dk", "crazyranger03", "us_m24_chaffee", 672),
            DeathDetailTruth("sw_pzkpfw_IV_ausf_J", "Axolot56", "ussr_su_122", 884),
        ],
        is_author=True,
    ),
    PlayerTruth(
        username="GrahamCanada22",
        team=1,
        kills_ground=1,
        kills_air=0,
        deaths_total=4,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "marks_killed_plane_10_ranks_higher",
            "hidden_all_streak",
            "hidden_base_capturer",
            "tank_die_hard",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "squad_kill",
            "hidden_squad_streaks_2_stage",
            "squad_kill",
            "squad_kill",
            "hidden_squad_streaks_4_stage",
            "squad_best",
        ],
        kill_details=[
            KillDetailTruth("us_m4a1_1942_sherman", "little_leaf_fox", "fr_amx_13_fl_11", 296),
        ],
        death_details=[
            DeathDetailTruth("us_m4a1_1942_sherman", "little_leaf_fox", "f6f-5_france", 400),
            DeathDetailTruth("us_m24_chaffee", "bramcracker7", "germ_sdkfz_234_2", 876),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="1550251896",
        team=1,
        kills_ground=3,
        kills_air=0,
        deaths_total=6,
        awards=[
            "tank_marked_enemy_destroyed_by_ally",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "hidden_assist_streak",
            "squad_assist",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_squad_streaks_2_stage",
            "hidden_allsquad_streak",
            "squad_kill",
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill1_on_fighter",
            "fr_volunteer_cross_streak",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill3_streak",
        ],
        kill_details=[
            KillDetailTruth("f6f-3", "matiz_cubista", "germ_sdkfz_234_2", 358),
        ],
        death_details=[
            DeathDetailTruth("us_m24_chaffee", "ShadowWolf168", "uk_concept3_ngac", 224),
            DeathDetailTruth("us_m4a2_sherman", "RT-7274", "germ_pzkpfw_IV_ausf_H", 499),
            DeathDetailTruth("us_m19", "snakeeater1945", "germ_pzkpfw_IV_ausf_F2", 702),
            DeathDetailTruth("us_m10", "snakeeater1945", "germ_pzkpfw_IV_ausf_H", 908),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="CJQSNBB",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=2,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_2_tank",
            "hidden_kill1_on_tank",
        ],
        kill_details=[
            KillDetailTruth("us_m4_sherman", "Ranol", "sw_sav_fm48", 461),
        ],
        death_details=[
            DeathDetailTruth("us_m10", "snakeeater1945", "germ_pzkpfw_IV_ausf_F2", 301),
            DeathDetailTruth("us_m4_sherman", "snakeeater1945", "germ_pzkpfw_IV_ausf_F2", 658),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="matiz_cubista",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=3,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "tank_die_hard",
            "hidden_all_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("germ_pzsflk40_sturer_emil", "shawn32100", "jp_type_4_chi_to_late", 189),
        ],
        death_details=[
            DeathDetailTruth("germ_pzsflk40_sturer_emil", "shawn32100", "b7a2", 261),
            DeathDetailTruth("germ_sdkfz_234_2", "1550251896", "f6f-3", 358),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="gabrielzonhtmj",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[
            DeathDetailTruth("cn_isu_152", "TakenCeiling338", "germ_pzkpfw_IV_ausf_F2", 190),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="FullcaioDias",
        team=1,
        kills_ground=1,
        kills_air=0,
        deaths_total=2,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_heavy_tank",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
        ],
        kill_details=[
            KillDetailTruth("ussr_kv_1_zis_5", "SQUEX6409", "germ_sdkfz_234_2", 238),
        ],
        death_details=[
            DeathDetailTruth("ussr_kv_1_zis_5", "bramcracker7", "germ_stug_III_ausf_G", 250),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="snakeeater1945",
        team=2,
        kills_ground=5,
        kills_air=0,
        deaths_total=2,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "marks_killed_plane_10_ranks_higher",
            "hidden_all_streak",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "defender_tank",
            "defender_tank",
            "global_avenge_friendly",
            "global_destroy_enemy_marked_by_ally",
            "marks_5_tanks",
            "hidden_all_streak_tank",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("germ_pzkpfw_IV_ausf_F2", "CJQSNBB", "us_m10", 301),
            KillDetailTruth("germ_pzkpfw_IV_ausf_F2", "CJQSNBB", "us_m4_sherman", 658),
            KillDetailTruth("germ_pzkpfw_IV_ausf_F2", "1550251896", "us_m19", 702),
            KillDetailTruth("germ_pzkpfw_IV_ausf_H", "1550251896", "us_m10", 908),
        ],
        death_details=[
            DeathDetailTruth("germ_pzkpfw_IV_ausf_F2", "Palmetto_97", "ussr_kv_1_L_11", 782),
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "Palmetto_97", "ussr_su_122", 1018),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="shawn32100",
        team=1,
        kills_ground=4,
        kills_air=1,
        deaths_total=3,
        awards=[
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "defender_ground",
            "global_avenge_self",
            "hidden_global_avenge_self_stage",
            "hidden_kill3_streak",
            "hidden_marks_1_aircraft",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_die_hard",
            "hidden_all_streak",
        ],
        kill_details=[
            KillDetailTruth("jp_type_4_chi_to_late", "yoncl", "fr_arl_44_acl1", 121),
            KillDetailTruth("jp_type_4_chi_to_late", "Masteryoda6656", "germ_pzkpfw_IV_ausf_J", 152),
            KillDetailTruth("b7a2", "matiz_cubista", "germ_pzsflk40_sturer_emil", 261),
            KillDetailTruth("b7a2", "SQUEX6409", "germ_pzkpfw_IV_ausf_J", 323),
        ],
        death_details=[
            DeathDetailTruth("jp_type_4_chi_to_late", "matiz_cubista", "germ_pzsflk40_sturer_emil", 189),
            DeathDetailTruth("b7a2", "rebajas-bromista", "fw-190a-5_u2", 655),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="bearhntr",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=[],
        kill_details=[],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="BaIIs",
        team=1,
        kills_ground=10,
        kills_air=1,
        deaths_total=3,
        awards=[
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "tank_marked_enemy_destroyed_by_ally",
            "global_destroy_enemy_marked_by_ally",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "tank_marked_enemy_destroyed_by_ally",
            "defender_tank",
            "global_shadow_assassin",
            "hidden_allDef_streak_1_tank",
            "hidden_battlepass_season_22_challenge_7_kill3_without_death",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "marks_killed_plane_10_ranks_higher",
            "tank_kill_without_fail",
            "hidden_all_streak",
            "tank_marked_enemy_destroyed_by_ally",
            "tank_marked_enemy_destroyed_by_ally",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_2_tank",
            "hidden_global_avenge_self_stage",
            "defender_ground",
            "hidden_kill1_on_fighter",
            "hidden_marks_1_aircraft",
            "defender_ground",
            "global_shadow_assassin",
            "marks_5_tanks",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "hidden_all_streak_tank",
            "hidden_kill3_on_fighter",
            "defender_tank",
            "hidden_kill1_on_tank_destroyer",
            "defender_tank",
            "multi_kill_air",
            "tank_kill_without_fail",
            "global_shadow_assassin",
            "hidden_kill3_on_tank_destroyer",
            "tank_kill_without_fail",
            "global_shadow_assassin",
            "hidden_david_2_kill",
            "marks_10_tanks",
            "tank_kill_without_fail",
            "squad_best",
            "trophy_near_punisher",
            "hidden_allNearHeroic_streak",
            "hidden_allNearHeroic_streak_air",
            "hidden_allNearHeroic_streak_tank",
            "hidden_allsquad_streak",
        ],
        kill_details=[
            KillDetailTruth("jp_m24_chaffee", "Nahu_1207", "germ_sdkfz_234_2", 119),
            KillDetailTruth("jp_m24_chaffee", "ShadowWolf168", "uk_17_pdr_m10_achilles", 157),
            KillDetailTruth("jp_m24_chaffee", "ShadowWolf168", "uk_concept3_ngac", 274),
            KillDetailTruth("jp_m24_chaffee", "ShadowWolf168", "uk_17_pdr_m10_achilles", 382),
            KillDetailTruth("ki_61_1a_otsu", "little_leaf_fox", "f6f-5_france", 458),
            KillDetailTruth("ki_61_1a_otsu", "rebajas-bromista", "germ_pzkpfw_IV_ausf_H", 478),
            KillDetailTruth("jp_type_5_na_to", "eyxio", "sw_m24_chaffee_dk", 806),
        ],
        death_details=[
            DeathDetailTruth("jp_m24_chaffee", "ShadowWolf168", "uk_17_pdr_m10_achilles", 382),
            DeathDetailTruth("ki_61_1a_otsu", "little_leaf_fox", "fr_amx_vtt_dca", 633),
            DeathDetailTruth("jp_type_5_na_to", "little_leaf_fox", "fr_m10", 1026),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="YoloRaptorK15222",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=3,
        awards=["hidden_win_streak"],
        kill_details=[],
        death_details=[
            DeathDetailTruth("germ_pzsfl_IVa_dickermax", "crazyranger03", "us_m10", 298),
            DeathDetailTruth("germ_pzkpfw_IV_ausf_J", "ThirtySeven", "cn_m4a4_sherman_1st_ptg", 394),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="yoncl",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=["fr_volunteer_cross_streak", "tank_die_hard", "hidden_all_streak", "hidden_win_streak"],
        kill_details=[],
        death_details=[
            DeathDetailTruth("fr_arl_44_acl1", "shawn32100", "jp_type_4_chi_to_late", 121),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="rebajas-bromista",
        team=2,
        kills_ground=8,
        kills_air=1,
        deaths_total=3,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "hidden_base_capturer",
            "hidden_kill1_on_fighter",
            "defender_ground",
            "hidden_kill3_streak",
            "hidden_marks_1_aircraft",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_2_tank",
            "hidden_kill1_on_tank_destroyer",
            "marks_killed_plane_10_ranks_higher",
            "tank_kill_without_fail",
            "hidden_all_streak",
            "global_shadow_assassin",
            "hidden_kill3_on_tank_destroyer",
            "marks_5_tanks",
            "tank_kill_without_fail",
            "hidden_all_streak_tank",
            "defender_tank",
            "tank_kill_without_fail",
            "global_destroy_enemy_marked_by_ally",
            "global_kills_without_death",
            "tank_kill_without_fail",
            "global_kills_without_death",
            "global_shadow_assassin",
            "tank_kill_without_fail",
            "final_blow",
            "hidden_all_streak_air",
            "hidden_win_streak",
            "squad_best",
            "hidden_allsquad_streak",
        ],
        kill_details=[
            KillDetailTruth("fw-190a-5_u2", "shawn32100", "b7a2", 655),
            KillDetailTruth("germ_stug_III_ausf_F", "crazyranger03", "us_m24_chaffee", 707),
            KillDetailTruth("germ_stug_III_ausf_F", "crazyranger03", "us_m4a1_1942_sherman", 939),
        ],
        death_details=[
            DeathDetailTruth("germ_pzsflk40_sturer_emil", "crazyranger03", "us_m10", 197),
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "BaIIs", "ki_61_1a_otsu", 478),
            DeathDetailTruth("fw-190a-5_u2", "AdrielElProfe", "p-47d_22_re", 656),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="crazyranger03",
        team=1,
        kills_ground=8,
        kills_air=0,
        deaths_total=3,
        awards=[
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill3_on_tank_destroyer",
            "hidden_kill3_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "hidden_base_capturer",
            "fr_volunteer_cross_streak",
            "squad_assist",
            "tank_marked_enemy_destroyed_by_ally",
            "hidden_squad_streaks_2_stage",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_kill1_on_tank",
            "marks_5_tanks",
            "hidden_all_streak_tank",
            "hidden_kill3_on_tank",
            "multi_kill_air",
            "fr_volunteer_cross_streak",
            "heroic_wingman",
            "hidden_allHeroic_streak",
            "hidden_allHeroic_streak_air",
            "hidden_allHeroic_streak_tank",
            "hidden_allNearHeroic_streak",
            "hidden_allNearHeroic_streak_air",
            "hidden_allNearHeroic_streak_tank",
        ],
        kill_details=[
            KillDetailTruth("us_m10", "rebajas-bromista", "germ_pzsflk40_sturer_emil", 197),
            KillDetailTruth("us_m10", "TakenCeiling338", "germ_pzkpfw_IV_ausf_F2", 200),
            KillDetailTruth("us_m10", "YoloRaptorK15222", "germ_pzsfl_IVa_dickermax", 298),
            KillDetailTruth("us_m24_chaffee", "Ranol", "sw_m24_chaffee_dk", 672),
            KillDetailTruth("us_m24_chaffee", "RT-7274", "germ_pzkpfw_IV_ausf_F2", 701),
        ],
        death_details=[
            DeathDetailTruth("us_m10", "eyxio", "sw_sav_m43_1946", 443),
            DeathDetailTruth("us_m24_chaffee", "rebajas-bromista", "germ_stug_III_ausf_F", 707),
            DeathDetailTruth("us_m4a1_1942_sherman", "rebajas-bromista", "germ_stug_III_ausf_F", 939),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="SQUEX6409",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=3,
        awards=["fr_volunteer_cross_streak", "hidden_win_streak"],
        kill_details=[],
        death_details=[
            DeathDetailTruth("germ_sdkfz_234_2", "FullcaioDias", "ussr_kv_1_zis_5", 238),
            DeathDetailTruth("germ_pzkpfw_IV_ausf_J", "shawn32100", "b7a2", 323),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="eyxio",
        team=2,
        kills_ground=4,
        kills_air=0,
        deaths_total=6,
        awards=[
            "tank_help_with_repairing",
            "fr_volunteer_cross_streak",
            "tank_help_with_repairing",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_kill1_on_tank",
            "defender_tank",
            "hidden_kill3_streak",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "global_shadow_assassin",
            "hidden_battlepass_season_22_challenge_7_kill3_without_death",
            "hidden_kill3_on_tank",
            "multi_kill_air",
            "tank_marked_enemy_destroyed_by_ally",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("sw_sav_m43_1946", "crazyranger03", "us_m10", 443),
            KillDetailTruth("sw_m24_chaffee_dk", "ThirtySeven", "cn_m4a4_sherman_1st_ptg", 696),
            KillDetailTruth("sw_m24_chaffee_dk", "Kiritouhu2#1", "us_m44", 704),
        ],
        death_details=[
            DeathDetailTruth("sw_m24_chaffee_dk", "AdrielElProfe", "us_m4a2_sherman", 157),
            DeathDetailTruth("sw_pvkv_III", "ThirtySeven", "cn_m4a4_sherman_1st_ptg", 269),
            DeathDetailTruth("sw_sav_m43_1946", "ThirtySeven", "cn_m4a4_sherman_1st_ptg", 448),
            DeathDetailTruth("sw_l_62_anti_II", "Palmetto_97", "ussr_t_34_1941_l_11", 569),
            DeathDetailTruth("sw_m24_chaffee_dk", "BaIIs", "jp_type_5_na_to", 806),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="AdrielElProfe",
        team=1,
        kills_ground=3,
        kills_air=2,
        deaths_total=1,
        awards=[
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
            "squad_assist",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_squad_streaks_2_stage",
            "hidden_allsquad_streak",
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "hidden_base_capturer",
            "hidden_kill1_on_fighter",
            "defender_bomber",
            "defender_ground",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_air",
            "hidden_kill3_streak",
            "hidden_marks_1_aircraft",
            "global_shadow_assassin",
            "hidden_kill3_on_fighter",
        ],
        kill_details=[
            KillDetailTruth("us_m4a2_sherman", "eyxio", "sw_m24_chaffee_dk", 157),
            KillDetailTruth("p-47d_22_re", "rebajas-bromista", "fw-190a-5_u2", 656),
        ],
        death_details=[
            DeathDetailTruth("us_m4a2_sherman", "bramcracker7", "germ_stug_III_ausf_G", 363),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="TakenCeiling338",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=2,
        awards=[
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "marks_killed_plane_10_ranks_higher",
            "hidden_all_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("germ_pzkpfw_IV_ausf_F2", "gabrielzonhtmj", "cn_isu_152", 190),
        ],
        death_details=[
            DeathDetailTruth("germ_pzkpfw_IV_ausf_F2", "crazyranger03", "us_m10", 200),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Nahu_1207",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=["tank_marked_enemy_destroyed_by_ally", "hidden_win_streak"],
        kill_details=[],
        death_details=[
            DeathDetailTruth("germ_sdkfz_234_2", "BaIIs", "jp_m24_chaffee", 119),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Masteryoda6656",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=["hidden_win_streak"],
        kill_details=[],
        death_details=[
            DeathDetailTruth("germ_pzkpfw_IV_ausf_J", "shawn32100", "jp_type_4_chi_to_late", 152),
            DeathDetailTruth("germ_pzsfl_IVa_dickermax", "ThirtySeven", "cn_m4a4_sherman_1st_ptg", 298),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Palmetto_97",
        team=1,
        kills_ground=5,
        kills_air=0,
        deaths_total=4,
        awards=[
            "fr_volunteer_cross_streak",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "hidden_base_capturer",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "tank_die_hard",
            "hidden_all_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_heavy_tank",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_kill1_on_tank_destroyer",
            "hidden_multitasker_tank_1_kill",
            "marks_5_tanks",
            "marks_killed_plane_10_ranks_higher",
            "hidden_all_streak_tank",
        ],
        kill_details=[
            KillDetailTruth("ussr_t_34_1941_l_11", "Sgt_ Norris Doms", "germ_sdkfz_234_2", 490),
            KillDetailTruth("ussr_t_34_1941_l_11", "eyxio", "sw_l_62_anti_II", 569),
            KillDetailTruth("ussr_kv_1_L_11", "snakeeater1945", "germ_pzkpfw_IV_ausf_F2", 782),
            KillDetailTruth("ussr_su_122", "snakeeater1945", "germ_pzkpfw_IV_ausf_H", 1018),
        ],
        death_details=[
            DeathDetailTruth("ussr_su_152", "Ranol", "sw_t_34_1941", 212),
            DeathDetailTruth("ussr_t_34_1941_l_11", "Sgt_ Norris Doms", "germ_infanterie_kampfpanzer_churchill", 605),
            DeathDetailTruth("ussr_kv_1_L_11", "bramcracker7", "germ_sdkfz_234_2", 932),
            DeathDetailTruth("ussr_su_122", "bramcracker7", "germ_sdkfz_234_2", 1023),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Kilrak_Bloodfang",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=[
            "fr_volunteer_cross_streak",
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
        ],
        kill_details=[],
        death_details=[
            DeathDetailTruth("us_m19", "bramcracker7", "germ_stug_III_ausf_G", 223),
            DeathDetailTruth("us_m42_duster", "bramcracker7", "germ_sdkfz_234_2", 663),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ShadowWolf168",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=3,
        awards=[
            "defender_tank",
            "global_avenge_friendly",
            "global_destroy_enemy_marked_by_ally",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_2_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_tank_destroyer",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            KillDetailTruth("uk_concept3_ngac", "1550251896", "us_m24_chaffee", 224),
            KillDetailTruth("uk_17_pdr_m10_achilles", "BaIIs", "jp_m24_chaffee", 382),
        ],
        death_details=[
            DeathDetailTruth("uk_17_pdr_m10_achilles", "BaIIs", "jp_m24_chaffee", 157),
            DeathDetailTruth("uk_concept3_ngac", "BaIIs", "jp_m24_chaffee", 274),
            DeathDetailTruth("uk_17_pdr_m10_achilles", "BaIIs", "jp_m24_chaffee", 382),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ThirtySeven",
        team=1,
        kills_ground=5,
        kills_air=0,
        deaths_total=1,
        awards=[
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "global_shadow_assassin",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "global_shadow_assassin",
            "multi_kill_air",
            "defender_tank",
            "global_avenge_friendly",
            "global_kills_without_death",
            "global_shadow_assassin",
            "hidden_allDef_streak_1_tank",
            "marks_5_tanks",
            "tank_kill_without_fail",
            "hidden_all_streak_tank",
            "hidden_base_capturer",
            "fr_volunteer_cross_streak",
            "tank_die_hard",
            "hidden_all_streak",
        ],
        kill_details=[
            KillDetailTruth("cn_m4a4_sherman_1st_ptg", "eyxio", "sw_pvkv_III", 269),
            KillDetailTruth("cn_m4a4_sherman_1st_ptg", "Masteryoda6656", "germ_pzsfl_IVa_dickermax", 298),
            KillDetailTruth("cn_m4a4_sherman_1st_ptg", "YoloRaptorK15222", "germ_pzkpfw_IV_ausf_J", 394),
            KillDetailTruth("cn_m4a4_sherman_1st_ptg", "eyxio", "sw_sav_m43_1946", 448),
        ],
        death_details=[
            DeathDetailTruth("cn_m4a4_sherman_1st_ptg", "eyxio", "sw_m24_chaffee_dk", 696),
        ],
        is_author=False,
    ),
]


class TestMetadata:
    def test_session_id(self, replay: dict[str, Any]) -> None:
        assert replay["session_id"] == "6414f3f0024322e"

    def test_player_count(self, replay: dict[str, Any]) -> None:
        assert len(replay["players"]) == 32

    def test_author_username(self, replay: dict[str, Any]) -> None:
        author_truth = next(p for p in PLAYERS if p.is_author)
        assert replay["author"]["username"] == author_truth.username


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
            assert (
                actual >= expected_min
            ), f"{truth.username}: expected at least {expected_min}x '{award_id}', got {actual}"

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
            pytest.xfail(f"{truth.username}: {len(not_found)}/{len(truth.kill_details)} kill detail(s) not resolved")

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
            pytest.xfail(f"{truth.username}: {len(not_found)}/{len(truth.death_details)} death detail(s) not resolved")
