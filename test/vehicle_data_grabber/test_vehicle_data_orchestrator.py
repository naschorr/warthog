import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.common
from src.vehicle_data_grabber.configuration.configuration_models import VehicleDataOrchestratorConfig
from src.vehicle_data_grabber.services.vehicle_data_orchestrator import VehicleDataOrchestrator


class FakeVehicleDataProcessor:
    def __init__(self, release_datetimes_path: Path, *, fail_version: str | None = None):
        self._release_datetimes_path = release_datetimes_path
        self._fail_version = fail_version
        self.processed_versions: list[str] = []

    def get_datamined_file_paths(self) -> list[Path]:
        return []

    def process_vehicle_data(self, *, repository_version: str, repository_path: Path):
        release_datetimes = json.loads(self._release_datetimes_path.read_text(encoding="utf-8"))
        assert repository_version not in release_datetimes
        self.processed_versions.append(repository_version)
        if repository_version == self._fail_version:
            raise RuntimeError(f"Failed to process {repository_version}")


class FakeGitRepositoryClient:
    def __init__(self, repository_path: Path, tags=()):
        self.repository = SimpleNamespace(working_dir=repository_path)
        self.is_cloned = False
        self.checked_out_versions: list[str] = []
        self._tags = tags

    def clone_partial(self, *, sparse_paths: list[Path]) -> None:
        self.is_cloned = True

    def get_tags(self):
        return self._tags

    def checkout_branch(self, version: str) -> None:
        self.checked_out_versions.append(version)

    def get_head_date(self, *, utc: bool = False) -> datetime:
        return datetime(2025, 2, 3, 4, 5, 6)


def create_orchestrator(
    tmp_path: Path,
    *,
    versions: list[str] | None,
    processor: FakeVehicleDataProcessor,
    release_datetimes_path: Path,
    replay_manager_service=None,
    tags=(),
) -> VehicleDataOrchestrator:
    config = VehicleDataOrchestratorConfig(
        working_directory_path=tmp_path / "working",
        game_versions=versions or [],
        datamine_data_directory_path=tmp_path / "datamine",
        store_datamine_data=False,
        game_version_release_datetimes_file_path=release_datetimes_path,
    )
    orchestrator = VehicleDataOrchestrator(
        config,
        vehicle_data_processor=processor,
        replay_manager_service=replay_manager_service,
    )
    orchestrator._git_repository_client = FakeGitRepositoryClient(tmp_path / "repository", tags)
    orchestrator._clean_working_directory = lambda: None
    return orchestrator


def test_selects_tags_covering_processed_and_raw_replay_dates(tmp_path: Path):
    release_datetimes_path = tmp_path / "release_datetimes.json"
    release_datetimes_path.write_text("{}", encoding="utf-8")
    replay_dates = [datetime(2025, 1, 15)]
    processed_raw_replay = tmp_path / "processed.wrpl"
    raw_replay_dates = {
        processed_raw_replay: datetime(2025, 2, 1),
        tmp_path / "raw-one.wrpl": datetime(2025, 4, 10),
        tmp_path / "raw-two.wrpl": datetime(2025, 4, 12),
    }
    raw_replay_session_ids = {
        processed_raw_replay: "0",
        tmp_path / "raw-one.wrpl": "raw-one",
        tmp_path / "raw-two.wrpl": "raw-two",
    }
    parsed_raw_replays = []

    def get_replay_start_time(path: Path) -> datetime:
        parsed_raw_replays.append(path)
        return raw_replay_dates[path]

    replay_manager_service = SimpleNamespace(
        loaded_replays={
            str(index): SimpleNamespace(start_time=replay_date)
            for index, replay_date in enumerate(replay_dates)
        },
        _raw_replay_dir_path=tmp_path,
        discover_raw_replay_files=lambda _: raw_replay_session_ids,
        _replay_parser_service=SimpleNamespace(
            get_start_time_from_replay_file=get_replay_start_time
        ),
    )
    tags = [
        SimpleNamespace(
            name="future-version",
            commit=SimpleNamespace(committed_datetime=datetime(2025, 5, 1, tzinfo=timezone.utc)),
        ),
        SimpleNamespace(
            name="spring-version",
            commit=SimpleNamespace(committed_datetime=datetime(2025, 3, 1, tzinfo=timezone.utc)),
        ),
        SimpleNamespace(
            name="winter-version",
            commit=SimpleNamespace(committed_datetime=datetime(2025, 1, 1, tzinfo=timezone.utc)),
        ),
    ]
    orchestrator = create_orchestrator(
        tmp_path,
        versions=None,
        processor=FakeVehicleDataProcessor(release_datetimes_path),
        release_datetimes_path=release_datetimes_path,
        replay_manager_service=replay_manager_service,
        tags=tags,
    )

    assert orchestrator.get_game_versions() == ["winter-version", "spring-version"]
    assert parsed_raw_replays == [tmp_path / "raw-one.wrpl", tmp_path / "raw-two.wrpl"]


def test_skips_versions_in_release_datetime_map_and_preserves_existing_entries(tmp_path: Path):
    release_datetimes_path = tmp_path / "release_datetimes.json"
    existing_datetime = "2025-01-01 00:00:00"
    release_datetimes_path.write_text(
        json.dumps({"already-processed": existing_datetime}),
        encoding="utf-8",
    )
    processor = FakeVehicleDataProcessor(release_datetimes_path)
    orchestrator = create_orchestrator(
        tmp_path,
        versions=["already-processed", "new-version"],
        processor=processor,
        release_datetimes_path=release_datetimes_path,
    )

    orchestrator.run_orchestrator()

    assert processor.processed_versions == ["new-version"]
    assert orchestrator._git_repository_client.checked_out_versions == ["new-version"]
    assert json.loads(release_datetimes_path.read_text(encoding="utf-8")) == {
        "already-processed": existing_datetime,
        "new-version": "2025-02-03 04:05:06",
    }


def test_failed_version_is_not_written_but_successful_versions_are_preserved(tmp_path: Path):
    release_datetimes_path = tmp_path / "release_datetimes.json"
    release_datetimes_path.write_text("{}", encoding="utf-8")
    processor = FakeVehicleDataProcessor(release_datetimes_path, fail_version="failed-version")
    orchestrator = create_orchestrator(
        tmp_path,
        versions=["successful-version", "failed-version"],
        processor=processor,
        release_datetimes_path=release_datetimes_path,
    )

    with pytest.raises(RuntimeError, match="Failed to process failed-version"):
        orchestrator.run_orchestrator()

    assert processor.processed_versions == ["successful-version", "failed-version"]
    assert json.loads(release_datetimes_path.read_text(encoding="utf-8")) == {
        "successful-version": "2025-02-03 04:05:06"
    }
