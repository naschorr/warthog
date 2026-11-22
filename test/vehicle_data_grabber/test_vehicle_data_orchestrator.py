import json
from datetime import datetime
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
    def __init__(self, repository_path: Path):
        self.repository = SimpleNamespace(working_dir=repository_path)
        self.is_cloned = False
        self.checked_out_versions: list[str] = []

    def clone_partial(self, *, sparse_paths: list[Path]) -> None:
        self.is_cloned = True

    def checkout_branch(self, version: str) -> None:
        self.checked_out_versions.append(version)

    def get_head_date(self, *, utc: bool = False) -> datetime:
        return datetime(2025, 2, 3, 4, 5, 6)


def create_orchestrator(
    tmp_path: Path,
    *,
    versions: list[str],
    processor: FakeVehicleDataProcessor,
    release_datetimes_path: Path,
) -> VehicleDataOrchestrator:
    config = VehicleDataOrchestratorConfig(
        working_directory_path=tmp_path / "working",
        game_versions=versions,
        datamine_data_directory_path=tmp_path / "datamine",
        store_datamine_data=False,
        game_version_release_datetimes_file_path=release_datetimes_path,
    )
    orchestrator = VehicleDataOrchestrator(
        config,
        vehicle_data_processor=processor,
        replay_manager_service=None,
    )
    orchestrator._git_repository_client = FakeGitRepositoryClient(tmp_path / "repository")
    orchestrator._clean_working_directory = lambda: None
    return orchestrator


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
