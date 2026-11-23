import json
from pathlib import Path
from types import SimpleNamespace

from src.common.factories import ServiceFactory
from src.replay_data_grabber.configuration import ReplayManagerServiceConfig
from src.replay_data_grabber.services.replay_manager_service import ReplayManagerService


def test_manager_can_skip_loading_processed_replays(tmp_path: Path, monkeypatch) -> None:
    config = ReplayManagerServiceConfig(
        raw_replay_dir=tmp_path,
        processed_replay_dir=tmp_path / "processed",
    )

    def unexpected_load(self):
        raise AssertionError("Processed replays should not be loaded")

    monkeypatch.setattr(ReplayManagerService, "load_processed_replays", unexpected_load)

    manager = ReplayManagerService(
        config,
        replay_parser_service=SimpleNamespace(),
        load_existing_replays=False,
    )

    assert manager.loaded_replays == {}
    assert manager._loaded_session_ids == set()


def test_manager_still_loads_processed_replays_by_default(tmp_path: Path, monkeypatch) -> None:
    config = ReplayManagerServiceConfig(
        raw_replay_dir=tmp_path,
        processed_replay_dir=tmp_path / "processed",
    )
    calls = []

    def load_processed_replays(self):
        calls.append(True)
        return {"existing-session"}, {}

    monkeypatch.setattr(ReplayManagerService, "load_processed_replays", load_processed_replays)

    manager = ReplayManagerService(
        config,
        replay_parser_service=SimpleNamespace(),
    )

    assert calls == [True]
    assert manager._loaded_session_ids == {"existing-session"}


def test_factory_forwards_load_existing_replays_option(tmp_path: Path, monkeypatch) -> None:
    config = ReplayManagerServiceConfig(
        raw_replay_dir=tmp_path,
        processed_replay_dir=tmp_path / "processed",
    )
    factory = object.__new__(ServiceFactory)
    factory._config = SimpleNamespace(
        replay_data_grabber_config=SimpleNamespace(
            replay_manager_service_config=config,
        )
    )
    factory._replay_manager_service = None
    monkeypatch.setattr(factory, "get_replay_parser_service", lambda: SimpleNamespace())
    monkeypatch.setattr(
        ReplayManagerService,
        "load_processed_replays",
        lambda self: (_ for _ in ()).throw(AssertionError("Processed replays should not be loaded")),
    )

    manager = factory.get_replay_manager_service(load_existing_replays=False)

    assert manager._loaded_session_ids == set()


def test_processed_replay_discovery_reads_session_id_without_model_validation(tmp_path: Path) -> None:
    config = ReplayManagerServiceConfig(
        raw_replay_dir=tmp_path,
        processed_replay_dir=tmp_path / "processed",
    )
    replay_file = config.processed_replay_dir / "replay_invalid-optional-player-fields.json"
    replay_file.write_text(
        json.dumps(
            {
                "session_id": "existing-session",
                "players": [{"platform_type": None, "country": None}],
            }
        ),
        encoding="utf-8",
    )
    manager = ReplayManagerService(
        config,
        replay_parser_service=SimpleNamespace(),
        load_existing_replays=False,
    )

    assert manager.discover_processed_replay_files() == {
        replay_file: "existing-session",
    }
