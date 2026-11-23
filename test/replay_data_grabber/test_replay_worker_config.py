from pathlib import Path
from types import SimpleNamespace

from src.replay_data_grabber.configuration import (
    ReplayManagerServiceConfig,
    WarthogReplayDataGrabberConfig,
)
from src.replay_data_grabber.models.enums import ProcessingMode
from src.replay_data_grabber.warthog_replay_data_grabber import (
    WarthogReplayDataGrabber,
)


def create_config(tmp_path: Path, *, max_parse_workers: int | None = None):
    replay_manager_config = ReplayManagerServiceConfig(
        raw_replay_dir=tmp_path,
        processed_replay_dir=tmp_path / "processed",
    )
    if max_parse_workers is None:
        return WarthogReplayDataGrabberConfig(
            replay_manager_service_config=replay_manager_config,
        )
    return WarthogReplayDataGrabberConfig(
        replay_manager_service_config=replay_manager_config,
        max_parse_workers=max_parse_workers,
    )


def test_replay_grabber_config_defaults_parse_workers_to_four(tmp_path: Path) -> None:
    config = create_config(tmp_path)

    assert config.max_parse_workers == 4


def test_grabber_uses_configured_parse_workers_and_cpu_cap(
    tmp_path: Path, monkeypatch
) -> None:
    config = create_config(tmp_path, max_parse_workers=4)
    manager = SimpleNamespace(
        _raw_replay_dir_path=tmp_path,
        _processed_replay_dir_path=tmp_path / "processed",
    )

    class FakeServiceFactory:
        def get_replay_data_grabber_config(self):
            return config

        def create_logging_service(self):
            pass

        def get_replay_manager_service(self, **kwargs):
            return manager

    monkeypatch.setattr(
        "src.replay_data_grabber.warthog_replay_data_grabber.ServiceFactory",
        FakeServiceFactory,
    )
    monkeypatch.setattr(
        "src.replay_data_grabber.warthog_replay_data_grabber.os.cpu_count",
        lambda: 2,
    )

    grabber = WarthogReplayDataGrabber(
        raw_replay_dir_path=tmp_path,
        processing_mode=ProcessingMode.NEW,
    )

    assert grabber._max_parse_workers == 2
