"""Tests for replay codec/layout selection and event count caps."""

import struct
import zlib

import pytest
import zstandard

from src.replay_data_grabber.services.replay_stream_decoder_service import (
    ReplayStreamDecoderService,
    _KillEvent,
    _LateSpawnEvent,
    _ReplaySchemaStrategy,
    _StreamParseState,
    _ZLIB_REPLAY_SCHEMA,
    _ZSTANDARD_REPLAY_SCHEMA,
)


def _wrap_compressed_stream(compressed: bytes, prefix: bytes = b"") -> bytes:
    stream_start = 1224
    results_offset = stream_start + len(prefix) + len(compressed)
    raw = bytearray(results_offset)
    struct.pack_into("<I", raw, 684, results_offset)
    struct.pack_into("<I", raw, 748, 0)
    raw[stream_start:] = prefix + compressed
    return bytes(raw)


@pytest.mark.parametrize(
    ("schema", "compressed", "prefix", "expected_stream"),
    [
        (
            _ZLIB_REPLAY_SCHEMA,
            zlib.compress(b"legacy stream"),
            b"",
            b"legacy stream",
        ),
        (
            _ZSTANDARD_REPLAY_SCHEMA,
            zstandard.ZstdCompressor().compress(b"modern stream"),
            b"streamhead",
            b"modern stream",
        ),
    ],
)
def test_decompress_selects_schema_from_frame_signature(
    schema: _ReplaySchemaStrategy,
    compressed: bytes,
    prefix: bytes,
    expected_stream: bytes,
) -> None:
    raw = _wrap_compressed_stream(compressed, prefix)

    stream_data, detected_schema = (
        ReplayStreamDecoderService._decompress_stream_with_schema(raw)
    )

    assert detected_schema is schema
    assert stream_data == expected_stream


def test_raw_replay_selects_kill_layout_independently_of_codec(monkeypatch) -> None:
    stream_data = b"\x02\x58\x58\xf0\x30\x00\xfe\xff\x07"
    raw = _wrap_compressed_stream(zlib.compress(stream_data))
    decoder = ReplayStreamDecoderService()
    result = object()
    decoded = {}

    def capture_decode_stream(stream: bytes, **kwargs):
        decoded["stream"] = stream
        decoded["schema_strategy"] = kwargs["schema_strategy"]
        return result

    monkeypatch.setattr(decoder, "decode_stream", capture_decode_stream)

    assert decoder.decode_from_raw_replay(raw) is result
    assert decoded["stream"] == stream_data
    assert decoded["schema_strategy"] is _ZSTANDARD_REPLAY_SCHEMA


def test_deadwindow_inference_without_vehicle_activations_returns_empty_result() -> (
    None
):
    decoder = ReplayStreamDecoderService()

    assert decoder._infer_deadwindow_victim_eids([], {}, [], {}, [], None) == (0, set())


def test_physics_spawn_attribution_without_vehicle_activations_returns_zero() -> None:
    decoder = ReplayStreamDecoderService()

    assert decoder._infer_physics_spawn_attributions([], {}, [], {}, []) == 0


@pytest.mark.parametrize(
    ("schema", "expected_prefix"),
    [
        (_ZLIB_REPLAY_SCHEMA, b"\x00\xfe\x3f"),
        (_ZSTANDARD_REPLAY_SCHEMA, b"\x00\xfe\xff\x07"),
    ],
)
def test_kill_event_layouts_normalize_to_common_event(
    schema: _ReplaySchemaStrategy, expected_prefix: bytes
) -> None:
    vehicle = b"us_tank"
    event = (
        b"\x02\x58\x58\xf0"
        + b"\x30"
        + expected_prefix
        + struct.pack("<I", 10)
        + bytes((len(vehicle),))
        + vehicle
        + struct.pack("<HH", 512, 513)
        + b"\xff" * 4
    )
    state = _StreamParseState(schema_strategy=schema)

    ReplayStreamDecoderService()._handle_kill_event(event, 0, 7, state)

    assert state.kill_events == [_KillEvent(0, 7, 10, "us_tank", 512, 513)]


def test_build_result_caps_kill_events_to_authoritative_total() -> None:
    state = _StreamParseState(
        kill_events=[
            _KillEvent(10, 0, 0, "us_tank", 1000, 2000),
            _KillEvent(20, 1, 0, "us_tank", 1001, 2000),
            _KillEvent(30, 2, 1, "uk_tank", 1002, 2001),
        ]
    )

    result = ReplayStreamDecoderService()._build_result(
        state,
        slot_kill_caps={0: 1, 1: 1},
    )

    assert result.vehicle_kills == {0: {"us_tank": 1}, 1: {"uk_tank": 1}}
    assert len(result.kill_details) == 2


@pytest.mark.parametrize(
    ("death_cap", "expected_counted"),
    [(0, False), (1, True)],
)
def test_build_result_marks_only_scoreboard_deaths_as_counted(
    death_cap: int, expected_counted: bool
) -> None:
    state = _StreamParseState(
        kill_events=[_KillEvent(10, 0, 0, "us_tank", 1200, 1201)],
        late_spawn_events=[_LateSpawnEvent(0, 1200, 1, "uk_tank")],
    )

    result = ReplayStreamDecoderService()._build_result(
        state,
        slot_deaths={1: death_cap},
    )

    detail = result.kill_details[0]
    assert detail.victim_slot == 1
    assert detail.victim_vehicle == "uk_tank"
    assert detail.victim_death_counted is expected_counted
    assert sum(result.vehicle_deaths.get(1, {}).values()) == death_cap
