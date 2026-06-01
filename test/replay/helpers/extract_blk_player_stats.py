#!/usr/bin/env python3
"""
Extract the post-game BLK section from a War Thunder .wrpl replay and dump player kills/deaths/assists.

Usage:
    python test/replay/helpers/extract_blk_player_stats.py <replay.wrpl>
    python test/replay/helpers/extract_blk_player_stats.py <replay.wrpl> --wt-ext-cli <path/to/wt_ext_cli>

The script reads the results offset from the .wrpl header, extracts the embedded BLK section,
passes it to wt_ext_cli, and prints a per-player summary from the post-game results data.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def extract_results_offset(raw_replay: bytes) -> int:
    if len(raw_replay) < 684:
        raise ValueError("Replay file is too small to contain a valid header")

    # Header layout based on src/replay_data_grabber/services/replay_parser_service.py
    # 0..3    = magic
    # 4..7    = version
    # 8..135  = level
    # 136..395 = level settings
    # 396..523 = battle type
    # 524..651 = environment
    # 652..683 = visibility
    # 684..687 = results_offset
    results_offset = struct.unpack("<I", raw_replay[684:688])[0]
    return results_offset


def resolve_player_info(player_data: dict, players_info: dict[str, dict]) -> tuple[str, str, int | None]:
    user_id = str(player_data.get("userId", ""))
    for info in players_info.values():
        if str(info.get("id", "")) == user_id:
            username = info.get("username") or info.get("name") or user_id
            team = info.get("team")
            return username, info.get("squadronTag", ""), team
    return f"<unknown:{user_id}>", "", None


def format_stats(player_data: dict[str, object]) -> str:
    ground = player_data.get("groundKills", 0)
    air = player_data.get("kills", 0)
    naval = player_data.get("navalKills", 0)
    team_kills = player_data.get("teamKills", 0)
    ai_ground = player_data.get("aiGroundKills", 0)
    ai_air = player_data.get("aiKills", 0)
    ai_naval = player_data.get("aiNavalKills", 0)
    deaths = player_data.get("deaths", 0)
    assists = player_data.get("assists", 0)
    return (
        f"G={ground:<2} A={air:<2} N={naval:<2} T={team_kills:<2} "
        f"AI_G={ai_ground:<2} AI_A={ai_air:<2} AI_N={ai_naval:<2} "
        f"D={deaths:<2} S={assists:<2}"
    )


def load_results_from_blk(results_bytes: bytes, wt_ext_cli_path: Path | None) -> dict:
    from src.replay_data_grabber.services.wt_ext_cli_client_service import WtExtCliClientService
    from src.replay_data_grabber.configuration.configuration_models import WtExtCliServiceConfig

    config_kwargs = {}
    if wt_ext_cli_path is not None:
        config_kwargs["wt_ext_cli_path"] = wt_ext_cli_path

    config = WtExtCliServiceConfig(**config_kwargs)
    client = WtExtCliClientService(config)
    return client.unpack_raw_blk(results_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract BLK player stats from a War Thunder .wrpl file.")
    parser.add_argument("replay_file", type=Path, help="Path to the raw .wrpl replay file")
    parser.add_argument(
        "--wt-ext-cli",
        dest="wt_ext_cli",
        type=Path,
        default=None,
        help="Optional path to the wt_ext_cli executable. If omitted, the script will auto-discover it in the repo.",
    )
    parser.add_argument(
        "--dump-json",
        type=Path,
        default=None,
        help="Optional path to write the decoded BLK JSON output.",
    )
    parser.add_argument(
        "--player",
        metavar="USERNAME",
        action="append",
        dest="players_filter",
        default=None,
        help="Only show this player (case-insensitive). Repeat for multiple players.",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    sys.path.insert(0, str(repo_root))

    replay_path = args.replay_file
    if not replay_path.exists():
        raise FileNotFoundError(f"Replay file not found: {replay_path}")

    raw_replay = replay_path.read_bytes()
    if raw_replay[:4] != b"\xe5\xac\x00\x10":
        raise ValueError("Invalid replay file header; expected War Thunder WRPL magic bytes")

    results_offset = extract_results_offset(raw_replay)
    if results_offset <= 0 or results_offset >= len(raw_replay):
        raise ValueError(f"Invalid results offset: {results_offset}")

    results_bytes = raw_replay[results_offset:]
    print(f"# Replay: {replay_path.name}")
    print(f"# Results offset: {results_offset}")
    print(f"# Results length: {len(results_bytes)} bytes")

    results = load_results_from_blk(results_bytes, args.wt_ext_cli)

    if args.dump_json:
        args.dump_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"# Dumped BLK JSON to {args.dump_json}")

    players_array = results.get("player", [])
    ui_scripts_data = results.get("uiScriptsData", {})
    players_info = ui_scripts_data.get("playersInfo", {})

    print()
    print("# Player stats from BLK results")
    print("username                     team squad  stats")
    print("-" * 90)

    sorted_players = sorted(players_array, key=lambda p: str(p.get("userId", "")))
    filter_lower = {name.lower() for name in args.players_filter} if args.players_filter else None
    for player_data in sorted_players:
        username, squadron_tag, team = resolve_player_info(player_data, players_info)
        if filter_lower and username.lower() not in filter_lower:
            continue
        team_display = str(team) if team is not None else "?"
        squad_display = squadron_tag or "-"
        print(f"{username:<25} {team_display:<4} {squad_display:<6} {format_stats(player_data)}")


if __name__ == "__main__":
    main()
