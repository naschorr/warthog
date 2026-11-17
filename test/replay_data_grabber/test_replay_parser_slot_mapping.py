"""Tests for preserving replay player slots and filtering event attribution."""

from datetime import datetime
from types import SimpleNamespace

from src.common.enums import BattleType, BattleVehicleClassType
from src.replay_data_grabber.models import Player
from src.replay_data_grabber.services.replay_parser_service import (
    ReplayParserService,
)
from src.replay_data_grabber.services.replay_stream_decoder_service import (
    StreamDecodeResult,
    _RawKillDetail,
)


def test_missing_player_info_preserves_author_stream_slot(monkeypatch) -> None:
    results = {
        "authorUserId": "19608329",
        "player": [
            {"userId": "-1", "name": ""},
            {"userId": "-1", "name": ""},
            {
                "userId": "19608329",
                "name": "Ranol",
                "groundKills": 7,
                "deaths": 3,
                "team": 2,
            },
        ],
        "uiScriptsData": {"playersInfo": {}},
    }
    wt_ext_cli = SimpleNamespace(unpack_raw_blk=lambda _: results)
    parser = ReplayParserService(
        vehicle_service=None,
        wt_ext_cli_client_service=wt_ext_cli,
    )
    header = {
        "version": 101374,
        "level": "test",
        "level_settings": "",
        "environment": "",
        "visibility": "",
        "battle_type": BattleType.REALISTIC,
        "session_type": 0,
        "session_id": "test-session",
        "loc_name": "",
        "start_time": datetime(2026, 1, 1),
        "time_limit_minutes": 0,
        "score_limit": 0,
        "battle_class": BattleVehicleClassType.AIR_GROUND,
        "battle_kill_streak": "",
        "results_offset": 1,
    }
    monkeypatch.setattr(parser, "_parse_replay_header", lambda _: header)
    decoded_slots = {}
    decoded_kill_caps = {}

    def decode_stream(_data: bytes, **kwargs):
        decoded_slots.update(kwargs["slot_deaths"])
        decoded_kill_caps.update(kwargs["slot_kill_caps"])
        return StreamDecodeResult(
            kill_details=[
                _RawKillDetail(
                    killer_slot=2,
                    killer_vehicle="sw_cv_90105",
                    victim_slot=None,
                    victim_vehicle=None,
                )
            ]
        )

    monkeypatch.setattr(
        parser._replay_stream_decoder, "decode_from_raw_replay", decode_stream
    )

    replay = parser.parse_replay_data(b"test replay data")

    assert len(replay.players) == 1
    assert replay.author.username == "Ranol"
    assert replay.author.slot == 2
    assert replay.author.kills.ground == 7
    assert replay.author.deaths.total == 3
    assert decoded_slots == {2: 3}
    assert decoded_kill_caps == {2: 7}
    assert replay.author.kills.vehicles[0].killer_slot == 2


def test_filtered_kill_event_does_not_add_death_detail() -> None:
    parser = ReplayParserService(
        vehicle_service=None,
        wt_ext_cli_client_service=SimpleNamespace(),
    )
    killer = Player(
        user_id="killer-id",
        username="killer",
        slot=0,
        lineup=["us_tank"],
    )
    victim = Player(
        user_id="victim-id",
        username="victim",
        slot=1,
        lineup=["uk_tank"],
    )
    replay = SimpleNamespace(
        players=[killer, victim],
        start_time=datetime(2026, 1, 1),
    )
    stream_result = StreamDecodeResult(
        kill_details=[
            _RawKillDetail(
                killer_slot=0,
                killer_vehicle="us_tank",
                victim_slot=1,
                victim_vehicle="uk_tank",
            )
        ]
    )

    parser._apply_stream_result(replay, stream_result)

    assert len(killer.kills.vehicles) == 1
    assert killer.kills.vehicles[0].victim_slot == 1
    assert victim.deaths.vehicles == []
