"""
Regression test for parsed replay session 63ef86a001440d4.

Sources:
  - Raw replay:  #2026.03.06 01.16.49.wrpl
  - Battle log:  battle_log_63ef86a001440d4.txt

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

# ---------------------------------------------------------------------------
# Source-of-truth player list
# ---------------------------------------------------------------------------

PLAYERS: list[PlayerTruth] = [
    PlayerTruth(
        username="LMEESH35",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=3,
        awards=[
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
        ],
        kill_details=[],
        death_details=[
            # 3:45 =IMPro= ooxxaa (SAV 20.12.48) destroyed 🎮 LMEESH35 (M4)
            DeathDetailTruth("us_m4_sherman", "ooxxaa", "sw_sav_fm48", 225),
            # 5:12 =CNGDP= Late Noon (✸M24) destroyed 🎮 LMEESH35 (M4A1)
            DeathDetailTruth("us_m4a1_1942_sherman", "Late Noon", "cn_m24_chaffee", 312),
            # 6:40 =CNGDP= Late Noon (✸M24) destroyed 🎮 LMEESH35 (M3A1)
            DeathDetailTruth("us_m3a1_stuart", "Late Noon", "cn_m24_chaffee", 400),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Trember",
        team=1,
        kills_ground=4,
        kills_air=0,
        deaths_total=3,
        awards=[
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "defender_tank",
            "global_shadow_assassin",
            "hidden_allDef_streak_2_tank",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "defender_tank",
            "fr_volunteer_cross_streak",
            "squad_assist",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
        ],
        kill_details=[
            # 1:45 [Vaygr] Trember (Pz.IV H) destroyed 🎮 LarryErkniq (M4A2)
            KillDetailTruth("germ_pzkpfw_IV_ausf_H", "LarryErkniq", "us_m4a2_sherman", 105),
            # 4:38 [Vaygr] Trember (Pz.IV H) destroyed =Vizzy= 🎮 C DESTROYER26 (M55)
            KillDetailTruth("germ_pzkpfw_IV_ausf_H", "C DESTROYER26", "us_m55", 278),
            # 8:25 [Vaygr] Trember (Pz.IV H) destroyed StealthCookie (M44)
            KillDetailTruth("germ_pzkpfw_IV_ausf_H", "StealthCookie", "us_m44", 505),
            # 9:44 [Vaygr] Trember (Pz.IV H) destroyed =Vizzy= 🎮 C DESTROYER26 (M4A2)
            KillDetailTruth("germ_pzkpfw_IV_ausf_H", "C DESTROYER26", "us_m4a2_sherman", 584),
        ],
        death_details=[
            # 10:32 🎮 channdro (KV-1E) destroyed [Vaygr] Trember (Pz.IV H)
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "channdro", "ussr_kv_1e", 632),
            # 11:44 StealthCookie (M55) destroyed [Vaygr] Trember (Pz.IV G)
            DeathDetailTruth("germ_pzkpfw_IV_ausf_G", "StealthCookie", "us_m55", 704),
            # 12:39 =TDGL= ExtremistMagpie (ZiS-12 (94-KM)) destroyed [Vaygr] Trember (Pz.IV F2)
            DeathDetailTruth("germ_pzkpfw_IV_ausf_F2", "ExtremistMagpie", "ussr_zis_12_94KM_1945", 759),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="MGrizzB",
        team=2,
        kills_ground=9,
        kills_air=0,
        deaths_total=4,
        awards=[
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
            "tank_marked_enemy_destroyed_by_ally",
            "global_shadow_assassin",
            "hidden_battlepass_season_22_challenge_7_kill3_without_death",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "hidden_kill1_on_fighter",
            "defender_ground",
            "global_destroy_enemy_marked_by_ally",
            "marks_5_tanks",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "hidden_all_streak_tank",
            "hidden_kill3_on_fighter",
            "multi_kill_air",
            "multi_kill_air",
            "hidden_win_streak",
        ],
        kill_details=[
            # 2:30 MGrizzB (⊙M24) destroyed 🎮 Stampedinbuny420 (Pz.IV H)
            KillDetailTruth("it_m24_chaffee", "Stampedinbuny420", "germ_pzkpfw_IV_ausf_H", 150),
            # 3:50 MGrizzB (⊙M24) destroyed =285AW= autumn1196 (Na-To)
            KillDetailTruth("it_m24_chaffee", "autumn1196", "jp_type_5_na_to", 230),
            # 4:45 MGrizzB (⊙M24) destroyed i_Scorched (Pz.IV H)
            KillDetailTruth("it_m24_chaffee", "i_Scorched", "germ_pzkpfw_IV_ausf_H", 285),
            # 6:42 MGrizzB (🇨🇭Bf 109 F) destroyed -4b0- Wiggle#6 (Ystervark)
            KillDetailTruth("bf-109f-4_hungary", "Wiggle#6", "uk_ystervark_spaa", 402),
            # 7:04 MGrizzB (🇨🇭Bf 109 F) destroyed Laughing Hawk (⊙M4A1)
            KillDetailTruth("bf-109f-4_hungary", "Laughing Hawk", "fr_m4a1_sherman", 424),
            # 7:20 MGrizzB (🇨🇭Bf 109 F) destroyed -4b0- Wiggle#6 (Ystervark)
            KillDetailTruth("bf-109f-4_hungary", "Wiggle#6", "uk_ystervark_spaa", 440),
            # 8:58 MGrizzB (🇨🇭Bf 109 F) destroyed i_Scorched (Sd.Kfz.251/21)
            KillDetailTruth("bf-109f-4_hungary", "i_Scorched", "germ_sdkfz_251_21", 538),
            # 9:49 MGrizzB (🇨🇭Bf 109 F) destroyed ^UAOD^ ChasingRapture (Crusader AA Mk II)
            KillDetailTruth("bf-109f-4_hungary", "ChasingRapture", "uk_crusader_aa_mk_2", 589),
            # 10:05 MGrizzB (🇨🇭Bf 109 F) destroyed Laughing Hawk (VTT DCA)
            KillDetailTruth("bf-109f-4_hungary", "Laughing Hawk", "fr_amx_vtt_dca", 605),
        ],
        death_details=[
            # 5:38 ^UAOD^ ChasingRapture (Churchill NA75) destroyed MGrizzB (⊙M24)
            DeathDetailTruth("it_m24_chaffee", "ChasingRapture", "uk_churchill_na75", 338),
            # 7:56 -4b0- Wiggle#6 (Sherman VC) shot down MGrizzB (🇨🇭Bf 109 F)
            DeathDetailTruth("bf-109f-4_hungary", "Wiggle#6", "uk_sherman_vc_firefly", 476),
            # 10:43 Laughing Hawk (VTT DCA) shot down MGrizzB (🇨🇭Bf 109 F)
            DeathDetailTruth("bf-109f-4_hungary", "Laughing Hawk", "fr_amx_vtt_dca", 643),
            # 12:07 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed MGrizzB (M42)
            DeathDetailTruth("it_m15_42_contraereo", "IBecameTheAmmo", "germ_sdkfz_9_flak37", 727),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Pro_Gamer_20000",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=4,
        awards=[
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "marks_killed_plane_10_ranks_higher",
            "hidden_all_streak",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "squad_kill",
            "hidden_squad_streaks_2_stage",
            "fr_volunteer_cross_streak",
            "tank_marked_enemy_destroyed_by_ally",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_win_streak",
            "squad_best",
        ],
        kill_details=[
            # 2:23 =TDGL= Pro_Gamer_20000 (SU-76M) destroyed =285AW= autumn1196 (☆M24)
            KillDetailTruth("ussr_su_76m_1943", "autumn1196", "jp_m24_chaffee", 143),
            # 11:39 =TDGL= Pro_Gamer_20000 (T-34) destroyed Ranol (Pvkv II)
            KillDetailTruth("ussr_t_34_1941_l_11", "Ranol", "sw_pvkv_II", 699),
        ],
        death_details=[
            # 4:07 USS_Liberty_K1K3 (Pvkv m/43 (1946)) destroyed =TDGL= Pro_Gamer_20000 (SU-76M)
            DeathDetailTruth("ussr_su_76m_1943", "USS_Liberty_K1K3", "sw_pvkv_m43_1946", 247),
            # 7:24 Ranol (SAV 20.12.48) destroyed =TDGL= Pro_Gamer_20000 (T-50)
            DeathDetailTruth("ussr_t_50", "Ranol", "sw_sav_fm48", 444),
            # 8:20 =JPs3V= _SP23 (Chi-To) destroyed =TDGL= Pro_Gamer_20000 (BT-7M)
            DeathDetailTruth("ussr_bt_7_m", "_SP23", "jp_type_4_chi_to", 500),
            # 12:19 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed =TDGL= Pro_Gamer_20000 (T-34)
            DeathDetailTruth("ussr_t_34_1941_l_11", "IBecameTheAmmo", "germ_sdkfz_9_flak37", 739),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="IBecameTheAmmo",
        team=1,
        kills_ground=5,
        kills_air=0,
        deaths_total=2,
        awards=[
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "defender_tank",
            "global_shadow_assassin",
            "hidden_allDef_streak_1_tank",
            "hidden_kill3_on_tank_destroyer",
            "hidden_kill3_streak",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_allMulty_streak",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_kill_without_fail",
            "global_kills_without_death",
            "global_shadow_assassin",
            "marks_5_tanks",
            "tank_kill_without_fail",
            "hidden_all_streak_tank",
        ],
        kill_details=[
            # 11:13 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed =Vizzy= 🎮 C DESTROYER26 (M55)
            KillDetailTruth("germ_sdkfz_9_flak37", "C DESTROYER26", "us_m55", 673),
            # 12:07 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed MGrizzB (M42)
            KillDetailTruth("germ_sdkfz_9_flak37", "MGrizzB", "it_m15_42_contraereo", 727),
            # 12:19 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed =TDGL= Pro_Gamer_20000 (T-34)
            KillDetailTruth("germ_sdkfz_9_flak37", "Pro_Gamer_20000", "ussr_t_34_1941_l_11", 739),
            # 12:49 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed =Vizzy= 🎮 C DESTROYER26 (T77E1)
            KillDetailTruth("germ_sdkfz_9_flak37", "C DESTROYER26", "us_t77e1", 769),
            # 13:27 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed 🎮 Darkcart 8430 (M10)
            KillDetailTruth("germ_sdkfz_9_flak37", "Darkcart 8430", "us_m10", 807),
        ],
        death_details=[
            # 6:41 =TDGL= SCHNOOKUMSPRIME (P-400) destroyed =KPOHA= IBecameTheAmmo (Pz.IV H)
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "SCHNOOKUMSPRIME", "p-400", 401),
            # 14:15 .Rdh1.Bymemory (La-5) destroyed =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.)
            DeathDetailTruth("germ_sdkfz_9_flak37", "Bymemory", "la-5fn", 855),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="_SP23",
        team=1,
        kills_ground=4,
        kills_air=0,
        deaths_total=3,
        awards=[
            "tank_marked_enemy_destroyed_by_ally",
            "tank_marked_enemy_destroyed_by_ally",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "tank_marked_enemy_destroyed_by_ally",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_2_tank",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "tank_kill_without_fail",
            "fr_volunteer_cross_streak",
        ],
        kill_details=[
            # 4:08 =JPs3V= _SP23 (☆M24) destroyed 🎮 Darkcart 8430 (M24)
            KillDetailTruth("jp_m24_chaffee", "Darkcart 8430", "us_m24_chaffee", 248),
            # 8:20 =JPs3V= _SP23 (Chi-To) destroyed =TDGL= Pro_Gamer_20000 (BT-7M)
            KillDetailTruth("jp_type_4_chi_to", "Pro_Gamer_20000", "ussr_bt_7_m", 500),
            # 11:56 =JPs3V= _SP23 (Chi-Nu) destroyed StealthCookie (M55)
            KillDetailTruth("jp_type_3_chi_nu", "StealthCookie", "us_m55", 716),
            # 13:08 =JPs3V= _SP23 (Chi-Nu) destroyed =TDGL= SCHNOOKUMSPRIME (M24)
            KillDetailTruth("jp_type_3_chi_nu", "SCHNOOKUMSPRIME", "us_m24_chaffee", 788),
        ],
        death_details=[
            # 5:38 [iCAT] ACCTGU 145 (T-34-57) destroyed =JPs3V= _SP23 (☆M24)
            DeathDetailTruth("jp_m24_chaffee", "ACCTGU 145", "ussr_t_34_1941_57", 338),
            # 9:29 .Rdh1.Bymemory (T-34) destroyed =JPs3V= _SP23 (Chi-To)
            DeathDetailTruth("jp_type_4_chi_to", "Bymemory", "ussr_t_34_1941_cast_turret", 569),
            # 14:34 ZaddyLongStyle (M4A1) destroyed =JPs3V= _SP23 (Chi-Nu)
            DeathDetailTruth("jp_type_3_chi_nu", "ZaddyLongStyle", "us_m4a1_1942_sherman", 874),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="\u041b\u0435\u0439\u0442\u0435\u043d\u0430\u043d\u0442 \u0415\u0431\u043e\u043d\u043e\u0432",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=1,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_heavy_tank",
            "hidden_kill_streak",
            "global_destroy_enemy_marked_by_ally",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            # 2:24 =TROY= Лейтенант Ебонов (T14) destroyed i_Scorched (Marder III H)
            KillDetailTruth("us_t14", "i_Scorched", "germ_pzkpfw_38t_Marder_III_ausf_H", 144),
            # 2:51 =TROY= Лейтенант Ебонов (T14) destroyed ^UAOD^ ChasingRapture (Sherman VC)
            KillDetailTruth("us_t14", "ChasingRapture", "uk_sherman_vc_firefly", 171),
        ],
        death_details=[],
        is_author=False,
    ),
    PlayerTruth(
        username="autumn1196",
        team=1,
        kills_ground=0,
        kills_air=4,
        deaths_total=5,
        awards=[
            "fr_volunteer_cross_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill_streak",
            "hidden_marks_1_aircraft",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "tank_die_hard",
            "hidden_all_streak",
            "hidden_kill1_on_fighter",
            "hidden_kill3_streak",
            "hidden_marks_3_fighters",
            "fr_volunteer_cross_streak",
        ],
        kill_details=[
            # 7:04 =285AW= autumn1196 (☆M19A1) shot down =TDGL= ExtremistMagpie (I-185)
            KillDetailTruth("jp_m19", "ExtremistMagpie", "i_185_m82", 424),
            # 7:27 =285AW= autumn1196 (☆M19A1) shot down 🎮 channdro (★P-47D)
            KillDetailTruth("jp_m19", "channdro", "p-47d_ussr", 447),
            # 10:52 =285AW= autumn1196 (Ki-43) shot down [iCAT] ACCTGU 145 (Yak-9T)
            KillDetailTruth("ki_43_3_otsu", "ACCTGU 145", "yak-9t", 652),
            # 13:26 =285AW= autumn1196 (Ki-43) shot down StealthCookie (P-51)
            KillDetailTruth("ki_43_3_otsu", "StealthCookie", "p-51_mk1a_usaaf", 806),
        ],
        death_details=[
            # 2:23 =TDGL= Pro_Gamer_20000 (SU-76M) destroyed =285AW= autumn1196 (☆M24)
            DeathDetailTruth("jp_m24_chaffee", "Pro_Gamer_20000", "ussr_su_76m_1943", 143),
            # 3:50 MGrizzB (⊙M24) destroyed =285AW= autumn1196 (Na-To)
            DeathDetailTruth("jp_type_5_na_to", "MGrizzB", "it_m24_chaffee", 230),
            # 6:32 .Rdh1.Bymemory (T-34) destroyed =285AW= autumn1196 (☆M42)
            DeathDetailTruth("jp_m42_duster", "Bymemory", "ussr_t_34_1941_cast_turret", 392),
            # 9:37 .Rdh1.Bymemory (T-34) destroyed =285AW= autumn1196 (☆M19A1)
            DeathDetailTruth("jp_m19", "Bymemory", "ussr_t_34_1941_cast_turret", 577),
            # 13:26 =285AW= autumn1196 (Ki-43) has crashed.
            DeathDetailTruth("ki_43_3_otsu", time_seconds=806),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ZaddyLongStyle",
        team=2,
        kills_ground=3,
        kills_air=0,
        deaths_total=2,
        awards=[
            "fr_volunteer_cross_streak",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            # 6:21 ZaddyLongStyle (M24) destroyed 🎮 Stampedinbuny420 (StuG III G)
            KillDetailTruth("us_m24_chaffee", "Stampedinbuny420", "germ_stug_III_ausf_G", 381),
            # 10:23 ZaddyLongStyle (M24) destroyed Ranol (M24DK)
            KillDetailTruth("us_m24_chaffee", "Ranol", "sw_m24_chaffee_dk", 623),
            # 14:34 ZaddyLongStyle (M4A1) destroyed =JPs3V= _SP23 (Chi-Nu)
            KillDetailTruth("us_m4a1_1942_sherman", "_SP23", "jp_type_3_chi_nu", 874),
        ],
        death_details=[
            # 3:51 ql toxic lp (Sherman VC) destroyed ZaddyLongStyle (M10)
            DeathDetailTruth("us_m10", "ql toxic lp", "uk_sherman_vc_firefly", 231),
            # 13:27 Ranol (SAV 20.12.48) destroyed ZaddyLongStyle (M24)
            DeathDetailTruth("us_m24_chaffee", "Ranol", "sw_sav_fm48", 807),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="LarryErkniq",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
        ],
        kill_details=[],
        death_details=[
            # 1:45 [Vaygr] Trember (Pz.IV H) destroyed 🎮 LarryErkniq (M4A2)
            DeathDetailTruth("us_m4a2_sherman", "Trember", "germ_pzkpfw_IV_ausf_H", 105),
            # 4:00 =CNGDP= Late Noon (✸M24) destroyed 🎮 LarryErkniq (M4)
            DeathDetailTruth("us_m4_sherman", "Late Noon", "cn_m24_chaffee", 240),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ACCTGU 145",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=2,
        awards=[
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "row_air_assist",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
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
            # 5:38 [iCAT] ACCTGU 145 (T-34-57) destroyed =JPs3V= _SP23 (☆M24)
            KillDetailTruth("ussr_t_34_1941_57", "_SP23", "jp_m24_chaffee", 338),
        ],
        death_details=[
            # 6:26 =CNGDP= Late Noon (✸M24) destroyed [iCAT] ACCTGU 145 (T-34-57)
            DeathDetailTruth("ussr_t_34_1941_57", "Late Noon", "cn_m24_chaffee", 386),
            # 10:52 =285AW= autumn1196 (Ki-43) shot down [iCAT] ACCTGU 145 (Yak-9T)
            DeathDetailTruth("yak-9t", "autumn1196", "ki_43_3_otsu", 652),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Ranol",
        team=1,
        kills_ground=7,
        kills_air=1,
        deaths_total=6,
        awards=[
            "hidden_base_capturer",
            "tank_die_hard",
            "hidden_all_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_2_tank",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill3_streak",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_allMulty_streak",
            "global_shadow_assassin",
            "hidden_kill3_on_tank_destroyer",
            "multi_kill_air",
            "tank_kill_without_fail",
            "global_shadow_assassin",
            "marks_5_tanks",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_all_streak_tank",
            "global_base_capturer",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "tank_kill_without_fail",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "tank_kill_without_fail",
            "fr_volunteer_cross_streak",
            "hidden_assist_streak",
            "defender_tank",
            "final_blow",
            "hidden_all_streak_air",
            "hidden_marks_1_aircraft",
        ],
        kill_details=[
            # 4:41 Ranol (⊙T-34) destroyed 🎮 channdro (ASU-57)
            KillDetailTruth("sw_t_34_1941", "channdro", "ussr_asu_57", 281),
            # 7:16 Ranol (SAV 20.12.48) destroyed 🎮 Darkcart 8430 (M4A2)
            KillDetailTruth("sw_sav_fm48", "Darkcart 8430", "us_m4a2_sherman", 436),
            # 7:24 Ranol (SAV 20.12.48) destroyed =TDGL= Pro_Gamer_20000 (T-50)
            KillDetailTruth("sw_sav_fm48", "Pro_Gamer_20000", "ussr_t_50", 444),
            # 7:39 Ranol (SAV 20.12.48) destroyed 🎮 DARKLORD574699 (M16)
            KillDetailTruth("sw_sav_fm48", "DARKLORD574699", "us_halftrack_m16", 459),
            # 7:52 Ranol (SAV 20.12.48) destroyed Jandamarra (ASU-57)
            KillDetailTruth("sw_sav_fm48", "Jandamarra", "ussr_asu_57", 472),
            # 11:26 Ranol (Pvkv II) destroyed 🎮 Darkcart 8430 (M10)
            KillDetailTruth("sw_pvkv_II", "Darkcart 8430", "us_m10", 686),
            # 13:27 Ranol (SAV 20.12.48) destroyed ZaddyLongStyle (M24)
            KillDetailTruth("sw_sav_fm48", "ZaddyLongStyle", "us_m24_chaffee", 807),
            # 15:06 Ranol (Pbv 301) shot down .Rdh1.Bymemory (La-5)
            KillDetailTruth("sw_pbv_301", "Bymemory", "la-5fn", 906),
        ],
        death_details=[
            # 4:53 =TDGL= SCHNOOKUMSPRIME (M4A1) destroyed Ranol (⊙T-34)
            DeathDetailTruth("sw_t_34_1941", "SCHNOOKUMSPRIME", "us_m4a1_1942_sherman", 293),
            # 8:51 .Rdh1.Bymemory (T-34) destroyed Ranol (SAV 20.12.48)
            DeathDetailTruth("sw_sav_fm48", "Bymemory", "ussr_t_34_1941_cast_turret", 531),
            # 10:23 ZaddyLongStyle (M24) destroyed Ranol (M24DK)
            DeathDetailTruth("sw_m24_chaffee_dk", "ZaddyLongStyle", "us_m24_chaffee", 623),
            # 11:39 =TDGL= Pro_Gamer_20000 (T-34) destroyed Ranol (Pvkv II)
            DeathDetailTruth("sw_pvkv_II", "Pro_Gamer_20000", "ussr_t_34_1941_l_11", 699),
            # 12:31 🎮 channdro (KV-1E) destroyed Ranol (⊙Pz.IV)
            DeathDetailTruth("sw_pzkpfw_IV_ausf_J", "channdro", "ussr_kv_1e", 751),
            # 14:24 🎮 channdro (★P-47D) destroyed Ranol (SAV 20.12.48)
            DeathDetailTruth("sw_sav_fm48", "channdro", "p-47d_ussr", 864),
        ],
        is_author=True,
    ),
    PlayerTruth(
        username="StealthCookie",
        team=2,
        kills_ground=3,
        kills_air=0,
        deaths_total=4,
        awards=[
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_2_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill3_on_tank_destroyer",
            "hidden_kill3_streak",
            "hidden_base_capturer",
            "hidden_win_streak",
        ],
        kill_details=[
            # 2:41 StealthCookie (M55) destroyed Laughing Hawk (ARL-44 (ACL-1))
            KillDetailTruth("us_m55", "Laughing Hawk", "fr_arl_44_acl1", 161),
            # 5:17 StealthCookie (M44) destroyed ql toxic lp (Sherman VC)
            KillDetailTruth("us_m44", "ql toxic lp", "uk_sherman_vc_firefly", 317),
            # 11:44 StealthCookie (M55) destroyed [Vaygr] Trember (Pz.IV G)
            KillDetailTruth("us_m55", "Trember", "germ_pzkpfw_IV_ausf_G", 704),
        ],
        death_details=[
            # 4:25 USS_Liberty_K1K3 (Pvkv m/43 (1946)) destroyed StealthCookie (M55)
            DeathDetailTruth("us_m55", "USS_Liberty_K1K3", "sw_pvkv_m43_1946", 265),
            # 8:25 [Vaygr] Trember (Pz.IV H) destroyed StealthCookie (M44)
            DeathDetailTruth("us_m44", "Trember", "germ_pzkpfw_IV_ausf_H", 505),
            # 11:56 =JPs3V= _SP23 (Chi-Nu) destroyed StealthCookie (M55)
            DeathDetailTruth("us_m55", "_SP23", "jp_type_3_chi_nu", 716),
            # 13:26 =285AW= autumn1196 (Ki-43) shot down StealthCookie (P-51)
            DeathDetailTruth("p-51_mk1a_usaaf", "autumn1196", "ki_43_3_otsu", 806),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Wiggle#6",
        team=1,
        kills_ground=0,
        kills_air=1,
        deaths_total=5,
        awards=[
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "row_air_assist",
            "squad_assist",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_squad_streaks_2_stage",
            "hidden_allsquad_streak",
            "fr_volunteer_cross_streak",
            "hidden_assist_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_1_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "hidden_marks_1_aircraft",
        ],
        kill_details=[
            # 7:56 -4b0- Wiggle#6 (Sherman VC) shot down MGrizzB (🇨🇭fBf 109 F)
            KillDetailTruth("uk_sherman_vc_firefly", "MGrizzB", "bf-109f-4_hungary", 476),
        ],
        death_details=[
            # 4:03 =Vizzy= 🎮 C DESTROYER26 (M55) destroyed -4b0- Wiggle#6 (Churchill VII)
            DeathDetailTruth("uk_a_22f_mk_7_churchill_1944", "C DESTROYER26", "us_m55", 243),
            # 5:45 🎮 channdro (★P-47D) destroyed -4b0- Wiggle#6 (Avenger)
            DeathDetailTruth("uk_a30_sp_avenger", "channdro", "p-47d_ussr", 345),
            # 6:42 MGrizzB (🇨🇭fBf 109 F) destroyed -4b0- Wiggle#6 (Ystervark)
            DeathDetailTruth("uk_ystervark_spaa", "MGrizzB", "bf-109f-4_hungary", 402),
            # 7:20 MGrizzB (🇨🇭fBf 109 F) destroyed -4b0- Wiggle#6 (Ystervark)
            DeathDetailTruth("uk_ystervark_spaa", "MGrizzB", "bf-109f-4_hungary", 440),
            # 9:07 .Rdh1.Bymemory (T-34) destroyed -4b0- Wiggle#6 (Sherman VC)
            DeathDetailTruth("uk_sherman_vc_firefly", "Bymemory", "ussr_t_34_1941_cast_turret", 547),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ql toxic lp",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=3,
        awards=[
            "fr_volunteer_cross_streak",
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
        ],
        kill_details=[
            # 3:51 ql toxic lp (Sherman VC) destroyed ZaddyLongStyle (M10)
            KillDetailTruth("uk_sherman_vc_firefly", "ZaddyLongStyle", "us_m10", 231),
            # 5:04 ql toxic lp (Sherman VC) destroyed 🎮 DARKLORD574699 (M16)
            KillDetailTruth("uk_sherman_vc_firefly", "DARKLORD574699", "us_halftrack_m16", 304),
        ],
        death_details=[
            # 5:17 StealthCookie (M44) destroyed ql toxic lp (Sherman VC)
            DeathDetailTruth("uk_sherman_vc_firefly", "StealthCookie", "us_m44", 317),
            # 6:35 🎮 channdro (★P-47D) destroyed ql toxic lp (Sherman VC)
            DeathDetailTruth("uk_sherman_vc_firefly", "channdro", "p-47d_ussr", 395),
            # 7:18 .Rdh1.Bymemory (T-34) destroyed ql toxic lp (Achilles)
            DeathDetailTruth("uk_17_pdr_m10_achilles", "Bymemory", "ussr_t_34_1941_cast_turret", 438),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="SCHNOOKUMSPRIME",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=3,
        awards=[
            "tank_help_with_repairing",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "hidden_base_capturer",
            "hidden_kill1_on_fighter",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
            "squad_best",
            "hidden_allsquad_streak",
        ],
        kill_details=[
            # 4:53 =TDGL= SCHNOOKUMSPRIME (M4A1) destroyed Ranol (⊙T-34)
            KillDetailTruth("us_m4a1_1942_sherman", "Ranol", "sw_t_34_1941", 293),
            # 6:41 =TDGL= SCHNOOKUMSPRIME (P-400) destroyed =KPOHA= IBecameTheAmmo (Pz.IV H)
            KillDetailTruth("p-400", "IBecameTheAmmo", "germ_pzkpfw_IV_ausf_H", 401),
        ],
        death_details=[
            # 5:03 Laughing Hawk (⊙M4A1) destroyed =TDGL= SCHNOOKUMSPRIME (M4A1)
            DeathDetailTruth("us_m4a1_1942_sherman", "Laughing Hawk", "fr_m4a1_sherman", 303),
            # 6:50 =TDGL= SCHNOOKUMSPRIME (P-400) has crashed.
            DeathDetailTruth("p-400", time_seconds=410),
            # 13:08 =JPs3V= _SP23 (Chi-Nu) destroyed =TDGL= SCHNOOKUMSPRIME (M24)
            DeathDetailTruth("us_m24_chaffee", "_SP23", "jp_type_3_chi_nu", 788),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Jandamarra",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[
            "tank_help_with_repairing",
            "hidden_base_capturer",
            "global_base_capturer",
            "hidden_win_streak",
        ],
        kill_details=[],
        death_details=[
            # 7:52 Ranol (SAV 20.12.48) destroyed Jandamarra (ASU-57)
            DeathDetailTruth("ussr_asu_57", "Ranol", "sw_sav_fm48", 472),
            # 9:15 Laughing Hawk (VTT DCA) shot down Jandamarra (Yak-3)
            DeathDetailTruth("yak-3", "Laughing Hawk", "fr_amx_vtt_dca", 555),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="channdro",
        team=2,
        kills_ground=10,
        kills_air=0,
        deaths_total=4,
        awards=[
            "first_blood",
            "hidden_all_streak",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
            "tank_marked_enemy_destroyed_by_ally",
            "tank_marked_enemy_destroyed_by_ally",
            "hidden_kill1_on_fighter",
            "defender_ground",
            "global_avenge_friendly",
            "global_destroy_enemy_marked_by_ally",
            "global_shadow_assassin",
            "hidden_kill3_on_fighter",
            "hidden_kill3_streak",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "marks_5_tanks",
            "multi_kill_air",
            "hidden_all_streak_tank",
            "fr_volunteer_cross_streak",
            "hidden_base_capturer",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_heavy_tank",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "tank_die_hard",
            "defender_tank",
            "hidden_kill3_on_heavy_tank",
            "multi_kill_air",
            "fr_volunteer_cross_streak",
            "defender_ground",
            "global_base_defender",
            "global_avenge_self",
            "global_base_defender",
            "hidden_global_avenge_self_stage",
            "marks_10_tanks",
            "multi_kill_air",
            "hidden_win_streak",
        ],
        kill_details=[
            # 1:38 🎮 channdro (ASU-57) destroyed Starka228 (Marder III H)
            KillDetailTruth("ussr_asu_57", "Starka228", "germ_pzkpfw_38t_Marder_III_ausf_H", 98),
            # 5:45 🎮 channdro (★P-47D) destroyed -4b0- Wiggle#6 (Avenger)
            KillDetailTruth("p-47d_ussr", "Wiggle#6", "uk_a30_sp_avenger", 345),
            # 6:06 🎮 channdro (★P-47D) destroyed ^UAOD^ ChasingRapture (Churchill NA75)
            KillDetailTruth("p-47d_ussr", "ChasingRapture", "uk_churchill_na75", 366),
            # 6:06 🎮 channdro (★P-47D) destroyed Undertaker1134 (Crusader III)
            KillDetailTruth("p-47d_ussr", "Undertaker1134", "uk_crusader_mk_3", 366),
            # 6:35 🎮 channdro (★P-47D) destroyed ql toxic lp (Sherman VC)
            KillDetailTruth("p-47d_ussr", "ql toxic lp", "uk_sherman_vc_firefly", 395),
            # 10:32 🎮 channdro (KV-1E) destroyed [Vaygr] Trember (Pz.IV H)
            KillDetailTruth("ussr_kv_1e", "Trember", "germ_pzkpfw_IV_ausf_H", 632),
            # 12:12 🎮 channdro (KV-1E) destroyed ^UAOD^ ChasingRapture (Crusader AA Mk II)
            KillDetailTruth("ussr_kv_1e", "ChasingRapture", "uk_crusader_aa_mk_2", 732),
            # 12:31 🎮 channdro (KV-1E) destroyed Ranol (⊙Pz.IV)
            KillDetailTruth("ussr_kv_1e", "Ranol", "sw_pzkpfw_IV_ausf_J", 751),
            # 14:24 🎮 channdro (★P-47D) destroyed Ranol (SAV 20.12.48)
            KillDetailTruth("p-47d_ussr", "Ranol", "sw_sav_fm48", 864),
            # 14:44 🎮 channdro (★P-47D) destroyed ^UAOD^ ChasingRapture (Concept 3)
            KillDetailTruth("p-47d_ussr", "ChasingRapture", "uk_concept3_ngac", 884),
        ],
        death_details=[
            # 4:41 Ranol (⊙T-34) destroyed 🎮 channdro (ASU-57)
            DeathDetailTruth("ussr_asu_57", "Ranol", "sw_t_34_1941", 281),
            # 7:27 =285AW= autumn1196 (☆M19A1) shot down 🎮 channdro (★P-47D)
            DeathDetailTruth("p-47d_ussr", "autumn1196", "jp_m19", 447),
            # 13:21 ^UAOD^ ChasingRapture (Concept 3) destroyed 🎮 channdro (KV-1E)
            DeathDetailTruth("ussr_kv_1e", "ChasingRapture", "uk_concept3_ngac", 801),
            # 15:04 ^UAOD^ ChasingRapture (⊙M44) shot down 🎮 channdro (★P-47D)
            DeathDetailTruth("p-47d_ussr", "ChasingRapture", "uk_m44", 904),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Late Noon",
        team=1,
        kills_ground=8,
        kills_air=0,
        deaths_total=1,
        awards=[
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "global_destroy_enemy_marked_by_ally",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "tank_kill_without_fail",
            "defender_tank",
            "global_shadow_assassin",
            "hidden_allDef_streak_2_tank",
            "marks_killed_plane_10_ranks_higher",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_allMulty_streak",
            "hidden_all_streak",
            "defender_tank",
            "global_kills_without_death",
            "marks_5_tanks",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_all_streak_tank",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "tank_die_hard",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "squad_best",
        ],
        kill_details=[
            # 4:00 =CNGDP= Late Noon (✸M24) destroyed 🎮 LarryErkniq (M4)
            KillDetailTruth("cn_m24_chaffee", "LarryErkniq", "us_m4_sherman", 240),
            # 5:12 =CNGDP= Late Noon (✸M24) destroyed 🎮 LMEESH35 (M4A1)
            KillDetailTruth("cn_m24_chaffee", "LMEESH35", "us_m4a1_1942_sherman", 312),
            # 6:18 =CNGDP= Late Noon (✸M24) destroyed =Vizzy= 🎮 C DESTROYER26 (M4A2)
            KillDetailTruth("cn_m24_chaffee", "C DESTROYER26", "us_m4a2_sherman", 378),
            # 6:26 =CNGDP= Late Noon (✸M24) destroyed [iCAT] ACCTGU 145 (T-34-57)
            KillDetailTruth("cn_m24_chaffee", "ACCTGU 145", "ussr_t_34_1941_57", 386),
            # 6:40 =CNGDP= Late Noon (✸M24) destroyed 🎮 LMEESH35 (M3A1)
            KillDetailTruth("cn_m24_chaffee", "LMEESH35", "us_m3a1_stuart", 400),
            # 10:49 =CNGDP= Late Noon (✸M4A4 (1st PTG)) destroyed =TDGL= ExtremistMagpie (SMK)
            KillDetailTruth("cn_m4a4_sherman_1st_ptg", "ExtremistMagpie", "ussr_smk", 649),
            # 12:20 =CNGDP= Late Noon (✸M4A4 (1st PTG)) destroyed .Rdh1.Bymemory (T-34)
            KillDetailTruth("cn_m4a4_sherman_1st_ptg", "Bymemory", "ussr_t_34_1941_cast_turret", 740),
            # 13:51 =CNGDP= Late Noon (✸M4A4 (1st PTG)) destroyed =TDGL= ExtremistMagpie (ZiS-12 (94-KM))
            KillDetailTruth("cn_m4a4_sherman_1st_ptg", "ExtremistMagpie", "ussr_zis_12_94KM_1945", 831),
        ],
        death_details=[
            # 8:28 =Vizzy= 🎮 C DESTROYER26 (M4A2) destroyed =CNGDP= Late Noon (✸M24)
            DeathDetailTruth("cn_m24_chaffee", "C DESTROYER26", "us_m4a2_sherman", 508),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ChasingRapture",
        team=1,
        kills_ground=2,
        kills_air=2,
        deaths_total=5,
        awards=[
            "tank_die_hard",
            "hidden_all_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_heavy_tank",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_friendly",
            "hidden_allDef_streak_2_tank",
            "hidden_marks_1_aircraft",
            "fr_volunteer_cross_streak",
            "hidden_assist_streak",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_tank",
            "hidden_kill3_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_kill1_on_tank_destroyer",
            "hidden_multitasker_tank_1_kill",
        ],
        kill_details=[
            # 5:38 ^UAOD^ ChasingRapture (Churchill NA75) destroyed MGrizzB (⊙M24)
            KillDetailTruth("uk_churchill_na75", "MGrizzB", "it_m24_chaffee", 338),
            # 13:21 ^UAOD^ ChasingRapture (Concept 3) destroyed 🎮 channdro (KV-1E)
            KillDetailTruth("uk_concept3_ngac", "channdro", "ussr_kv_1e", 801),
            # 15:04 ^UAOD^ ChasingRapture (⊙M44) shot down 🎮 channdro (★P-47D)
            KillDetailTruth("uk_m44", "channdro", "p-47d_ussr", 904),
        ],
        death_details=[
            # 2:51 =TROY= Лейтенант Ебонов (T14) destroyed ^UAOD^ ChasingRapture (Sherman VC)
            DeathDetailTruth(
                "uk_sherman_vc_firefly",
                "\u041b\u0435\u0439\u0442\u0435\u043d\u0430\u043d\u0442 \u0415\u0431\u043e\u043d\u043e\u0432",
                "us_t14",
                171,
            ),
            # 6:06 🎮 channdro (★P-47D) destroyed ^UAOD^ ChasingRapture (Churchill NA75)
            DeathDetailTruth("uk_churchill_na75", "channdro", "p-47d_ussr", 366),
            # 9:49 MGrizzB (🇨🇭fBf 109 F) destroyed ^UAOD^ ChasingRapture (Crusader AA Mk II)
            DeathDetailTruth("uk_crusader_aa_mk_2", "MGrizzB", "bf-109f-4_hungary", 589),
            # 12:12 🎮 channdro (KV-1E) destroyed ^UAOD^ ChasingRapture (Crusader AA Mk II)
            DeathDetailTruth("uk_crusader_aa_mk_2", "channdro", "ussr_kv_1e", 732),
            # 14:44 🎮 channdro (★P-47D) destroyed ^UAOD^ ChasingRapture (Concept 3)
            DeathDetailTruth("uk_concept3_ngac", "channdro", "p-47d_ussr", 884),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="USS_Liberty_K1K3",
        team=1,
        kills_ground=3,
        kills_air=0,
        deaths_total=2,
        awards=[
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "hidden_allDef_streak_1_tank",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_kill3_on_tank_destroyer",
            "hidden_kill3_streak",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_allMulty_streak",
            "fr_volunteer_cross_streak",
            "fr_volunteer_cross_streak",
            "row_air_assist",
            "tank_die_hard",
            "hidden_all_streak",
        ],
        kill_details=[
            # 2:39 USS_Liberty_K1K3 (Pvkv m/43 (1946)) destroyed 🎮 DARKLORD574699 (M24)
            KillDetailTruth("sw_pvkv_m43_1946", "DARKLORD574699", "us_m24_chaffee", 159),
            # 4:07 USS_Liberty_K1K3 (Pvkv m/43 (1946)) destroyed =TDGL= Pro_Gamer_20000 (SU-76M)
            KillDetailTruth("sw_pvkv_m43_1946", "Pro_Gamer_20000", "ussr_su_76m_1943", 247),
            # 4:25 USS_Liberty_K1K3 (Pvkv m/43 (1946)) destroyed StealthCookie (M55)
            KillDetailTruth("sw_pvkv_m43_1946", "StealthCookie", "us_m55", 265),
        ],
        death_details=[
            # 3:19 🎮 Darkcart 8430 (M24) destroyed USS_Liberty_K1K3 (Pvkv m/43 (1946))
            DeathDetailTruth("sw_pvkv_m43_1946", "Darkcart 8430", "us_m24_chaffee", 199),
            # 6:44 .Rdh1.Bymemory (T-34) destroyed USS_Liberty_K1K3 (Pvkv m/43 (1946))
            DeathDetailTruth("sw_pvkv_m43_1946", "Bymemory", "ussr_t_34_1941_cast_turret", 404),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Laughing Hawk",
        team=1,
        kills_ground=2,
        kills_air=2,
        deaths_total=4,
        awards=[
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "defender_tank",
            "global_avenge_friendly",
            "global_destroy_enemy_marked_by_ally",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "fr_volunteer_cross_streak",
            "hidden_assist_streak",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "hidden_kill3_streak",
            "hidden_marks_1_aircraft",
            "defender_tank",
            "global_avenge_self",
            "hidden_global_avenge_self_stage",
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "squad_best",
            "trophy_near_punisher",
            "hidden_allNearHeroic_streak",
            "hidden_allNearHeroic_streak_air",
            "hidden_allNearHeroic_streak_tank",
        ],
        kill_details=[
            # 5:03 Laughing Hawk (⊙M4A1) destroyed =TDGL= SCHNOOKUMSPRIME (M4A1)
            KillDetailTruth("fr_m4a1_sherman", "SCHNOOKUMSPRIME", "us_m4a1_1942_sherman", 303),
            # 5:10 Laughing Hawk (⊙M4A1) destroyed =TDGL= ExtremistMagpie (KV-2)
            KillDetailTruth("fr_m4a1_sherman", "ExtremistMagpie", "ussr_kv_2_1939", 310),
            # 9:15 Laughing Hawk (VTT DCA) shot down Jandamarra (Yak-3)
            KillDetailTruth("fr_amx_vtt_dca", "Jandamarra", "yak-3", 555),
            # 10:43 Laughing Hawk (VTT DCA) shot down MGrizzB (🇨🇭fBf 109 F)
            KillDetailTruth("fr_amx_vtt_dca", "MGrizzB", "bf-109f-4_hungary", 643),
        ],
        death_details=[
            # 2:41 StealthCookie (M55) destroyed Laughing Hawk (ARL-44 (ACL-1))
            DeathDetailTruth("fr_arl_44_acl1", "StealthCookie", "us_m55", 161),
            # 7:04 MGrizzB (🇨🇭fBf 109 F) destroyed Laughing Hawk (⊙M4A1)
            DeathDetailTruth("fr_m4a1_sherman", "MGrizzB", "bf-109f-4_hungary", 424),
            # 10:05 MGrizzB (🇨🇭fBf 109 F) destroyed Laughing Hawk (VTT DCA)
            DeathDetailTruth("fr_amx_vtt_dca", "MGrizzB", "bf-109f-4_hungary", 605),
            # 13:24 .Rdh1.Bymemory (La-5) destroyed Laughing Hawk (VTT DCA)
            DeathDetailTruth("fr_amx_vtt_dca", "Bymemory", "la-5fn", 804),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Starka228",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=3,
        awards=[
            "tank_help_with_repairing",
        ],
        kill_details=[],
        death_details=[
            # 1:38 🎮 channdro (ASU-57) destroyed Starka228 (Marder III H)
            DeathDetailTruth("germ_pzkpfw_38t_Marder_III_ausf_H", "channdro", "ussr_asu_57", 98),
            # 5:16 .Rdh1.Bymemory (T-34) destroyed Starka228 (Pz.IV H)
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "Bymemory", "ussr_t_34_1941_cast_turret", 316),
            # 6:21 =TDGL= ExtremistMagpie (I-185) destroyed Starka228 (Marder III H)
            DeathDetailTruth("germ_pzkpfw_38t_Marder_III_ausf_H", "ExtremistMagpie", "i_185_m82", 381),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ExtremistMagpie",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=4,
        awards=[
            "squad_kill",
            "hidden_squad_streaks_1_stage",
            "hidden_allsquad_streak",
            "hidden_base_capturer",
            "hidden_kill1_on_fighter",
            "hidden_kill_streak",
            "squad_kill",
            "hidden_squad_streaks_2_stage",
            "global_base_capturer",
            "tank_die_hard",
            "hidden_all_streak",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
            "squad_best",
        ],
        kill_details=[
            # 6:21 =TDGL= ExtremistMagpie (I-185) destroyed Starka228 (Marder III H)
            KillDetailTruth("i_185_m82", "Starka228", "germ_pzkpfw_38t_Marder_III_ausf_H", 381),
            # 12:39 =TDGL= ExtremistMagpie (ZiS-12 (94-KM)) destroyed [Vaygr] Trember (Pz.IV F2)
            KillDetailTruth("ussr_zis_12_94KM_1945", "Trember", "germ_pzkpfw_IV_ausf_F2", 759),
        ],
        death_details=[
            # 5:10 Laughing Hawk (⊙M4A1) destroyed =TDGL= ExtremistMagpie (KV-2)
            DeathDetailTruth("ussr_kv_2_1939", "Laughing Hawk", "fr_m4a1_sherman", 310),
            # 7:04 =285AW= autumn1196 (☆M19A1) shot down =TDGL= ExtremistMagpie (I-185)
            DeathDetailTruth("i_185_m82", "autumn1196", "jp_m19", 424),
            # 10:49 =CNGDP= Late Noon (✸M4A4 (1st PTG)) destroyed =TDGL= ExtremistMagpie (SMK)
            DeathDetailTruth("ussr_smk", "Late Noon", "cn_m4a4_sherman_1st_ptg", 649),
            # 13:51 =CNGDP= Late Noon (✸M4A4 (1st PTG)) destroyed =TDGL= ExtremistMagpie (ZiS-12 (94-KM))
            DeathDetailTruth("ussr_zis_12_94KM_1945", "Late Noon", "cn_m4a4_sherman_1st_ptg", 831),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Bymemory",
        team=2,
        kills_ground=12,
        kills_air=0,
        deaths_total=3,
        awards=[
            "tank_die_hard",
            "hidden_all_streak",
            "hidden_base_capturer",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_1_tank",
            "hidden_global_avenge_self_stage",
            "multi_kill_air",
            "hidden_allMulty_streak",
            "global_shadow_assassin",
            "hidden_kill3_on_tank",
            "hidden_kill3_streak",
            "defender_tank",
            "hidden_allDef_streak_2_tank",
            "multi_kill_air",
            "global_kills_without_death",
            "marks_5_tanks",
            "hidden_all_streak_tank",
            "defender_tank",
            "global_kills_without_death",
            "global_shadow_assassin",
            "global_kills_without_death",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_kill_without_fail",
            "global_kills_without_death",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_kill_without_fail",
            "global_kills_without_death",
            "global_shadow_assassin",
            "multi_kill_air",
            "tank_kill_without_fail",
            "global_kills_without_death",
            "global_shadow_assassin",
            "marks_10_tanks",
            "multi_kill_air",
            "hidden_kill1_on_fighter",
            "defender_ground",
            "fr_fighter_cross_streak",
            "heroic_tankman",
            "hidden_allHeroic_streak",
            "hidden_allHeroic_streak_tank",
            "hidden_allNearHeroic_streak",
            "hidden_allNearHeroic_streak_tank",
            "hidden_win_streak",
        ],
        kill_details=[
            # 5:16 .Rdh1.Bymemory (T-34) destroyed Starka228 (Pz.IV H)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "Starka228", "germ_pzkpfw_IV_ausf_H", 316),
            # 5:23 .Rdh1.Bymemory (T-34) destroyed =IMPro= ooxxaa (SAV 20.12.48)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "ooxxaa", "sw_sav_fm48", 323),
            # 6:32 .Rdh1.Bymemory (T-34) destroyed =285AW= autumn1196 (☆M42)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "autumn1196", "jp_m42_duster", 392),
            # 6:44 .Rdh1.Bymemory (T-34) destroyed USS_Liberty_K1K3 (Pvkv m/43 (1946))
            KillDetailTruth("ussr_t_34_1941_cast_turret", "USS_Liberty_K1K3", "sw_pvkv_m43_1946", 404),
            # 7:18 .Rdh1.Bymemory (T-34) destroyed ql toxic lp (Achilles)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "ql toxic lp", "uk_17_pdr_m10_achilles", 438),
            # 8:51 .Rdh1.Bymemory (T-34) destroyed Ranol (SAV 20.12.48)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "Ranol", "sw_sav_fm48", 531),
            # 9:07 .Rdh1.Bymemory (T-34) destroyed -4b0- Wiggle#6 (Sherman VC)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "Wiggle#6", "uk_sherman_vc_firefly", 547),
            # 9:19 .Rdh1.Bymemory (T-34) destroyed Undertaker1134 (Ystervark)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "Undertaker1134", "uk_ystervark_spaa", 559),
            # 9:29 .Rdh1.Bymemory (T-34) destroyed =JPs3V= _SP23 (Chi-To)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "_SP23", "jp_type_4_chi_to", 569),
            # 9:37 .Rdh1.Bymemory (T-34) destroyed =285AW= autumn1196 (☆M19A1)
            KillDetailTruth("ussr_t_34_1941_cast_turret", "autumn1196", "jp_m19", 577),
            # 13:24 .Rdh1.Bymemory (La-5) destroyed Laughing Hawk (VTT DCA)
            KillDetailTruth("la-5fn", "Laughing Hawk", "fr_amx_vtt_dca", 804),
            # 14:15 .Rdh1.Bymemory (La-5) destroyed =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.)
            KillDetailTruth("la-5fn", "IBecameTheAmmo", "germ_sdkfz_9_flak37", 855),
        ],
        death_details=[
            # 2:21 =IMPro= ooxxaa (SAV 20.12.48) destroyed .Rdh1.Bymemory (T-34)
            DeathDetailTruth("ussr_t_34_1941_cast_turret", "ooxxaa", "sw_sav_fm48", 141),
            # 12:20 =CNGDP= Late Noon (✸M4A4 (1st PTG)) destroyed .Rdh1.Bymemory (T-34)
            DeathDetailTruth("ussr_t_34_1941_cast_turret", "Late Noon", "cn_m4a4_sherman_1st_ptg", 740),
            # 15:06 Ranol (Pbv 301) shot down .Rdh1.Bymemory (La-5)
            DeathDetailTruth("la-5fn", "Ranol", "sw_pbv_301", 906),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="ooxxaa",
        team=1,
        kills_ground=3,
        kills_air=0,
        deaths_total=1,
        awards=[
            "hidden_base_capturer",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "global_destroy_enemy_marked_by_ally",
            "global_shadow_assassin",
            "hidden_kill3_on_tank_destroyer",
            "hidden_kill3_streak",
            "multi_kill_air",
            "tank_kill_without_fail",
            "hidden_allMulty_streak",
        ],
        kill_details=[
            # 2:21 =IMPro= ooxxaa (SAV 20.12.48) destroyed .Rdh1.Bymemory (T-34)
            KillDetailTruth("sw_sav_fm48", "Bymemory", "ussr_t_34_1941_cast_turret", 141),
            # 3:45 =IMPro= ooxxaa (SAV 20.12.48) destroyed 🎮 LMEESH35 (M4)
            KillDetailTruth("sw_sav_fm48", "LMEESH35", "us_m4_sherman", 225),
            # 3:51 =IMPro= ooxxaa (SAV 20.12.48) destroyed 🎮 DARKLORD574699 (M4A3 (105))
            KillDetailTruth("sw_sav_fm48", "DARKLORD574699", "us_m4a3_105_sherman", 231),
        ],
        death_details=[
            # 5:23 .Rdh1.Bymemory (T-34) destroyed =IMPro= ooxxaa (SAV 20.12.48)
            DeathDetailTruth("sw_sav_fm48", "Bymemory", "ussr_t_34_1941_cast_turret", 323),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Undertaker1134",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=3,
        awards=[
            "tank_help_with_repairing",
            "fr_volunteer_cross_streak",
            "hidden_assist_streak",
        ],
        kill_details=[],
        death_details=[
            # 6:06 🎮 channdro (★P-47D) destroyed Undertaker1134 (Crusader III)
            DeathDetailTruth("uk_crusader_mk_3", "channdro", "p-47d_ussr", 366),
            # 9:19 .Rdh1.Bymemory (T-34) destroyed Undertaker1134 (Ystervark)
            DeathDetailTruth("uk_ystervark_spaa", "Bymemory", "ussr_t_34_1941_cast_turret", 559),
            # 10:41 Undertaker1134 (Mosquito FB) has crashed.
            DeathDetailTruth("mosquito_fb_mk6", time_seconds=641),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="DARKLORD574699",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=[
            "hidden_win_streak",
        ],
        kill_details=[],
        death_details=[
            # 2:39 USS_Liberty_K1K3 (Pvkv m/43 (1946)) destroyed 🎮 DARKLORD574699 (M24)
            DeathDetailTruth("us_m24_chaffee", "USS_Liberty_K1K3", "sw_pvkv_m43_1946", 159),
            # 3:51 =IMPro= ooxxaa (SAV 20.12.48) destroyed 🎮 DARKLORD574699 (M4A3 (105))
            DeathDetailTruth("us_m4a3_105_sherman", "ooxxaa", "sw_sav_fm48", 231),
            # 5:04 ql toxic lp (Sherman VC) destroyed 🎮 DARKLORD574699 (M16)
            DeathDetailTruth("us_halftrack_m16", "ql toxic lp", "uk_sherman_vc_firefly", 304),
            # 7:39 Ranol (SAV 20.12.48) destroyed 🎮 DARKLORD574699 (M16)
            DeathDetailTruth("us_halftrack_m16", "Ranol", "sw_sav_fm48", 459),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="i_Scorched",
        team=1,
        kills_ground=1,
        kills_air=0,
        deaths_total=4,
        awards=[
            "defender_tank",
            "global_avenge_friendly",
            "global_avenge_self",
            "hidden_allDef_streak_1_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "marks_killed_plane_10_ranks_higher",
            "hidden_all_streak",
        ],
        kill_details=[],
        death_details=[
            # 2:24 =TROY= Лейтенант Ебонов (T14) destroyed i_Scorched (Marder III H)
            DeathDetailTruth(
                "germ_pzkpfw_38t_Marder_III_ausf_H",
                "\u041b\u0435\u0439\u0442\u0435\u043d\u0430\u043d\u0442 \u0415\u0431\u043e\u043d\u043e\u0432",
                "us_t14",
                144,
            ),
            # 4:45 MGrizzB (⊙M24) destroyed i_Scorched (Pz.IV H)
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "MGrizzB", "it_m24_chaffee", 285),
            # 7:12 🎮 Darkcart 8430 (M4A2) destroyed i_Scorched (Pz.III M)
            DeathDetailTruth("germ_pzkpfw_III_ausf_M", "Darkcart 8430", "us_m4a2_sherman", 432),
            # 8:58 MGrizzB (🇨🇭fBf 109 F) destroyed i_Scorched (Sd.Kfz.251/21)
            DeathDetailTruth("germ_sdkfz_251_21", "MGrizzB", "bf-109f-4_hungary", 538),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="C DESTROYER26",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=5,
        awards=[
            "hidden_kill1_on_tank_destroyer",
            "hidden_kill_streak",
            "tank_die_hard",
            "hidden_all_streak",
            "defender_tank",
            "global_avenge_self",
            "hidden_allDef_streak_1_tank",
            "hidden_global_avenge_self_stage",
            "hidden_kill1_on_tank",
            "fr_volunteer_cross_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            # 4:03 =Vizzy= 🎮 C DESTROYER26 (M55) destroyed -4b0- Wiggle#6 (Churchill VII)
            KillDetailTruth("us_m55", "Wiggle#6", "uk_a_22f_mk_7_churchill_1944", 243),
            # 8:28 =Vizzy= 🎮 C DESTROYER26 (M4A2) destroyed =CNGDP= Late Noon (✸M24)
            KillDetailTruth("us_m4a2_sherman", "Late Noon", "cn_m24_chaffee", 508),
        ],
        death_details=[
            # 4:38 [Vaygr] Trember (Pz.IV H) destroyed =Vizzy= 🎮 C DESTROYER26 (M55)
            DeathDetailTruth("us_m55", "Trember", "germ_pzkpfw_IV_ausf_H", 278),
            # 6:18 =CNGDP= Late Noon (✸M24) destroyed =Vizzy= 🎮 C DESTROYER26 (M4A2)
            DeathDetailTruth("us_m4a2_sherman", "Late Noon", "cn_m24_chaffee", 378),
            # 9:44 [Vaygr] Trember (Pz.IV H) destroyed =Vizzy= 🎮 C DESTROYER26 (M4A2)
            DeathDetailTruth("us_m4a2_sherman", "Trember", "germ_pzkpfw_IV_ausf_H", 584),
            # 11:13 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed =Vizzy= 🎮 C DESTROYER26 (M55)
            DeathDetailTruth("us_m55", "IBecameTheAmmo", "germ_sdkfz_9_flak37", 673),
            # 12:49 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed =Vizzy= 🎮 C DESTROYER26 (T77E1)
            DeathDetailTruth("us_t77e1", "IBecameTheAmmo", "germ_sdkfz_9_flak37", 769),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Darkcart 8430",
        team=2,
        kills_ground=2,
        kills_air=0,
        deaths_total=4,
        awards=[
            "defender_tank",
            "global_destroy_enemy_marked_by_ally",
            "hidden_allDef_streak_1_tank",
            "hidden_kill1_on_tank",
            "hidden_kill_streak",
            "global_base_defender",
            "tank_die_hard",
            "hidden_all_streak",
            "hidden_win_streak",
        ],
        kill_details=[
            # 3:19 🎮 Darkcart 8430 (M24) destroyed USS_Liberty_K1K3 (Pvkv m/43 (1946))
            KillDetailTruth("us_m24_chaffee", "USS_Liberty_K1K3", "sw_pvkv_m43_1946", 199),
            # 7:12 🎮 Darkcart 8430 (M4A2) destroyed i_Scorched (Pz.III M)
            KillDetailTruth("us_m4a2_sherman", "i_Scorched", "germ_pzkpfw_III_ausf_M", 432),
        ],
        death_details=[
            # 4:08 =JPs3V= _SP23 (☆M24) destroyed 🎮 Darkcart 8430 (M24)
            DeathDetailTruth("us_m24_chaffee", "_SP23", "jp_m24_chaffee", 248),
            # 7:16 Ranol (SAV 20.12.48) destroyed 🎮 Darkcart 8430 (M4A2)
            DeathDetailTruth("us_m4a2_sherman", "Ranol", "sw_sav_fm48", 436),
            # 11:26 Ranol (Pvkv II) destroyed 🎮 Darkcart 8430 (M10)
            DeathDetailTruth("us_m10", "Ranol", "sw_pvkv_II", 686),
            # 13:27 =KPOHA= IBecameTheAmmo (8,8 cm Flak 37 Sfl.) destroyed 🎮 Darkcart 8430 (M10)
            DeathDetailTruth("us_m10", "IBecameTheAmmo", "germ_sdkfz_9_flak37", 807),
        ],
        is_author=False,
    ),
    PlayerTruth(
        username="Stampedinbuny420",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=[],
        kill_details=[],
        death_details=[
            # 2:30 MGrizzB (⊙M24) destroyed 🎮 Stampedinbuny420 (Pz.IV H)
            DeathDetailTruth("germ_pzkpfw_IV_ausf_H", "MGrizzB", "it_m24_chaffee", 150),
            # 6:21 ZaddyLongStyle (M24) destroyed 🎮 Stampedinbuny420 (StuG III G)
            DeathDetailTruth("germ_stug_III_ausf_G", "ZaddyLongStyle", "us_m24_chaffee", 381),
        ],
        is_author=False,
    ),
]

# ---------------------------------------------------------------------------
# Parsed-replay fixture
# ---------------------------------------------------------------------------

WRPL_PATH = Path(__file__).parent / "#2026.03.06 01.16.49.wrpl"


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
        assert replay["session_id"] == "63ef86a001440d4"

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
