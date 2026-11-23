import json
from datetime import datetime

import src.common
from src.common.configuration import VehicleServiceConfig
from src.common.services.vehicle_service import VehicleService


def test_vehicle_buckets_are_loaded_on_demand_and_cached(tmp_path):
    vehicle_data_directory = tmp_path / "vehicle_data"
    vehicle_data_directory.mkdir()
    older_path = vehicle_data_directory / "processed_vehicle_data.1.0.json"
    newer_path = vehicle_data_directory / "processed_vehicle_data.2.0.json"
    older_path.write_text("{}", encoding="utf-8")
    newer_path.write_text("{}", encoding="utf-8")

    release_datetimes_path = tmp_path / "release_datetimes.json"
    release_datetimes_path.write_text(
        json.dumps(
            {
                "1.0": "2025-01-01 00:00:00",
                "2.0": "2025-02-01 00:00:00",
            }
        ),
        encoding="utf-8",
    )
    service = VehicleService(
        VehicleServiceConfig(
            processed_vehicle_data_directory_path=vehicle_data_directory,
            game_version_to_release_datetime_file_path=release_datetimes_path,
        )
    )
    loaded_paths = []
    service._load_vehicle_data_bucket = lambda path: loaded_paths.append(path) or {}

    assert loaded_paths == []
    service.get_all_vehicles(search_datetime=datetime(2025, 3, 1))
    service.get_all_vehicles(search_datetime=datetime(2025, 3, 1))
    assert loaded_paths == [newer_path]

    service.get_all_vehicles(search_datetime=datetime(2025, 1, 15))
    assert loaded_paths == [newer_path, older_path]
