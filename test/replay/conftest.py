from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.common.factories import ServiceFactory


@pytest.fixture(scope="module")
def replay(request: pytest.FixtureRequest) -> dict[str, Any]:
    replay_path = getattr(request.module, "WRPL_PATH", None)
    if not isinstance(replay_path, Path):
        pytest.fail(f"{request.module.__name__} must define WRPL_PATH")
    parser = ServiceFactory().get_replay_parser_service()
    parsed_replay = parser.parse_replay_file(replay_path)
    return parsed_replay.model_dump(mode="json")


@pytest.fixture(scope="module")
def players_by_name(replay: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {player["username"]: player for player in replay["players"]}


@pytest.fixture(scope="module")
def battle_start(replay: dict[str, Any]) -> datetime:
    start = datetime.fromisoformat(replay["start_time"])
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start
