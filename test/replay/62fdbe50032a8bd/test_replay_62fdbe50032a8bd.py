"""
Regression test for parsed replay session 62fdbe50032a8bd.

Sources:
  - Raw replay:  2026.02.22 14.49.18.wrpl
  - Battle log:  battle_log_62fdbe50032a8bd.txt

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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.common.factories import ServiceFactory

# ---------------------------------------------------------------------------
# Source-of-truth dataclasses
# ---------------------------------------------------------------------------


TIMESTAMP_TOLERANCE_S = 5  # ±seconds when matching time_utc against battle-log timestamps


@dataclass
class KillDetailTruth:
    """A kill that must be matchable in the player's kills.vehicles list."""

    killer_vehicle: str
    victim_username: str | None = None
    victim_vehicle: str | None = None
    # Elapsed seconds from battle start, derived from the battle log timestamp.
    # When the parsed record also carries time_utc, matching is constrained to
    # ±TIMESTAMP_TOLERANCE_S seconds.
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


# ---------------------------------------------------------------------------
# Source-of-truth player roster  (populated one player at a time below)
# ---------------------------------------------------------------------------

PLAYERS: list[PlayerTruth] = [
    # --- Team 1 ---
    PlayerTruth(
        "xK1NGSH0TZx",
        team=1,
        kills_ground=1,
        kills_air=0,
        deaths_total=2,
        awards=["hidden_win_streak", "hidden_kill_streak", "hidden_kill1_on_tank_destroyer"],
        kill_details=[
            # 5:09 xK1NGSHOTZx (SAV 20.12.48) destroyed FAN_Falcon (M24)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="FAN_Falcon", victim_vehicle="us_m24_chaffee", time_seconds=309
            ),
        ],
        death_details=[
            # 6:43 Toxic85828 (T-34) destroyed xK1NGSHOTZx (Sherman III/IV)
            DeathDetailTruth(
                "sw_sherman_3_4", killer_username="Toxic85828", killer_vehicle="ussr_t_34_1942", time_seconds=403
            ),
        ],
    ),
    PlayerTruth(
        "Zonney0007",
        team=1,
        kills_ground=6,
        kills_air=0,
        deaths_total=6,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "global_avenge_friendly",
            "marks_killed_plane_10_ranks_higher",
            "marks_5_tanks",
        ],
        kill_details=[
            # 3:16 Zonney0007 (Pz.IV J) destroyed marcosilvavil45 (M10)
            KillDetailTruth(
                "germ_pzkpfw_IV_ausf_J", victim_username="marcosilvavil45", victim_vehicle="us_m10", time_seconds=196
            ),
            # 6:50 Zonney0007 (Pz.IV H) destroyed Sophia 87208673 (M24)
            KillDetailTruth(
                "germ_pzkpfw_IV_ausf_H",
                victim_username="Sophia 87208673",
                victim_vehicle="us_m24_chaffee",
                time_seconds=410,
            ),
            # 7:05 Zonney0007 (Pz.IV H) destroyed _06254039349256 (T-34-57)
            KillDetailTruth(
                "germ_pzkpfw_IV_ausf_H",
                victim_username="_06254039349256",
                victim_vehicle="ussr_t_34_1941_57",
                time_seconds=425,
            ),
            # 11:17 Zonney0007 (Pz.IV H) destroyed Perjuro (T-34-57)
            KillDetailTruth(
                "germ_pzkpfw_IV_ausf_H", victim_username="Perjuro", victim_vehicle="ussr_t_34_57_1943", time_seconds=677
            ),
            # 12:27 Zonney0007 (Pz.IV H) destroyed Yogui78 (M10)
            KillDetailTruth(
                "germ_pzkpfw_IV_ausf_H", victim_username="Yogui78", victim_vehicle="us_m10", time_seconds=747
            ),
            # 16:59 Zonney0007 (Marder III H) destroyed marcosilvavil45 (T77E1)
            KillDetailTruth(
                "germ_pzkpfw_38t_Marder_III_ausf_H",
                victim_username="marcosilvavil45",
                victim_vehicle="us_t77e1",
                time_seconds=1019,
            ),
        ],
        death_details=[
            # 2:10 Perjuro (KV-1) destroyed Zonney0007 (Sd.Kfz.234/2)
            DeathDetailTruth(
                "germ_sdkfz_234_2", killer_username="Perjuro", killer_vehicle="ussr_kv_1_zis_5", time_seconds=130
            ),
            # 6:19 Toxic85828 (T-34) destroyed Zonney0007 (Pz.IV J)
            DeathDetailTruth(
                "germ_pzkpfw_IV_ausf_J", killer_username="Toxic85828", killer_vehicle="ussr_t_34_1942", time_seconds=379
            ),
            # 12:48 No-X1m- (M4) destroyed Zonney0007 (Pz.IV H)
            DeathDetailTruth(
                "germ_pzkpfw_IV_ausf_H", killer_username="No-X1m-", killer_vehicle="us_m4_sherman", time_seconds=768
            ),
            # 14:33 Ribacio (ZiS-12) shot down Zonney0007 (Ju 87 R)
            DeathDetailTruth(
                "ju-87r-2_snake", killer_username="Ribacio", killer_vehicle="ussr_zis_12_94KM_1945", time_seconds=873
            ),
            # 17:53 Ribacio (ZiS-12) destroyed Zonney0007 (Marder III H)
            DeathDetailTruth(
                "germ_pzkpfw_38t_Marder_III_ausf_H",
                killer_username="Ribacio",
                killer_vehicle="ussr_zis_12_94KM_1945",
                time_seconds=1073,
            ),
        ],
    ),
    PlayerTruth(
        "Ranol",
        is_author=True,
        team=1,
        kills_ground=17,
        kills_air=0,
        deaths_total=6,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "global_shadow_assassin",
            "global_shadow_assassin",
            "global_shadow_assassin",
            "global_shadow_assassin",
            "global_shadow_assassin",
            "global_shadow_assassin",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "global_kills_without_death",
            "global_kills_without_death",
            "global_kills_without_death",
            "global_avenge_friendly",
            "global_avenge_friendly",
            "global_avenge_friendly",
            "global_avenge_self",
            "global_avenge_self",
            "global_base_defender",
            "global_destroy_enemy_marked_by_ally",
            "marks_killed_plane_10_ranks_higher",
            "defender_bomber",
            "heroic_tankman",
            "final_blow",
            "marks_5_tanks",
            "marks_10_tanks",
        ],
        kill_details=[
            # 3:33 Ranol (⊙T-34) destroyed kodiak par (KV-1)
            KillDetailTruth(
                "sw_t_34_1941", victim_username="kodiak par", victim_vehicle="ussr_kv_1_L_11", time_seconds=213
            ),
            # 4:03 Ranol (⊙T-34) destroyed Yogui78 (M4A1)
            KillDetailTruth(
                "sw_t_34_1941", victim_username="Yogui78", victim_vehicle="us_m4a1_1942_sherman", time_seconds=243
            ),
            # 4:27 Ranol (⊙T-34) destroyed alpha_overcoat0 (M44)
            KillDetailTruth(
                "sw_t_34_1941", victim_username="alpha_overcoat0", victim_vehicle="us_m44", time_seconds=267
            ),
            # 7:31 Ranol (SAV 20.12.48) destroyed Yogui78 (M24)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="Yogui78", victim_vehicle="us_m24_chaffee", time_seconds=451
            ),
            # 7:55 Ranol (SAV 20.12.48) destroyed Toxic85828 (T-34)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="Toxic85828", victim_vehicle="ussr_t_34_1942", time_seconds=475
            ),
            # 9:25 Ranol (SAV 20.12.48) destroyed alexEC (KV-1)
            KillDetailTruth("sw_sav_fm48", victim_username="alexEC", victim_vehicle="ussr_kv_1s", time_seconds=565),
            # 10:35 Ranol (SAV 20.12.48) destroyed Zam__ (M4A3 (105))
            KillDetailTruth(
                "sw_sav_fm48", victim_username="Zam__", victim_vehicle="us_m4a3_105_sherman", time_seconds=635
            ),
            # 10:38 Ranol (SAV 20.12.48) destroyed _06254039349256 (T-34-57)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="_06254039349256", victim_vehicle="ussr_t_34_1941_57", time_seconds=638
            ),
            # 10:43 Ranol (SAV 20.12.48) destroyed FAN_Falcon (M24)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="FAN_Falcon", victim_vehicle="us_m24_chaffee", time_seconds=643
            ),
            # 12:01 Ranol (SAV 20.12.48) destroyed marcosilvavil45 (T77E1)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="marcosilvavil45", victim_vehicle="us_t77e1", time_seconds=721
            ),
            # 12:54 Ranol (SAV 20.12.48) destroyed No-X1m- (M4)
            KillDetailTruth("sw_sav_fm48", victim_username="No-X1m-", victim_vehicle="us_m4_sherman", time_seconds=774),
            # 13:12 Ranol (SAV 20.12.48) destroyed HASBU___ (M2A2)
            KillDetailTruth("sw_sav_fm48", victim_username="HASBU___", victim_vehicle="us_m2a2", time_seconds=792),
            # 20:55 Ranol (⊙Pz.IV) destroyed Toxic85828 (T-34)
            KillDetailTruth(
                "sw_pzkpfw_IV_ausf_J", victim_username="Toxic85828", victim_vehicle="ussr_t_34_1942", time_seconds=1255
            ),
            # 21:14 Ranol (⊙Pz.IV) destroyed FAN_Falcon (M4A3 (105))
            KillDetailTruth(
                "sw_pzkpfw_IV_ausf_J",
                victim_username="FAN_Falcon",
                victim_vehicle="us_m4a3_105_sherman",
                time_seconds=1274,
            ),
            # 21:21 Ranol (⊙Pz.IV) destroyed _06254039349256 (BTR-152A)
            KillDetailTruth(
                "sw_pzkpfw_IV_ausf_J",
                victim_username="_06254039349256",
                victim_vehicle="ussr_btr_152a",
                time_seconds=1281,
            ),
            # 22:47 Ranol (⊙Pz.IV) destroyed Toxic85828 (T-34)
            KillDetailTruth(
                "sw_pzkpfw_IV_ausf_J",
                victim_username="Toxic85828",
                victim_vehicle="ussr_t_34_1941_l_11",
                time_seconds=1367,
            ),
        ],
        death_details=[
            # 1:54 Perjuro (KV-1) destroyed Ranol (M24DK)
            DeathDetailTruth(
                "sw_m24_chaffee_dk", killer_username="Perjuro", killer_vehicle="ussr_kv_1_zis_5", time_seconds=114
            ),
            # 5:32 Toxic85828 (T-34) destroyed Ranol (⊙T-34)
            DeathDetailTruth(
                "sw_t_34_1941", killer_username="Toxic85828", killer_vehicle="ussr_t_34_1942", time_seconds=332
            ),
            # 10:47 No-X1m- (M4) destroyed Ranol (SAV 20.12.48)
            DeathDetailTruth(
                "sw_sav_fm48", killer_username="No-X1m-", killer_vehicle="us_m4_sherman", time_seconds=647
            ),
            # 14:02 No-X1m- (A-36) destroyed Ranol (SAV 20.12.48)
            DeathDetailTruth("sw_sav_fm48", killer_username="No-X1m-", killer_vehicle="p-51_a-36", time_seconds=842),
            # 18:21 Perjuro (Pe-8) destroyed Ranol (Pbv 301)
            DeathDetailTruth("sw_pbv_301", killer_username="Perjuro", killer_vehicle="pe-8_m82", time_seconds=1101),
            # 19:12 No-X1m- (A-36) destroyed Ranol (Pvkv II)
            DeathDetailTruth("sw_pvkv_II", killer_username="No-X1m-", killer_vehicle="p-51_a-36", time_seconds=1152),
        ],
    ),
    PlayerTruth(
        "Siran2007YT",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=1,
        awards=["defender_tank", "tank_marked_enemy_destroyed_by_ally"],
        kill_details=[
            # 20:30 Siran2007YT (Dicker Max) destroyed marcosilvavil45 (M4A2)
            KillDetailTruth(
                "germ_pzsfl_IVa_dickermax",
                victim_username="marcosilvavil45",
                victim_vehicle="us_m4a2_sherman",
                time_seconds=1230,
            ),
            # 22:37 Siran2007YT (Dicker Max) destroyed Ribacio (KV-1)
            KillDetailTruth(
                "germ_pzsfl_IVa_dickermax", victim_username="Ribacio", victim_vehicle="ussr_kv_1s", time_seconds=1357
            ),
        ],
        death_details=[
            # 2:13 No-X1m- (M19A1) destroyed Siran2007YT (Sd.Kfz.234/2)
            DeathDetailTruth("germ_sdkfz_234_2", killer_username="No-X1m-", killer_vehicle="us_m19", time_seconds=133),
        ],
    ),
    PlayerTruth(
        "HayHay9797",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=["hidden_win_streak"],
        death_details=[
            # 7:36 Ribacio (KV-1) destroyed HayHay9797 (Sd.Kfz.251/21)
            DeathDetailTruth(
                "germ_sdkfz_251_21", killer_username="Ribacio", killer_vehicle="ussr_kv_1_L_11", time_seconds=456
            ),
            # 9:35 marcosilvavil45 (T77E1) shot down HayHay9797 (He 51 A)
            DeathDetailTruth("he51a1", killer_username="marcosilvavil45", killer_vehicle="us_t77e1", time_seconds=575),
        ],
    ),
    PlayerTruth(
        "obsidianwolf13",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=3,
        awards=["defender_tank", "tank_die_hard"],
        kill_details=[
            # 3:47 obsidianwolf13 (☆T-34) destroyed Toxic85828 (T-34)
            KillDetailTruth(
                "cn_t_34_1942", victim_username="Toxic85828", victim_vehicle="ussr_t_34_1942", time_seconds=227
            ),
            # 11:55 obsidianwolf13 (Martin 139WC) destroyed Ribacio (BTR-152A)
            KillDetailTruth(
                "martin_139wc", victim_username="Ribacio", victim_vehicle="ussr_btr_152a", time_seconds=715
            ),
        ],
        death_details=[
            # 4:27 Perjuro (KV-1) destroyed obsidianwolf13 (☆T-34)
            DeathDetailTruth(
                "cn_t_34_1942", killer_username="Perjuro", killer_vehicle="ussr_kv_1_zis_5", time_seconds=267
            ),
            # 12:07 marcosilvavil45 (T77E1) shot down obsidianwolf13 (Martin 139WC)
            DeathDetailTruth(
                "martin_139wc", killer_username="marcosilvavil45", killer_vehicle="us_t77e1", time_seconds=727
            ),
            # 15:06 _06254039349256 (T-34) destroyed obsidianwolf13 (☆M24)
            DeathDetailTruth(
                "cn_m24_chaffee", killer_username="_06254039349256", killer_vehicle="ussr_t_34_1942", time_seconds=906
            ),
        ],
    ),
    PlayerTruth(
        "Pawin_Krittayamo",
        team=1,
        kills_ground=2,
        kills_air=1,
        deaths_total=6,
        awards=["defender_tank", "global_avenge_friendly", "global_avenge_self"],
        kill_details=[
            # 4:09 Pawin_Krittayamo (SARC MkVI (6pdr)) destroyed Ribacio (SU-152)
            KillDetailTruth(
                "uk_marmon_herrington_mk_6_6pdr",
                victim_username="Ribacio",
                victim_vehicle="ussr_su_152",
                time_seconds=249,
            ),
            # 5:56 Pawin_Krittayamo (Cromwell V (RP-3)) destroyed No-X1m- (M4A2)
            KillDetailTruth(
                "uk_a27m_cromwell_5_rp3", victim_username="No-X1m-", victim_vehicle="us_m4a2_sherman", time_seconds=356
            ),
            # 8:40 Pawin_Krittayamo (⊙Hellcat) shot down marcosilvavil45 (P-38E)
            KillDetailTruth(
                "hellcat_fmk1", victim_username="marcosilvavil45", victim_vehicle="p-38e", time_seconds=520
            ),
        ],
        death_details=[
            # 2:40 marcosilvavil45 (M10) destroyed Pawin_Krittayamo (SARC MkVI (6pdr))
            DeathDetailTruth(
                "uk_marmon_herrington_mk_6_6pdr",
                killer_username="marcosilvavil45",
                killer_vehicle="us_m10",
                time_seconds=160,
            ),
            # 4:27 No-X1m- (M4A2) destroyed Pawin_Krittayamo (SARC MkVI (6pdr))
            DeathDetailTruth(
                "uk_marmon_herrington_mk_6_6pdr",
                killer_username="No-X1m-",
                killer_vehicle="us_m4a2_sherman",
                time_seconds=267,
            ),
            # 7:27 FAN_Falcon (M24) destroyed Pawin_Krittayamo (Cromwell V (RP-3))
            DeathDetailTruth(
                "uk_a27m_cromwell_5_rp3",
                killer_username="FAN_Falcon",
                killer_vehicle="us_m24_chaffee",
                time_seconds=447,
            ),
            # 9:14 HASBU___ (M2A2) shot down Pawin_Krittayamo (⊙Hellcat)
            DeathDetailTruth("hellcat_fmk1", killer_username="HASBU___", killer_vehicle="us_m2a2", time_seconds=554),
            # 10:42 FAN_Falcon (M24) destroyed Pawin_Krittayamo (Cromwell V)
            DeathDetailTruth(
                "uk_a27m_cromwell_5", killer_username="FAN_Falcon", killer_vehicle="us_m24_chaffee", time_seconds=642
            ),
            # 12:14 No-X1m- (M4) destroyed Pawin_Krittayamo (Crusader AA Mk I)
            DeathDetailTruth(
                "uk_crusader_aa_mk_1", killer_username="No-X1m-", killer_vehicle="us_m4_sherman", time_seconds=734
            ),
        ],
    ),
    PlayerTruth(
        "Metarou",
        team=1,
        kills_ground=6,
        kills_air=2,
        deaths_total=5,
        awards=[
            "defender_tank",
            "defender_tank",
            "global_shadow_assassin",
            "global_shadow_assassin",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "global_avenge_self",
            "global_kills_without_death",
            "global_destroy_enemy_marked_by_ally",
            "marks_5_tanks",
        ],
        kill_details=[
            # 2:56 Metarou (SAV 20.12.48) destroyed StubblyStew310 (M4)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="StubblyStew310", victim_vehicle="us_m4_sherman", time_seconds=176
            ),
            # 5:09 Metarou (SAV 20.12.48) destroyed StubblyStew310 (M4A1)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="StubblyStew310", victim_vehicle="us_m4a1_1942_sherman", time_seconds=309
            ),
            # 6:25 Metarou (SAV 20.12.48) destroyed StubblyStew310 (M3)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="StubblyStew310", victim_vehicle="us_m3_lee", time_seconds=385
            ),
            # 8:31 Metarou (SAV 20.12.48) destroyed Ribacio (KV-1)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="Ribacio", victim_vehicle="ussr_kv_1_L_11", time_seconds=511
            ),
            # 10:47 Metarou (SAV 20.12.48) destroyed Ribacio (T-34)
            KillDetailTruth(
                "sw_sav_fm48", victim_username="Ribacio", victim_vehicle="ussr_t_34_1942", time_seconds=647
            ),
            # 17:39 Metarou (⊙T-34) destroyed _06254039349256 (T-34)
            KillDetailTruth(
                "sw_t_34_1941", victim_username="_06254039349256", victim_vehicle="ussr_t_34_1942", time_seconds=1059
            ),
            # 14:28 Metarou (J26) shot down Perjuro (I-185)
            KillDetailTruth(
                "p-51d-20-na_j26", victim_username="Perjuro", victim_vehicle="i_185_m71_standard", time_seconds=868
            ),
            # 22:05 Metarou (J26) shot down Perjuro (Pe-8)
            KillDetailTruth("p-51d-20-na_j26", victim_username="Perjuro", victim_vehicle="pe-8_m82", time_seconds=1325),
        ],
        death_details=[
            # 11:21 marcosilvavil45 (T77E1) destroyed Metarou (SAV 20.12.48)
            DeathDetailTruth(
                "sw_sav_fm48", killer_username="marcosilvavil45", killer_vehicle="us_t77e1", time_seconds=681
            ),
            # 12:59 Perjuro (I-185) destroyed Metarou (Ikv 103)
            DeathDetailTruth(
                "sw_ikv_103", killer_username="Perjuro", killer_vehicle="i_185_m71_standard", time_seconds=779
            ),
            # 14:46 No-X1m- (A-36) shot down Metarou (J26)
            DeathDetailTruth(
                "p-51d-20-na_j26", killer_username="No-X1m-", killer_vehicle="p-51_a-36", time_seconds=886
            ),
            # 18:21 Perjuro (Pe-8) destroyed Metarou (⊙T-34)
            DeathDetailTruth("sw_t_34_1941", killer_username="Perjuro", killer_vehicle="pe-8_m82", time_seconds=1101),
        ],
    ),
    PlayerTruth(
        "bosco3202",
        team=1,
        kills_ground=6,
        kills_air=0,
        deaths_total=2,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "global_avenge_friendly",
            "global_avenge_friendly",
            "global_avenge_self",
            "global_avenge_self",
            "global_shadow_assassin",
            "global_destroy_enemy_marked_by_ally",
            "marks_5_tanks",
        ],
        kill_details=[
            # 2:25 bosco3202 (Sturer Emil) destroyed No-X1m- (M19A1)
            KillDetailTruth(
                "germ_pzsflk40_sturer_emil", victim_username="No-X1m-", victim_vehicle="us_m19", time_seconds=145
            ),
            # 3:03 bosco3202 (Sturer Emil) destroyed alexEC (KV-2)
            KillDetailTruth(
                "germ_pzsflk40_sturer_emil", victim_username="alexEC", victim_vehicle="ussr_kv_2_1939", time_seconds=183
            ),
            # 5:22 bosco3202 (Sturer Emil) destroyed HASBU___ (M4A1)
            KillDetailTruth(
                "germ_pzsflk40_sturer_emil",
                victim_username="HASBU___",
                victim_vehicle="us_m4a1_1942_sherman",
                time_seconds=322,
            ),
            # 13:38 bosco3202 (Sturer Emil) destroyed marcosilvavil45 (M10)
            KillDetailTruth(
                "germ_pzsflk40_sturer_emil",
                victim_username="marcosilvavil45",
                victim_vehicle="us_m10",
                time_seconds=818,
            ),
            # 16:48 bosco3202 (Fw 190 A) destroyed Perjuro (BTR-152D)
            KillDetailTruth(
                "fw-190a-5_u2", victim_username="Perjuro", victim_vehicle="ussr_btr_152d", time_seconds=1008
            ),
            # 21:20 bosco3202 (Ostwind) destroyed Ribacio (ZiS-12 (94-KM))
            KillDetailTruth(
                "germ_flakpanzer_IV_Ostwind",
                victim_username="Ribacio",
                victim_vehicle="ussr_zis_12_94KM_1945",
                time_seconds=1280,
            ),
        ],
        death_details=[
            # 15:25 Perjuro (BTR-152D) destroyed bosco3202 (Sturer Emil)
            DeathDetailTruth(
                "germ_pzsflk40_sturer_emil", killer_username="Perjuro", killer_vehicle="ussr_btr_152d", time_seconds=925
            ),
            # 16:54 Ribacio (ZiS-12 (94-KM)) shot down bosco3202 (Fw 190 A)
            DeathDetailTruth(
                "fw-190a-5_u2", killer_username="Ribacio", killer_vehicle="ussr_zis_12_94KM_1945", time_seconds=1014
            ),
        ],
    ),
    PlayerTruth(
        "oliveshellhound",
        team=1,
        kills_ground=2,
        kills_air=2,
        deaths_total=6,
        awards=["marks_killed_plane_10_ranks_higher", "global_base_defender"],
        kill_details=[
            # 7:59 oliveshellhound (⊙Hurricane) shot down No-X1m- (P-63A)
            KillDetailTruth(
                "hurricane_mk1_late_finland", victim_username="No-X1m-", victim_vehicle="p-63a-10", time_seconds=479
            ),
            # 11:23 oliveshellhound (⊙Pz.IV) destroyed Toxic85828 (T-34)
            KillDetailTruth(
                "sw_pzkpfw_IV_ausf_J", victim_username="Toxic85828", victim_vehicle="ussr_t_34_1942", time_seconds=683
            ),
            # 17:06 oliveshellhound (L-62 ANTI II) shot down FAN_Falcon (F4U-1)
            KillDetailTruth(
                "sw_l_62_anti_II", victim_username="FAN_Falcon", victim_vehicle="f4u-1d", time_seconds=1026
            ),
            # 19:39 oliveshellhound (M24DK) destroyed Yogui78 (M16)
            KillDetailTruth(
                "sw_m24_chaffee_dk", victim_username="Yogui78", victim_vehicle="us_halftrack_m16", time_seconds=1179
            ),
        ],
        death_details=[
            # 6:13 marcosilvavil45 (P-400) destroyed oliveshellhound (L-62 ANTI II)
            DeathDetailTruth(
                "sw_l_62_anti_II", killer_username="marcosilvavil45", killer_vehicle="p-400", time_seconds=373
            ),
            # 10:07 marcosilvavil45 (T77E1) shot down oliveshellhound (⊙Hurricane)
            DeathDetailTruth(
                "hurricane_mk1_late_finland",
                killer_username="marcosilvavil45",
                killer_vehicle="us_t77e1",
                time_seconds=607,
            ),
            # 12:20 Perjuro (I-185) destroyed oliveshellhound (⊙Pz.IV)
            DeathDetailTruth(
                "sw_pzkpfw_IV_ausf_J", killer_username="Perjuro", killer_vehicle="i_185_m71_standard", time_seconds=740
            ),
            # 17:09 FAN_Falcon (F4U-1) destroyed oliveshellhound (L-62 ANTI II)
            DeathDetailTruth(
                "sw_l_62_anti_II", killer_username="FAN_Falcon", killer_vehicle="f4u-1d", time_seconds=1029
            ),
            # 20:50 Toxic85828 (T-34) destroyed oliveshellhound (M24DK)
            DeathDetailTruth(
                "sw_m24_chaffee_dk",
                killer_username="Toxic85828",
                killer_vehicle="ussr_t_34_1941_l_11",
                time_seconds=1250,
            ),
        ],
    ),
    PlayerTruth(
        "PinCushion45",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=2,
        awards=["defender_tank", "global_destroy_enemy_marked_by_ally", "marks_landing_after_critical_hit"],
        kill_details=[
            # 2:13 PinCushion45 (Sd.Kfz.234/2) destroyed Zam__ (M10)
            KillDetailTruth("germ_sdkfz_234_2", victim_username="Zam__", victim_vehicle="us_m10", time_seconds=133),
            # 3:57 PinCushion45 (Sd.Kfz.234/2) destroyed FAN_Falcon (M4A1)
            KillDetailTruth(
                "germ_sdkfz_234_2",
                victim_username="FAN_Falcon",
                victim_vehicle="us_m4a1_1942_sherman",
                time_seconds=237,
            ),
        ],
        death_details=[
            # 6:23 Ribacio (KV-1) destroyed PinCushion45 (Sd.Kfz.234/2)
            DeathDetailTruth(
                "germ_sdkfz_234_2", killer_username="Ribacio", killer_vehicle="ussr_kv_1_L_11", time_seconds=383
            ),
            # 14:24 No-X1m- (A-36) shot down PinCushion45 (Ju 87 D)
            DeathDetailTruth("ju-87d-5", killer_username="No-X1m-", killer_vehicle="p-51_a-36", time_seconds=864),
        ],
    ),
    PlayerTruth(
        "Evokekirby",
        team=1,
        kills_ground=1,
        kills_air=3,
        deaths_total=3,
        awards=[
            "defender_tank",
            "global_shadow_assassin",
            "global_avenge_self",
            "row_air_assist",
            "defender_fighter",
        ],
        kill_details=[
            # 6:42 Evokekirby (CCKW 353 (M45)) shot down marcosilvavil45 (P-400)
            KillDetailTruth(
                "cn_gmc_cckw_353_m45_quad", victim_username="marcosilvavil45", victim_vehicle="p-400", time_seconds=402
            ),
            # 7:59 Evokekirby (CCKW 353 (M45)) shot down Zam__ (P-51)
            KillDetailTruth(
                "cn_gmc_cckw_353_m45_quad", victim_username="Zam__", victim_vehicle="p-51_mk1a_usaaf", time_seconds=479
            ),
            # 8:46 Evokekirby (CCKW 353 (M45)) shot down HASBU___ (P-51C)
            KillDetailTruth(
                "cn_gmc_cckw_353_m45_quad", victim_username="HASBU___", victim_vehicle="p-51c-10-nt", time_seconds=526
            ),
            # 17:46 Evokekirby (Martin 139WC) destroyed Toxic85828 (T-34)
            KillDetailTruth(
                "martin_139wc", victim_username="Toxic85828", victim_vehicle="ussr_t_34_1941_l_11", time_seconds=1066
            ),
        ],
        death_details=[
            # 5:02 HASBU___ (M4A1) destroyed Evokekirby (☆M10)
            DeathDetailTruth(
                "cn_m10", killer_username="HASBU___", killer_vehicle="us_m4a1_1942_sherman", time_seconds=302
            ),
            # 9:38 Zam__ (M4A3 (105)) destroyed Evokekirby (CCKW 353 (M45))
            DeathDetailTruth(
                "cn_gmc_cckw_353_m45_quad",
                killer_username="Zam__",
                killer_vehicle="us_m4a3_105_sherman",
                time_seconds=578,
            ),
            # 18:20 Ribacio (ZiS-12 (94-KM)) shot down Evokekirby (Martin 139WC)
            DeathDetailTruth(
                "martin_139wc", killer_username="Ribacio", killer_vehicle="ussr_zis_12_94KM_1945", time_seconds=1100
            ),
        ],
    ),
    PlayerTruth(
        "InDommWeTrust",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=1,
        awards=["tank_die_hard"],
        death_details=[
            # 8:08 Toxic85828 (T-34) destroyed InDommWeTrust (Pz.Bef.Wg.IV J)
            DeathDetailTruth(
                "germ_panzerbefelhswagen_IV_ausf_J",
                killer_username="Toxic85828",
                killer_vehicle="ussr_t_34_1941",
                time_seconds=488,
            ),
        ],
    ),
    PlayerTruth(
        "Thorkell_83",
        team=1,
        kills_ground=2,
        kills_air=0,
        deaths_total=5,
        awards=["defender_tank", "global_base_capturer"],
        kill_details=[
            # 6:16 Thorkell_83 (⊙M10) destroyed Zam__ (M24)
            KillDetailTruth("fr_m10", victim_username="Zam__", victim_vehicle="us_m24_chaffee", time_seconds=376),
            # 6:29 Thorkell_83 (⊙M10) destroyed XanDerJacK_guNna (T-34)
            KillDetailTruth(
                "fr_m10", victim_username="XanDerJacK_guNna", victim_vehicle="ussr_t_34_1941_l_11", time_seconds=389
            ),
            # 13:22 Thorkell_83 (VTT DCA) shot down _06254039349256 (Yak-7)
            KillDetailTruth(
                "fr_amx_vtt_dca", victim_username="_06254039349256", victim_vehicle="yak-7b", time_seconds=802
            ),
        ],
        death_details=[
            # 3:30 Sophia 87208673 (M24) destroyed Thorkell_83 (AMX-13 (FL11))
            DeathDetailTruth(
                "fr_amx_13_fl_11", killer_username="Sophia 87208673", killer_vehicle="us_m24_chaffee", time_seconds=210
            ),
            # 5:49 No-X1m- (M4A2) destroyed Thorkell_83 (⊙M55)
            DeathDetailTruth("fr_m55", killer_username="No-X1m-", killer_vehicle="us_m4a2_sherman", time_seconds=349),
            # 6:33 _06254039349256 (T-34-57) destroyed Thorkell_83 (⊙M10)
            DeathDetailTruth(
                "fr_m10", killer_username="_06254039349256", killer_vehicle="ussr_t_34_1941_57", time_seconds=393
            ),
            # 9:17 _06254039349256 (T-34-57) destroyed Thorkell_83 (ARL-44 (ACL-1))
            DeathDetailTruth(
                "fr_arl_44_acl1",
                killer_username="_06254039349256",
                killer_vehicle="ussr_t_34_1941_57",
                time_seconds=557,
            ),
            # 12:27 Zonney0007 (Pz.IV H) destroyed Thorkell_83 (⊙M55)
            DeathDetailTruth(
                "fr_m55", killer_username="Zonney0007", killer_vehicle="germ_pzkpfw_IV_ausf_H", time_seconds=747
            ),
            # 12:38 Perjuro (I-185) destroyed Thorkell_83 (VTT DCA)
            DeathDetailTruth(
                "fr_amx_vtt_dca", killer_username="Perjuro", killer_vehicle="i_185_m71_standard", time_seconds=758
            ),
        ],
    ),
    PlayerTruth(
        "b1 Val",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=["tank_die_hard"],
        death_details=[
            # 3:30 Perjuro (KV-1) destroyed b1 Val (AMX-13 (FL11))
            DeathDetailTruth(
                "fr_amx_13_fl_11", killer_username="Perjuro", killer_vehicle="ussr_kv_1_zis_5", time_seconds=210
            ),
            # 5:04 Sophia 87208673 (M24) destroyed b1 Val (ARL-44 (ACL-1))
            DeathDetailTruth(
                "fr_arl_44_acl1", killer_username="Sophia 87208673", killer_vehicle="us_m24_chaffee", time_seconds=304
            ),
            # 6:01 XanDerJacK_guNna (T-34) destroyed b1 Val (⊙M10)
            DeathDetailTruth(
                "fr_m10", killer_username="XanDerJacK_guNna", killer_vehicle="ussr_t_34_1941_l_11", time_seconds=361
            ),
            # 6:42 Sophia 87208673 (M24) destroyed b1 Val (CCKW 353 AA)
            DeathDetailTruth(
                "fr_cckw_353_bofors",
                killer_username="Sophia 87208673",
                killer_vehicle="us_m24_chaffee",
                time_seconds=402,
            ),
        ],
    ),
    PlayerTruth(
        "KlutzyObject6",
        team=1,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        awards=["heroic_wingman"],
        death_details=[
            # 4:38 No-X1m- (M4A2) destroyed KlutzyObject6 (StuG III G)
            DeathDetailTruth(
                "germ_stug_III_ausf_G", killer_username="No-X1m-", killer_vehicle="us_m4a2_sherman", time_seconds=278
            ),
            # 11:14 Perjuro (T-34-57) destroyed KlutzyObject6 (StuH 42 G)
            DeathDetailTruth(
                "germ_stuh_III_ausf_G", killer_username="Perjuro", killer_vehicle="ussr_t_34_1941_57", time_seconds=674
            ),
            # 19:33 Toxic85828 (T-34) destroyed KlutzyObject6 (Sd.Kfz.234/2)
            DeathDetailTruth(
                "germ_sdkfz_234_2",
                killer_username="Toxic85828",
                killer_vehicle="ussr_t_34_1941_l_11",
                time_seconds=1173,
            ),
            # 20:55 No-X1m- (A-36) shot down KlutzyObject6 (He 111 H)
            DeathDetailTruth("he-111h-6", killer_username="No-X1m-", killer_vehicle="p-51_a-36", time_seconds=1255),
        ],
    ),
    # --- Team 2 ---
    PlayerTruth(
        "_06254039349256",
        team=2,
        kills_ground=3,
        kills_air=0,
        deaths_total=5,
        awards=[
            "defender_tank",
            "defender_tank",
            "global_avenge_friendly",
            "global_base_defender",
            "global_destroy_enemy_marked_by_ally",
        ],
        kill_details=[
            # 6:33 _06254039349256 (T-34-57) destroyed Thorkell_83 (⊙M10)
            KillDetailTruth(
                "ussr_t_34_1941_57", victim_username="Thorkell_83", victim_vehicle="fr_m10", time_seconds=393
            ),
            # 9:17 _06254039349256 (T-34-57) destroyed Thorkell_83 (ARL-44 (ACL-1))
            KillDetailTruth(
                "ussr_t_34_1941_57", victim_username="Thorkell_83", victim_vehicle="fr_arl_44_acl1", time_seconds=557
            ),
            # 15:06 _06254039349256 (T-34) destroyed obsidianwolf13 (☆M24)
            KillDetailTruth(
                "ussr_t_34_1942", victim_username="obsidianwolf13", victim_vehicle="cn_m24_chaffee", time_seconds=906
            ),
        ],
        death_details=[
            # 7:05 Zonney0007 (Pz.IV H) destroyed _06254039349256 (T-34-57)
            DeathDetailTruth(
                "ussr_t_34_1941_57",
                killer_username="Zonney0007",
                killer_vehicle="germ_pzkpfw_IV_ausf_H",
                time_seconds=425,
            ),
            # 10:38 Ranol (SAV 20.12.48) destroyed _06254039349256 (T-34-57)
            DeathDetailTruth(
                "ussr_t_34_1941_57", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=638
            ),
            # 13:22 Thorkell_83 (VTT DCA) shot down _06254039349256 (Yak-7)
            DeathDetailTruth(
                "yak-7b", killer_username="Thorkell_83", killer_vehicle="fr_amx_vtt_dca", time_seconds=802
            ),
            # 17:39 Metarou (⊙T-34) destroyed _06254039349256 (T-34)
            DeathDetailTruth(
                "ussr_t_34_1942", killer_username="Metarou", killer_vehicle="sw_t_34_1941", time_seconds=1059
            ),
            # 21:21 Ranol (⊙Pz.IV) destroyed _06254039349256 (BTR-152A)
            DeathDetailTruth(
                "ussr_btr_152a", killer_username="Ranol", killer_vehicle="sw_pzkpfw_IV_ausf_J", time_seconds=1281
            ),
        ],
    ),
    PlayerTruth(
        "No-X1m-",
        team=2,
        kills_ground=9,
        kills_air=3,
        deaths_total=4,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "global_avenge_friendly",
            "global_avenge_friendly",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "global_avenge_self",
            "global_kills_without_death",
            "global_shadow_assassin",
            "marks_killed_plane_10_ranks_higher",
            "marks_5_tanks",
        ],
        kill_details=[
            # 2:13 No-X1m- (M19A1) destroyed Siran2007YT (Sd.Kfz.234/2)
            KillDetailTruth(
                "us_m19", victim_username="Siran2007YT", victim_vehicle="germ_sdkfz_234_2", time_seconds=133
            ),
            # 4:27 No-X1m- (M4A2) destroyed Pawin_Krittayamo (SARC MkVI (6pdr))
            KillDetailTruth(
                "us_m4a2_sherman",
                victim_username="Pawin_Krittayamo",
                victim_vehicle="uk_marmon_herrington_mk_6_6pdr",
                time_seconds=267,
            ),
            # 4:38 No-X1m- (M4A2) destroyed KlutzyObject6 (StuG III G)
            KillDetailTruth(
                "us_m4a2_sherman",
                victim_username="KlutzyObject6",
                victim_vehicle="germ_stug_III_ausf_G",
                time_seconds=278,
            ),
            # 5:49 No-X1m- (M4A2) destroyed Thorkell_83 (⊙M55)
            KillDetailTruth(
                "us_m4a2_sherman", victim_username="Thorkell_83", victim_vehicle="fr_m55", time_seconds=349
            ),
            # 10:47 No-X1m- (M4) destroyed Ranol (SAV 20.12.48)
            KillDetailTruth("us_m4_sherman", victim_username="Ranol", victim_vehicle="sw_sav_fm48", time_seconds=647),
            # 12:14 No-X1m- (M4) destroyed Pawin_Krittayamo (Crusader AA Mk I)
            KillDetailTruth(
                "us_m4_sherman",
                victim_username="Pawin_Krittayamo",
                victim_vehicle="uk_crusader_aa_mk_1",
                time_seconds=734,
            ),
            # 12:48 No-X1m- (M4) destroyed Zonney0007 (Pz.IV H)
            KillDetailTruth(
                "us_m4_sherman", victim_username="Zonney0007", victim_vehicle="germ_pzkpfw_IV_ausf_H", time_seconds=768
            ),
            # 14:02 No-X1m- (A-36) destroyed Ranol (SAV 20.12.48)
            KillDetailTruth("p-51_a-36", victim_username="Ranol", victim_vehicle="sw_sav_fm48", time_seconds=842),
            # 14:24 No-X1m- (A-36) shot down PinCushion45 (Ju 87 D)
            KillDetailTruth("p-51_a-36", victim_username="PinCushion45", victim_vehicle="ju-87d-5", time_seconds=864),
            # 14:46 No-X1m- (A-36) shot down Metarou (J26)
            KillDetailTruth("p-51_a-36", victim_username="Metarou", victim_vehicle="p-51d-20-na_j26", time_seconds=886),
            # 19:12 No-X1m- (A-36) destroyed Ranol (Pvkv II)
            KillDetailTruth("p-51_a-36", victim_username="Ranol", victim_vehicle="sw_pvkv_II", time_seconds=1152),
            # 20:55 No-X1m- (A-36) shot down KlutzyObject6 (He 111 H)
            KillDetailTruth(
                "p-51_a-36", victim_username="KlutzyObject6", victim_vehicle="he-111h-6", time_seconds=1255
            ),
        ],
        death_details=[
            # 2:25 bosco3202 (Sturer Emil) destroyed No-X1m- (M19A1)
            DeathDetailTruth(
                "us_m19", killer_username="bosco3202", killer_vehicle="germ_pzsflk40_sturer_emil", time_seconds=145
            ),
            # 5:56 Pawin_Krittayamo (Cromwell V (RP-3)) destroyed No-X1m- (M4A2)
            DeathDetailTruth(
                "us_m4a2_sherman",
                killer_username="Pawin_Krittayamo",
                killer_vehicle="uk_a27m_cromwell_5_rp3",
                time_seconds=356,
            ),
            # 7:59 oliveshellhound (⊙Hurricane) shot down No-X1m- (P-63A)
            DeathDetailTruth(
                "p-63a-10",
                killer_username="oliveshellhound",
                killer_vehicle="hurricane_mk1_late_finland",
                time_seconds=479,
            ),
            # 12:54 Ranol (SAV 20.12.48) destroyed No-X1m- (M4)
            DeathDetailTruth("us_m4_sherman", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=774),
        ],
    ),
    PlayerTruth(
        "FAN_Falcon",
        team=2,
        kills_ground=3,
        kills_air=0,
        deaths_total=5,
        awards=["defender_tank", "global_avenge_self", "global_base_capturer"],
        kill_details=[
            # 7:27 FAN_Falcon (M24) destroyed Pawin_Krittayamo (Cromwell V (RP-3))
            KillDetailTruth(
                "us_m24_chaffee",
                victim_username="Pawin_Krittayamo",
                victim_vehicle="uk_a27m_cromwell_5_rp3",
                time_seconds=447,
            ),
            # 10:42 FAN_Falcon (M24) destroyed Pawin_Krittayamo (Cromwell V)
            KillDetailTruth(
                "us_m24_chaffee",
                victim_username="Pawin_Krittayamo",
                victim_vehicle="uk_a27m_cromwell_5",
                time_seconds=642,
            ),
            # 17:09 FAN_Falcon (F4U-1) destroyed oliveshellhound (L-62 ANTI II)
            KillDetailTruth(
                "f4u-1d", victim_username="oliveshellhound", victim_vehicle="sw_l_62_anti_II", time_seconds=1029
            ),
        ],
        death_details=[
            # 3:57 PinCushion45 (Sd.Kfz.234/2) destroyed FAN_Falcon (M4A1)
            DeathDetailTruth(
                "us_m4a1_1942_sherman",
                killer_username="PinCushion45",
                killer_vehicle="germ_sdkfz_234_2",
                time_seconds=237,
            ),
            # 5:09 xK1NGSH0TZx (SAV 20.12.48) destroyed FAN_Falcon (M24)
            DeathDetailTruth(
                "us_m24_chaffee", killer_username="xK1NGSH0TZx", killer_vehicle="sw_sav_fm48", time_seconds=309
            ),
            # 10:43 Ranol (SAV 20.12.48) destroyed FAN_Falcon (M24)
            DeathDetailTruth("us_m24_chaffee", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=643),
            # 17:06 oliveshellhound (L-62 ANTI II) shot down FAN_Falcon (F4U-1)
            DeathDetailTruth(
                "f4u-1d", killer_username="oliveshellhound", killer_vehicle="sw_l_62_anti_II", time_seconds=1026
            ),
            # 21:14 Ranol (⊙Pz.IV) destroyed FAN_Falcon (M4A3 (105))
            DeathDetailTruth(
                "us_m4a3_105_sherman", killer_username="Ranol", killer_vehicle="sw_pzkpfw_IV_ausf_J", time_seconds=1274
            ),
        ],
    ),
    PlayerTruth(
        "XanDerJacK_guNna",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=1,
        awards=["tank_die_hard"],
        kill_details=[
            # 6:01 XanDerJacK_guNna (T-34) destroyed b1 Val (⊙M10)
            KillDetailTruth("ussr_t_34_1941_l_11", victim_username="b1 Val", victim_vehicle="fr_m10", time_seconds=361),
        ],
        death_details=[
            # 6:29 Thorkell_83 (⊙M10) destroyed XanDerJacK_guNna (T-34)
            DeathDetailTruth(
                "ussr_t_34_1941_l_11", killer_username="Thorkell_83", killer_vehicle="fr_m10", time_seconds=389
            ),
        ],
    ),
    PlayerTruth(
        "Zam__",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=4,
        awards=["global_avenge_self"],
        kill_details=[
            # 9:38 Zam__ (M4A3 (105)) destroyed Evokekirby (CCKW 353 (M45))
            KillDetailTruth(
                "us_m4a3_105_sherman",
                victim_username="Evokekirby",
                victim_vehicle="cn_gmc_cckw_353_m45_quad",
                time_seconds=578,
            ),
        ],
        death_details=[
            # 2:13 PinCushion45 (Sd.Kfz.234/2) destroyed Zam__ (M10)
            DeathDetailTruth(
                "us_m10", killer_username="PinCushion45", killer_vehicle="germ_sdkfz_234_2", time_seconds=133
            ),
            # 6:16 Thorkell_83 (⊙M10) destroyed Zam__ (M24)
            DeathDetailTruth(
                "us_m24_chaffee", killer_username="Thorkell_83", killer_vehicle="fr_m10", time_seconds=376
            ),
            # 7:59 Evokekirby (CCKW 353 (M45)) shot down Zam__ (P-51)
            DeathDetailTruth(
                "p-51_mk1a_usaaf",
                killer_username="Evokekirby",
                killer_vehicle="cn_gmc_cckw_353_m45_quad",
                time_seconds=479,
            ),
            # 10:35 Ranol (SAV 20.12.48) destroyed Zam__ (M4A3 (105))
            DeathDetailTruth(
                "us_m4a3_105_sherman", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=635
            ),
        ],
    ),
    PlayerTruth(
        "marcosilvavil45",
        team=2,
        kills_ground=3,
        kills_air=3,
        deaths_total=7,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_ground",
        ],
        kill_details=[
            # 2:40 marcosilvavil45 (M10) destroyed Pawin_Krittayamo (SARC MkVI (6pdr))
            KillDetailTruth(
                "us_m10",
                victim_username="Pawin_Krittayamo",
                victim_vehicle="uk_marmon_herrington_mk_6_6pdr",
                time_seconds=160,
            ),
            # 6:13 marcosilvavil45 (P-400) destroyed oliveshellhound (L-62 ANTI II)
            KillDetailTruth(
                "p-400", victim_username="oliveshellhound", victim_vehicle="sw_l_62_anti_II", time_seconds=373
            ),
            # 9:35 marcosilvavil45 (T77E1) shot down HayHay9797 (He 51 A)
            KillDetailTruth("us_t77e1", victim_username="HayHay9797", victim_vehicle="he51a1", time_seconds=575),
            # 10:07 marcosilvavil45 (T77E1) shot down oliveshellhound (⊙Hurricane)
            KillDetailTruth(
                "us_t77e1",
                victim_username="oliveshellhound",
                victim_vehicle="hurricane_mk1_late_finland",
                time_seconds=607,
            ),
            # 11:21 marcosilvavil45 (T77E1) destroyed Metarou (SAV 20.12.48)
            KillDetailTruth("us_t77e1", victim_username="Metarou", victim_vehicle="sw_sav_fm48", time_seconds=681),
            # 12:07 marcosilvavil45 (T77E1) shot down obsidianwolf13 (Martin 139WC)
            KillDetailTruth(
                "us_t77e1", victim_username="obsidianwolf13", victim_vehicle="martin_139wc", time_seconds=727
            ),
        ],
        death_details=[
            # 3:16 Zonney0007 (Pz.IV J) destroyed marcosilvavil45 (M10)
            DeathDetailTruth(
                "us_m10", killer_username="Zonney0007", killer_vehicle="germ_pzkpfw_IV_ausf_J", time_seconds=196
            ),
            # 6:42 Evokekirby (CCKW 353 (M45)) shot down marcosilvavil45 (P-400)
            DeathDetailTruth(
                "p-400", killer_username="Evokekirby", killer_vehicle="cn_gmc_cckw_353_m45_quad", time_seconds=402
            ),
            # 8:40 Pawin_Krittayamo (⊙Hellcat) shot down marcosilvavil45 (P-38E)
            DeathDetailTruth(
                "p-38e", killer_username="Pawin_Krittayamo", killer_vehicle="hellcat_fmk1", time_seconds=520
            ),
            # 12:01 Ranol (SAV 20.12.48) destroyed marcosilvavil45 (T77E1)
            DeathDetailTruth("us_t77e1", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=721),
            # 13:38 bosco3202 (Sturer Emil) destroyed marcosilvavil45 (M10)
            DeathDetailTruth(
                "us_m10", killer_username="bosco3202", killer_vehicle="germ_pzsflk40_sturer_emil", time_seconds=818
            ),
            # 16:59 Zonney0007 (Marder III H) destroyed marcosilvavil45 (T77E1)
            DeathDetailTruth(
                "us_t77e1",
                killer_username="Zonney0007",
                killer_vehicle="germ_pzkpfw_38t_Marder_III_ausf_H",
                time_seconds=1019,
            ),
            # 20:30 Siran2007YT (Dicker Max) destroyed marcosilvavil45 (M4A2)
            DeathDetailTruth(
                "us_m4a2_sherman",
                killer_username="Siran2007YT",
                killer_vehicle="germ_pzsfl_IVa_dickermax",
                time_seconds=1230,
            ),
        ],
    ),
    PlayerTruth(
        "HASBU___",
        team=2,
        kills_ground=1,
        kills_air=1,
        deaths_total=4,
        awards=["defender_tank", "defender_tank"],
        kill_details=[
            # 5:02 HASBU___ (M4A1) destroyed Evokekirby (☆M10)
            KillDetailTruth(
                "us_m4a1_1942_sherman", victim_username="Evokekirby", victim_vehicle="cn_m10", time_seconds=302
            ),
            # 9:14 HASBU___ (M2A2) shot down Pawin_Krittayamo (⊙Hellcat)
            KillDetailTruth(
                "us_m2a2", victim_username="Pawin_Krittayamo", victim_vehicle="hellcat_fmk1", time_seconds=554
            ),
        ],
        death_details=[
            # 5:22 bosco3202 (Sturer Emil) destroyed HASBU___ (M4A1)
            DeathDetailTruth(
                "us_m4a1_1942_sherman",
                killer_username="bosco3202",
                killer_vehicle="germ_pzsflk40_sturer_emil",
                time_seconds=322,
            ),
            # 8:46 Evokekirby (CCKW 353 (M45)) shot down HASBU___ (P-51C)
            DeathDetailTruth(
                "p-51c-10-nt", killer_username="Evokekirby", killer_vehicle="cn_gmc_cckw_353_m45_quad", time_seconds=526
            ),
            # 13:12 Ranol (SAV 20.12.48) destroyed HASBU___ (M2A2)
            DeathDetailTruth("us_m2a2", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=792),
            # 14:32 HASBU___ (M10) has been wrecked
            DeathDetailTruth("us_m10", time_seconds=872),
        ],
    ),
    PlayerTruth(
        "alexEC",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        awards=["tank_die_hard"],
        death_details=[
            # 3:03 bosco3202 (Sturer Emil) destroyed alexEC (KV-2)
            DeathDetailTruth(
                "ussr_kv_2_1939",
                killer_username="bosco3202",
                killer_vehicle="germ_pzsflk40_sturer_emil",
                time_seconds=183,
            ),
            # 9:25 Ranol (SAV 20.12.48) destroyed alexEC (KV-1)
            DeathDetailTruth("ussr_kv_1s", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=565),
        ],
    ),
    PlayerTruth(
        "Sophia 87208673",
        team=2,
        kills_ground=3,
        kills_air=0,
        deaths_total=1,
        awards=["defender_tank", "global_shadow_assassin", "tank_marked_enemy_destroyed_by_ally"],
        kill_details=[
            # 3:30 Sophia 87208673 (M24) destroyed Thorkell_83 (AMX-13 (FL11))
            KillDetailTruth(
                "us_m24_chaffee", victim_username="Thorkell_83", victim_vehicle="fr_amx_13_fl_11", time_seconds=210
            ),
            # 5:04 Sophia 87208673 (M24) destroyed b1 Val (ARL-44 (ACL-1))
            KillDetailTruth(
                "us_m24_chaffee", victim_username="b1 Val", victim_vehicle="fr_arl_44_acl1", time_seconds=304
            ),
            # 6:42 Sophia 87208673 (M24) destroyed b1 Val (CCKW 353 AA)
            KillDetailTruth(
                "us_m24_chaffee", victim_username="b1 Val", victim_vehicle="fr_cckw_353_bofors", time_seconds=402
            ),
        ],
        death_details=[
            # 6:50 Zonney0007 (Pz.IV H) destroyed Sophia 87208673 (M24)
            DeathDetailTruth(
                "us_m24_chaffee", killer_username="Zonney0007", killer_vehicle="germ_pzkpfw_IV_ausf_H", time_seconds=410
            ),
        ],
    ),
    PlayerTruth(
        "kodiak par",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        death_details=[
            # 3:33 Ranol (⊙T-34) destroyed kodiak par (KV-1)
            DeathDetailTruth(
                "ussr_kv_1_L_11", killer_username="Ranol", killer_vehicle="sw_t_34_1941", time_seconds=213
            ),
            # 4:48 kodiak par (Pe-3) has crashed
            DeathDetailTruth("pe-3_early", time_seconds=288),
        ],
    ),
    PlayerTruth(
        "StubblyStew310",
        team=2,
        kills_ground=1,
        kills_air=0,
        deaths_total=3,
        awards=["defender_tank"],
        kill_details=[
            # 5:09 StubblyStew310 (M4A1) destroyed xK1NGSH0TZx (SAV 20.12.48)
            KillDetailTruth(
                "us_m4a1_1942_sherman", victim_username="xK1NGSH0TZx", victim_vehicle="sw_sav_fm48", time_seconds=309
            ),
        ],
        death_details=[
            # 2:56 Metarou (SAV 20.12.48) destroyed StubblyStew310 (M4)
            DeathDetailTruth(
                "us_m4_sherman", killer_username="Metarou", killer_vehicle="sw_sav_fm48", time_seconds=176
            ),
            # 5:09 Metarou (SAV 20.12.48) destroyed StubblyStew310 (M4A1)
            DeathDetailTruth(
                "us_m4a1_1942_sherman", killer_username="Metarou", killer_vehicle="sw_sav_fm48", time_seconds=309
            ),
            # 6:25 Metarou (SAV 20.12.48) destroyed StubblyStew310 (M3)
            DeathDetailTruth("us_m3_lee", killer_username="Metarou", killer_vehicle="sw_sav_fm48", time_seconds=385),
        ],
    ),
    PlayerTruth(
        "Ribacio",
        team=2,
        kills_ground=3,
        kills_air=3,
        deaths_total=6,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "global_avenge_friendly",
            "global_avenge_friendly",
            "global_base_capturer",
            "defender_fighter",
        ],
        kill_details=[
            # 6:23 Ribacio (KV-1) destroyed PinCushion45 (Sd.Kfz.234/2)
            KillDetailTruth(
                "ussr_kv_1_L_11", victim_username="PinCushion45", victim_vehicle="germ_sdkfz_234_2", time_seconds=383
            ),
            # 7:36 Ribacio (KV-1) destroyed HayHay9797 (Sd.Kfz.251/21)
            KillDetailTruth(
                "ussr_kv_1_L_11", victim_username="HayHay9797", victim_vehicle="germ_sdkfz_251_21", time_seconds=456
            ),
            # 14:33 Ribacio (ZiS-12 (94-KM)) shot down Zonney0007 (Ju 87 R)
            KillDetailTruth(
                "ussr_zis_12_94KM_1945", victim_username="Zonney0007", victim_vehicle="ju-87r-2_snake", time_seconds=873
            ),
            # 16:54 Ribacio (ZiS-12 (94-KM)) shot down bosco3202 (Fw 190 A)
            KillDetailTruth(
                "ussr_zis_12_94KM_1945", victim_username="bosco3202", victim_vehicle="fw-190a-5_u2", time_seconds=1014
            ),
            # 17:53 Ribacio (ZiS-12 (94-KM)) destroyed Zonney0007 (Marder III H)
            KillDetailTruth(
                "ussr_zis_12_94KM_1945",
                victim_username="Zonney0007",
                victim_vehicle="germ_pzkpfw_38t_Marder_III_ausf_H",
                time_seconds=1073,
            ),
            # 18:20 Ribacio (ZiS-12 (94-KM)) shot down Evokekirby (Martin 139WC)
            KillDetailTruth(
                "ussr_zis_12_94KM_1945", victim_username="Evokekirby", victim_vehicle="martin_139wc", time_seconds=1100
            ),
        ],
        death_details=[
            # 4:09 Pawin_Krittayamo (SARC MkVI (6pdr)) destroyed Ribacio (SU-152)
            DeathDetailTruth(
                "ussr_su_152",
                killer_username="Pawin_Krittayamo",
                killer_vehicle="uk_marmon_herrington_mk_6_6pdr",
                time_seconds=249,
            ),
            # 8:31 Metarou (SAV 20.12.48) destroyed Ribacio (KV-1)
            DeathDetailTruth(
                "ussr_kv_1_L_11", killer_username="Metarou", killer_vehicle="sw_sav_fm48", time_seconds=511
            ),
            # 10:47 Metarou (SAV 20.12.48) destroyed Ribacio (T-34)
            DeathDetailTruth(
                "ussr_t_34_1942", killer_username="Metarou", killer_vehicle="sw_sav_fm48", time_seconds=647
            ),
            # 11:55 obsidianwolf13 (Martin 139WC) destroyed Ribacio (BTR-152A)
            DeathDetailTruth(
                "ussr_btr_152a", killer_username="obsidianwolf13", killer_vehicle="martin_139wc", time_seconds=715
            ),
            # 21:20 bosco3202 (Ostwind) destroyed Ribacio (ZiS-12 (94-KM))
            DeathDetailTruth(
                "ussr_zis_12_94KM_1945",
                killer_username="bosco3202",
                killer_vehicle="germ_flakpanzer_IV_Ostwind",
                time_seconds=1280,
            ),
            # 22:37 Siran2007YT (Dicker Max) destroyed Ribacio (KV-1)
            DeathDetailTruth(
                "ussr_kv_1_L_11",
                killer_username="Siran2007YT",
                killer_vehicle="germ_pzsfl_IVa_dickermax",
                time_seconds=1357,
            ),
        ],
    ),
    PlayerTruth(
        "Yogui78",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=4,
        death_details=[
            # 4:03 Ranol (⊙T-34) destroyed Yogui78 (M4A1)
            DeathDetailTruth(
                "us_m4a1_1942_sherman", killer_username="Ranol", killer_vehicle="sw_t_34_1941", time_seconds=243
            ),
            # 7:31 Ranol (SAV 20.12.48) destroyed Yogui78 (M24)
            DeathDetailTruth("us_m24_chaffee", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=451),
            # 12:27 Zonney0007 (Pz.IV H) destroyed Yogui78 (M10)
            DeathDetailTruth(
                "us_m10", killer_username="Zonney0007", killer_vehicle="germ_pzkpfw_IV_ausf_H", time_seconds=747
            ),
            # 19:39 oliveshellhound (M24DK) destroyed Yogui78 (M16)
            DeathDetailTruth(
                "us_halftrack_m16",
                killer_username="oliveshellhound",
                killer_vehicle="sw_m24_chaffee_dk",
                time_seconds=1179,
            ),
        ],
    ),
    PlayerTruth(
        "alpha_overcoat0",
        team=2,
        kills_ground=0,
        kills_air=0,
        deaths_total=2,
        death_details=[
            # 4:27 Ranol (⊙T-34) destroyed alpha_overcoat0 (M44)
            DeathDetailTruth("us_m44", killer_username="Ranol", killer_vehicle="sw_t_34_1941", time_seconds=267),
            # 6:06 alpha_overcoat0 (M4) has been wrecked
            DeathDetailTruth("us_m4_sherman", time_seconds=366),
        ],
    ),
    PlayerTruth(
        "Toxic85828",
        team=2,
        kills_ground=6,
        kills_air=0,
        deaths_total=6,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "tank_kill_without_fail",
            "tank_kill_without_fail",
            "global_base_capturer",
            "global_base_capturer",
            "heroic_wingman",
            "marks_5_tanks",
        ],
        kill_details=[
            # 5:32 Toxic85828 (T-34) destroyed Ranol (⊙T-34)
            KillDetailTruth("ussr_t_34_1942", victim_username="Ranol", victim_vehicle="sw_t_34_1941", time_seconds=332),
            # 6:19 Toxic85828 (T-34) destroyed Zonney0007 (Pz.IV J)
            KillDetailTruth(
                "ussr_t_34_1942", victim_username="Zonney0007", victim_vehicle="germ_pzkpfw_IV_ausf_J", time_seconds=379
            ),
            # 6:43 Toxic85828 (T-34) destroyed xK1NGSH0TZx (Sherman III/IV)
            KillDetailTruth(
                "ussr_t_34_1942", victim_username="xK1NGSH0TZx", victim_vehicle="sw_sherman_3_4", time_seconds=403
            ),
            # 8:08 Toxic85828 (T-34) destroyed InDommWeTrust (Pz.Bef.Wg.IV J)
            KillDetailTruth(
                "ussr_t_34_1942",
                victim_username="InDommWeTrust",
                victim_vehicle="germ_panzerbefelhswagen_IV_ausf_J",
                time_seconds=488,
            ),
            # 19:33 Toxic85828 (T-34) destroyed KlutzyObject6 (Sd.Kfz.234/2)
            KillDetailTruth(
                "ussr_t_34_1941_l_11",
                victim_username="KlutzyObject6",
                victim_vehicle="germ_sdkfz_234_2",
                time_seconds=1173,
            ),
            # 20:50 Toxic85828 (T-34) destroyed oliveshellhound (M24DK)
            KillDetailTruth(
                "ussr_t_34_1941_l_11",
                victim_username="oliveshellhound",
                victim_vehicle="sw_m24_chaffee_dk",
                time_seconds=1250,
            ),
        ],
        death_details=[
            # 3:47 obsidianwolf13 (☆T-34) destroyed Toxic85828 (T-34)
            DeathDetailTruth(
                "ussr_t_34_1942", killer_username="obsidianwolf13", killer_vehicle="cn_t_34_1942", time_seconds=227
            ),
            # 7:55 Ranol (SAV 20.12.48) destroyed Toxic85828 (T-34)
            DeathDetailTruth("ussr_t_34_1942", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=475),
            # 11:23 oliveshellhound (⊙Pz.IV) destroyed Toxic85828 (T-34)
            DeathDetailTruth(
                "ussr_t_34_1942",
                killer_username="oliveshellhound",
                killer_vehicle="sw_pzkpfw_IV_ausf_J",
                time_seconds=683,
            ),
            # 17:46 Evokekirby (Martin 139WC) destroyed Toxic85828 (T-34)
            DeathDetailTruth(
                "ussr_t_34_1941_l_11", killer_username="Evokekirby", killer_vehicle="martin_139wc", time_seconds=1066
            ),
            # 20:55 Ranol (⊙Pz.IV) destroyed Toxic85828 (T-34)
            DeathDetailTruth(
                "ussr_t_34_1942", killer_username="Ranol", killer_vehicle="sw_pzkpfw_IV_ausf_J", time_seconds=1255
            ),
            # 22:47 Ranol (⊙Pz.IV) destroyed Toxic85828 (T-34)
            DeathDetailTruth(
                "ussr_t_34_1941_l_11", killer_username="Ranol", killer_vehicle="sw_pzkpfw_IV_ausf_J", time_seconds=1367
            ),
        ],
    ),
    PlayerTruth(
        "Perjuro",
        team=2,
        kills_ground=11,
        kills_air=0,
        deaths_total=5,
        awards=[
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "defender_tank",
            "global_shadow_assassin",
            "global_base_defender",
            "defender_fighter",
            "first_blood",
            "marks_5_tanks",
            "marks_10_tanks",
        ],
        kill_details=[
            # 1:54 Perjuro (KV-1) destroyed Ranol (M24DK)
            KillDetailTruth(
                "ussr_kv_1_zis_5", victim_username="Ranol", victim_vehicle="sw_m24_chaffee_dk", time_seconds=114
            ),
            # 2:10 Perjuro (KV-1) destroyed Zonney0007 (Sd.Kfz.234/2)
            KillDetailTruth(
                "ussr_kv_1_zis_5", victim_username="Zonney0007", victim_vehicle="germ_sdkfz_234_2", time_seconds=130
            ),
            # 3:30 Perjuro (KV-1) destroyed b1 Val (AMX-13 (FL11))
            KillDetailTruth(
                "ussr_kv_1_zis_5", victim_username="b1 Val", victim_vehicle="fr_amx_13_fl_11", time_seconds=210
            ),
            # 4:27 Perjuro (KV-1) destroyed obsidianwolf13 (☆T-34)
            KillDetailTruth(
                "ussr_kv_1_zis_5", victim_username="obsidianwolf13", victim_vehicle="cn_t_34_1942", time_seconds=267
            ),
            # 11:14 Perjuro (T-34-57) destroyed KlutzyObject6 (StuH 42 G)
            KillDetailTruth(
                "ussr_t_34_1941_57",
                victim_username="KlutzyObject6",
                victim_vehicle="germ_stuh_III_ausf_G",
                time_seconds=674,
            ),
            # 12:20 Perjuro (I-185) destroyed oliveshellhound (⊙Pz.IV)
            KillDetailTruth(
                "i_185_m71_standard",
                victim_username="oliveshellhound",
                victim_vehicle="sw_pzkpfw_IV_ausf_J",
                time_seconds=740,
            ),
            # 12:38 Perjuro (I-185) destroyed Thorkell_83 (VTT DCA)
            KillDetailTruth(
                "i_185_m71_standard", victim_username="Thorkell_83", victim_vehicle="fr_amx_vtt_dca", time_seconds=758
            ),
            # 12:59 Perjuro (I-185) destroyed Metarou (Ikv 103)
            KillDetailTruth(
                "i_185_m71_standard", victim_username="Metarou", victim_vehicle="sw_ikv_103", time_seconds=779
            ),
            # 15:25 Perjuro (BTR-152D) destroyed bosco3202 (Sturer Emil)
            KillDetailTruth(
                "ussr_btr_152d",
                victim_username="bosco3202",
                victim_vehicle="germ_pzsflk40_sturer_emil",
                time_seconds=925,
            ),
            # 18:21 Perjuro (Pe-8) destroyed Ranol (Pbv 301)
            KillDetailTruth("pe-8_m82", victim_username="Ranol", victim_vehicle="sw_pbv_301", time_seconds=1101),
            # 18:21 Perjuro (Pe-8) destroyed Metarou (⊙T-34)
            KillDetailTruth("pe-8_m82", victim_username="Metarou", victim_vehicle="sw_t_34_1941", time_seconds=1101),
        ],
        death_details=[
            # 6:44 Ranol (SAV 20.12.48) destroyed Perjuro (KV-1)
            DeathDetailTruth(
                "ussr_kv_1_zis_5", killer_username="Ranol", killer_vehicle="sw_sav_fm48", time_seconds=404
            ),
            # 11:17 Zonney0007 (Pz.IV H) destroyed Perjuro (T-34-57)
            DeathDetailTruth(
                "ussr_t_34_1941_57",
                killer_username="Zonney0007",
                killer_vehicle="germ_pzkpfw_IV_ausf_H",
                time_seconds=677,
            ),
            # 14:28 Metarou (J26) shot down Perjuro (I-185)
            DeathDetailTruth(
                "i_185_m71_standard", killer_username="Metarou", killer_vehicle="p-51d-20-na_j26", time_seconds=868
            ),
            # 16:48 bosco3202 (Fw 190 A) destroyed Perjuro (BTR-152D)
            DeathDetailTruth(
                "ussr_btr_152d", killer_username="bosco3202", killer_vehicle="fw-190a-5_u2", time_seconds=1008
            ),
            # 22:05 Metarou (J26) shot down Perjuro (Pe-8)
            DeathDetailTruth(
                "pe-8_m82", killer_username="Metarou", killer_vehicle="p-51d-20-na_j26", time_seconds=1325
            ),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Parsed-replay fixture
# ---------------------------------------------------------------------------

WRPL_PATH = Path(__file__).parent / "2026.02.22 14.49.18.wrpl"


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
# Helpers
# ---------------------------------------------------------------------------


def _elapsed_seconds(time_utc_str: str | None, battle_start: datetime) -> float | None:
    """Convert a time_utc ISO string to elapsed seconds from battle start."""
    if time_utc_str is None:
        return None
    dt = datetime.fromisoformat(time_utc_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - battle_start).total_seconds()


def find_kill(kills: list[dict], truth: KillDetailTruth, battle_start: datetime | None = None) -> dict | None:
    """Return the first kill detail matching all non-None fields of *truth*."""
    for kd in kills:
        if kd.get("killer_vehicle") != truth.killer_vehicle:
            continue
        if truth.victim_username is not None and kd.get("victim_username") != truth.victim_username:
            continue
        if truth.victim_vehicle is not None and kd.get("victim_vehicle") != truth.victim_vehicle:
            continue
        if truth.time_seconds is not None and battle_start is not None:
            elapsed = _elapsed_seconds(kd.get("time_utc"), battle_start)
            if elapsed is not None and abs(elapsed - truth.time_seconds) > TIMESTAMP_TOLERANCE_S:
                continue
        return kd
    return None


def find_death(deaths: list[dict], truth: DeathDetailTruth, battle_start: datetime | None = None) -> dict | None:
    """Return the first death detail matching all non-None fields of *truth*."""
    for dd in deaths:
        if dd.get("victim_vehicle") != truth.victim_vehicle:
            continue
        if truth.killer_username is not None and dd.get("killer_username") != truth.killer_username:
            continue
        if truth.killer_vehicle is not None and dd.get("killer_vehicle") != truth.killer_vehicle:
            continue
        if truth.time_seconds is not None and battle_start is not None:
            elapsed = _elapsed_seconds(dd.get("time_utc"), battle_start)
            if elapsed is not None and abs(elapsed - truth.time_seconds) > TIMESTAMP_TOLERANCE_S:
                continue
        return dd
    return None


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_session_id(self, replay: dict[str, Any]) -> None:
        assert replay["session_id"] == "62fdbe50032a8bd"

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

    def test_kill_details(self, players_by_name: dict, truth: PlayerTruth) -> None:
        if not truth.kill_details:
            pytest.skip("no kill details defined for this player")
        kds = players_by_name[truth.username]["kills"]["vehicles"]
        not_found: list[KillDetailTruth] = []
        for kd_truth in truth.kill_details:
            match = find_kill(kds, kd_truth)
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

    def test_death_details(self, players_by_name: dict, truth: PlayerTruth) -> None:
        if not truth.death_details:
            pytest.skip("no death details defined for this player")
        dds = players_by_name[truth.username]["deaths"]["vehicles"]
        not_found: list[DeathDetailTruth] = []
        for dd_truth in truth.death_details:
            match = find_death(dds, dd_truth)
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
