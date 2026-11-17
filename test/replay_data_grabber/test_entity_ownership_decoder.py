import logging
from pathlib import Path

from src.replay_data_grabber.services.entity_ownership_decoder import (
    EntityOwnership,
    decode_entity_ownership,
)
from src.replay_data_grabber.services.replay_stream_decoder_service import (
    ReplayStreamDecoderService,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _ownership_for_replay(path: Path) -> dict[int, list[EntityOwnership]]:
    stream_data = ReplayStreamDecoderService._decompress_stream(path.read_bytes())
    return decode_entity_ownership(stream_data)


def test_replay_62_kv1s_uid_resolves_to_player_slot_11() -> None:
    replay_path = FIXTURE_DIR / "62fdbe50032a8bd" / "2026.02.22 14.49.18.wrpl"

    entry = _ownership_for_replay(replay_path)[126][-1]

    assert (entry.player_id, entry.vehicle_name) == (11, "ussr_kv_1s")


def test_replay_63_victim_uids_resolve_to_player_slots() -> None:
    replay_path = FIXTURE_DIR / "63ef86a001440d4" / "#2026.03.06 01.16.49.wrpl"
    ownership = _ownership_for_replay(replay_path)

    assert (ownership[309][-1].player_id, ownership[309][-1].vehicle_name) == (
        3,
        "ussr_t_50",
    )
    assert (ownership[316][-1].player_id, ownership[316][-1].vehicle_name) == (
        27,
        "us_halftrack_m16",
    )


def test_truncated_ecs_packet_size_is_reported(caplog) -> None:
    with caplog.at_level(logging.WARNING):
        ownership = decode_entity_ownership(b"\x40")

    assert ownership == {}
    assert "Truncated two-byte packet size" in caplog.text
