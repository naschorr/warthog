import argparse
import json
from datetime import datetime
from pathlib import Path


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive whole number")
    return parsed


def _normalize_booster_type(value: str) -> str:
    booster_type = value.strip().lower()
    if booster_type not in {"research", "silver_lions"}:
        raise argparse.ArgumentTypeError("type must be one of: research, silver_lions")
    return booster_type


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a booster activation into Warthog config.")
    parser.add_argument(
        "--config-path",
        type=str,
        default="src/config.dev.json",
        help="Path to the config file to update (default: src/config.dev.json)",
    )
    parser.add_argument(
        "--type",
        required=True,
        type=_normalize_booster_type,
        help="Booster type: research or silver_lions",
    )
    parser.add_argument(
        "--audience",
        default="self",
        choices=["self", "public"],
        help="Booster audience. Default is self. Only public is persisted.",
    )
    parser.add_argument(
        "--amount-percent",
        required=True,
        type=_positive_int,
        help="Booster percent value, for example 150",
    )
    parser.add_argument(
        "--duration-matches",
        required=True,
        type=_positive_int,
        help="Number of matches this booster applies to",
    )
    return parser.parse_args()


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _save_config(config: dict, config_path: Path) -> None:
    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4, ensure_ascii=True)
        file.write("\n")


def main() -> int:
    args = parse_arguments()
    config_path = Path(args.config_path)

    config = _load_config(config_path)

    replay_data_explorer_config = config.setdefault("replay_data_explorer_config", {})
    boosters = replay_data_explorer_config.setdefault("boosters", [])

    booster_type = args.type
    audience = args.audience
    amount_percent = args.amount_percent
    duration_matches = args.duration_matches

    booster_entry = {
        "activation_timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "type": booster_type,
        "amount_percent": amount_percent,
        "duration_matches": duration_matches,
        "duration_hours": 24,
    }

    if audience == "public":
        booster_entry["audience"] = "public"

    boosters.append(booster_entry)

    _save_config(config, config_path)

    print(f"Added booster to {config_path}")
    print(
        f"type={booster_type}, audience={audience}, amount_percent={amount_percent}, "
        f"duration_matches={duration_matches}"
    )
    return 0


if __name__ == "__main__":
    main()
