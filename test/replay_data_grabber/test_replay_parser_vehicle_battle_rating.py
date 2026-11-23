import struct
from types import SimpleNamespace

import pytest

from src.common.enums import BattleType, BattleVehicleClassType
from src.replay_data_grabber.services.replay_parser_service import ReplayParserService


class StubVehicleService:
    def get_vehicles_by_internal_name(self, internal_name: str, *, search_datetime=None):
        assert internal_name == "f-4jk"
        return SimpleNamespace(
            battle_rating={
                BattleVehicleClassType.AIR: SimpleNamespace(
                    arcade=11.7,
                    realistic=12.0,
                    simulation=12.0,
                ),
                BattleVehicleClassType.AIR_GROUND: SimpleNamespace(
                    arcade=11.7,
                    realistic=10.3,
                    simulation=10.3,
                ),
            }
        )


def make_replay_header(level_settings: str, battle_class_raw: str) -> bytes:
    data = bytearray(1200)
    data[:4] = ReplayParserService.MAGIC

    def write_string(offset: int, length: int, value: str) -> None:
        encoded = value.encode("utf-8")
        data[offset : offset + min(len(encoded), length)] = encoded[:length]

    struct.pack_into("<I", data, 4, 1)
    write_string(8, 128, "levels/avg_soviet_range.bin")
    write_string(136, 260, level_settings)
    write_string(524, 128, "environment")
    write_string(652, 32, "visibility")
    struct.pack_into("<I", data, 684, 0)
    data[688] = 5
    data[724] = 0
    struct.pack_into("<Q", data, 732, 1)
    write_string(780, 128, "Soviet Range")
    struct.pack_into("<I", data, 908, 0)
    struct.pack_into("<I", data, 912, 0)
    struct.pack_into("<I", data, 916, 0)
    struct.pack_into("<I", data, 964, 11)
    write_string(968, 128, battle_class_raw)
    return bytes(data)


@pytest.mark.parametrize(
    ("battle_class_raw", "level_settings", "expected_class"),
    [
        (
            "air",
            "gamedata/missions/cta/tanks/soviet_range/soviet_range_dom.blk",
            BattleVehicleClassType.AIR,
        ),
        (
            "air",
            "gamedata/missions/cta/planes/berlin/berlin_dom.blk",
            BattleVehicleClassType.AIR,
        ),
        (
            "air_ground_dom",
            "gamedata/missions/cta/planes/berlin/berlin_dom.blk",
            BattleVehicleClassType.AIR_GROUND,
        ),
    ],
)
def test_header_parsing_uses_battle_class_field_not_mission_path(
    battle_class_raw: str,
    level_settings: str,
    expected_class: BattleVehicleClassType,
) -> None:
    parser = object.__new__(ReplayParserService)

    header = parser._parse_replay_header(
        make_replay_header(level_settings, battle_class_raw)
    )

    assert header["battle_class"] == expected_class


def test_realistic_ground_replay_uses_f4jk_air_ground_rating() -> None:
    parser = object.__new__(ReplayParserService)
    parser._vehicle_service = StubVehicleService()
    level_settings = "gamedata/missions/cta/tanks/soviet_range/soviet_range_dom.blk"

    header = parser._parse_replay_header(
        make_replay_header(level_settings, "air_ground_Dom")
    )
    battle_class = header["battle_class"]
    battle_rating = parser._get_player_battle_rating(
        battle_class,
        header["battle_type"],
        ["f-4jk"],
    )

    assert battle_class == BattleVehicleClassType.AIR_GROUND
    assert battle_rating == 10.3


def test_missing_lineup_battle_ratings_do_not_abort_replay_parsing(caplog) -> None:
    parser = object.__new__(ReplayParserService)
    parser._vehicle_service = StubVehicleService()

    battle_rating = parser._get_player_battle_rating(
        BattleVehicleClassType.AIR,
        BattleType.REALISTIC,
        [],
    )

    assert battle_rating == 0.0
    assert "using 0.0" in caplog.text
