#!/usr/bin/env python3
"""
Extract players and their lineups from a parsed replay JSON.

Usage:
    python test/replay/extract_lineups.py <parsed_replay.json> [--vehicle-data <vehicle_data.json>]

If --vehicle-data is provided, each vehicle_id is annotated with its display name.
When omitted, the script auto-discovers the latest vehicle data file in
data/vehicle_data/processed_vehicle_data/.

Output: a table of all players with team, author status, lineup vehicle IDs
        (with display names when vehicle data is available), and scalar stats.

Example:
    python test/replay/extract_lineups.py test/replay/63ef86a001440d4/replay_2026-03-06_00-52-48_63ef86a001440d4.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def find_latest_vehicle_data(repo_root: Path) -> Path | None:
    """Auto-discover the latest processed_vehicle_data JSON by version sort."""
    vdata_dir = repo_root / "data" / "vehicle_data" / "processed_vehicle_data"
    if not vdata_dir.is_dir():
        return None

    def version_key(p: Path) -> tuple[int, ...]:
        # processed_vehicle_data.2.53.0.88.json → (2, 53, 0, 88)
        stem = p.stem  # processed_vehicle_data.2.53.0.88
        parts = stem.split(".")[1:]  # ['2', '53', '0', '88']
        try:
            return tuple(int(x) for x in parts)
        except ValueError:
            return (0,)

    candidates = sorted(vdata_dir.glob("processed_vehicle_data.*.json"), key=version_key)
    return candidates[-1] if candidates else None


def load_vehicle_names(vehicle_data_path: Path) -> dict[str, str]:
    """Return {vehicle_id: display_name} from processed vehicle data."""
    with open(vehicle_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {vid: entry.get("name", vid) for vid, entry in data.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract player lineups from a parsed replay JSON.")
    parser.add_argument("replay_json", type=Path, help="Path to the parsed replay JSON file")
    parser.add_argument(
        "--vehicle-data",
        type=Path,
        default=None,
        help="Path to a processed_vehicle_data JSON. Auto-discovered if omitted.",
    )
    args = parser.parse_args()

    # Load parsed replay
    with open(args.replay_json, "r", encoding="utf-8") as f:
        replay = json.load(f)

    # Resolve vehicle data
    vehicle_names: dict[str, str] = {}
    vdata_path = args.vehicle_data
    if vdata_path is None:
        # Auto-discover from repo root (assumes script is at test/replay/)
        repo_root = Path(__file__).resolve().parent.parent.parent
        vdata_path = find_latest_vehicle_data(repo_root)
    if vdata_path and vdata_path.is_file():
        vehicle_names = load_vehicle_names(vdata_path)
        print(f"# Vehicle data: {vdata_path.name}", file=sys.stderr)
    else:
        print("# No vehicle data found — showing vehicle_ids only", file=sys.stderr)

    # Extract metadata
    session_id = replay.get("session_id", "?")
    start_time = replay.get("start_time", "?")
    author_name = replay.get("author", {}).get("username", "?")
    players = replay.get("players", [])

    print(f"# Session: {session_id}")
    print(f"# Start:   {start_time}")
    print(f"# Author:  {author_name}")
    print(f"# Players: {len(players)}")
    print()

    # Sort by team then username
    sorted_players = sorted(players, key=lambda p: (p["team"], p["username"]))

    for p in sorted_players:
        username = p["username"]
        team = p["team"]
        is_author = " [AUTHOR]" if username == author_name else ""
        kills_g = p.get("kills", {}).get("ground", 0)
        kills_a = p.get("kills", {}).get("air", 0)
        deaths_t = p.get("deaths", {}).get("total", 0)
        lineup = p.get("lineup", [])

        print(f"{'='*60}")
        print(f"  {username}{is_author}")
        print(f"  Team {team} | K(g)={kills_g} K(a)={kills_a} D={deaths_t}")
        print(f"  Lineup ({len(lineup)} vehicles):")
        for vid in lineup:
            display = vehicle_names.get(vid)
            if display:
                print(f"    - {vid}  ({display})")
            else:
                print(f"    - {vid}")
        print()


if __name__ == "__main__":
    main()
