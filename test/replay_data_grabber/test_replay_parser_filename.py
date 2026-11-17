"""Tests for timestamped replay filename parsing."""

from datetime import datetime
from pathlib import Path

import pytest

from src.replay_data_grabber.services.replay_parser_service import ReplayParserService


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("#2026.03.20 00.47.16.wrpl", datetime(2026, 3, 20, 0, 47, 16)),
        ("2026.06.06 14.23.57 nuke.wrpl", datetime(2026, 6, 6, 14, 23, 57)),
        (
            "2026.08.05 19.04.59 nuke in flight.wrpl",
            datetime(2026, 8, 5, 19, 4, 59),
        ),
    ],
)
def test_replay_end_time_accepts_timestamped_filenames_with_suffix(
    filename: str, expected: datetime
) -> None:
    assert (
        ReplayParserService._get_replay_end_time_from_filename(Path(filename))
        == expected
    )


def test_replay_end_time_rejects_non_timestamp_filename() -> None:
    with pytest.raises(ValueError, match="does not start with a timestamp"):
        ReplayParserService._get_replay_end_time_from_filename(Path("battle.wrpl"))
