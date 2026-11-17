"""Tests for decoding and interpolating replay tick timestamps."""

import struct

from src.replay_data_grabber.services.replay_stream_decoder_service import (
    ReplayStreamDecoderService,
    _TICK_MARKER,
)


def _tick(timestamp_ms: int) -> bytes:
    return struct.pack("<I", timestamp_ms) + _TICK_MARKER + bytes(18)


def test_tick_times_interpolate_outliers_and_keep_late_game_times() -> None:
    timestamps = [1_366_658, 1_366_738, 1_353_952, 1_366_906]
    stream_data = b"".join(_tick(timestamp) for timestamp in timestamps)
    decoder = ReplayStreamDecoderService()

    offsets = decoder._parse_tick_boundaries(stream_data)

    assert len(offsets) == len(timestamps)
    assert decoder._build_tick_game_times(stream_data, offsets) == [
        1_366_658,
        1_366_738,
        1_366_822,
        1_366_906,
    ]


def test_tick_time_seed_ignores_leading_false_markers() -> None:
    timestamps = [
        1_363_021,
        100,
        5_382,
        1_317_186,
        5_466,
        1_348_960,
        5_598,
        5_672,
        1_351_552,
        5_712,
    ]
    stream_data = b"".join(_tick(timestamp) for timestamp in timestamps)
    decoder = ReplayStreamDecoderService()

    offsets = decoder._parse_tick_boundaries(stream_data)

    game_times = decoder._build_tick_game_times(stream_data, offsets)

    assert len(offsets) == len(timestamps)
    assert game_times[2] == 5_382
    assert game_times[4] == 5_466
    assert game_times[6] == 5_598
    assert game_times[7] == 5_672
    assert game_times[9] == 5_712
    assert game_times == sorted(game_times)
