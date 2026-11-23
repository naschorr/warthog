import json

from src.replay_data_grabber.models import Player


def test_optional_player_enums_round_trip_as_json_null() -> None:
    player = Player(platform_type=None, country=None)

    serialized = json.loads(player.model_dump_json())

    assert serialized["platform_type"] is None
    assert serialized["country"] is None
    assert Player.model_validate_json(json.dumps(serialized)) == player


def test_optional_player_enums_accept_legacy_none_strings() -> None:
    player = Player.model_validate(
        {
            "platform_type": "None",
            "country": "None",
        }
    )

    assert player.platform_type is None
    assert player.country is None
