from concurrent.futures import Future
from pathlib import Path

from src.replay_data_grabber.models import Replay
from src.replay_data_grabber.warthog_replay_data_grabber import (
    WarthogReplayDataGrabber,
)


class InlineExecutor:
    def __init__(self, *, max_workers: int, initializer) -> None:
        self.max_workers = max_workers
        self.initializer = initializer
        self.submitted_paths: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def submit(self, worker, file_path: str) -> Future:
        self.submitted_paths.append(file_path)
        future = Future()
        try:
            future.set_result(worker(file_path))
        except Exception as error:
            future.set_exception(error)
        return future


class FakeReplayManager:
    def __init__(self, raw_replays: dict[Path, str], processed_replays: dict[Path, str] | None = None):
        self.raw_replays = raw_replays
        self.processed_replays = processed_replays or {}
        self.stored: list[tuple[Replay, bool]] = []

    def discover_raw_replay_files(self, replay_directory: Path) -> dict[Path, str]:
        return self.raw_replays

    def discover_processed_replay_files(self, replay_directory: Path) -> dict[Path, str]:
        return self.processed_replays

    def store_replay(self, replay: Replay, *, overwrite: bool = False) -> Path:
        self.stored.append((replay, overwrite))
        return Path(replay.session_id)


def make_grabber(manager: FakeReplayManager) -> WarthogReplayDataGrabber:
    grabber = object.__new__(WarthogReplayDataGrabber)
    grabber._max_parse_workers = 2
    grabber._replay_manager_service = manager
    grabber._processed_replay_dir_path = Path("processed")
    return grabber


def test_parallel_parse_stores_successes_in_input_order_and_continues_after_failure(monkeypatch) -> None:
    raw_files = {
        Path("first.wrpl"): "duplicate-session",
        Path("bad.wrpl"): "session-2",
        Path("last.wrpl"): "duplicate-session",
    }
    manager = FakeReplayManager(raw_files)
    grabber = make_grabber(manager)
    executor = InlineExecutor
    monkeypatch.setattr(
        "src.replay_data_grabber.warthog_replay_data_grabber.ProcessPoolExecutor",
        executor,
    )

    def parse(file_path: str) -> Replay:
        if file_path == "bad.wrpl":
            raise ValueError("invalid replay")
        return Replay(
            session_id="duplicate-session",
            loc_name=Path(file_path).stem,
        )

    monkeypatch.setattr(
        "src.replay_data_grabber.warthog_replay_data_grabber.parse_replay_file_in_worker",
        parse,
    )

    grabber.parse_all_replay_files(Path("raw"))

    assert [replay.session_id for replay, _ in manager.stored] == [
        "duplicate-session",
        "duplicate-session",
    ]
    assert [replay.loc_name for replay, _ in manager.stored] == ["first", "last"]
    assert all(overwrite for _, overwrite in manager.stored)


def test_new_replay_processing_filters_processed_sessions(monkeypatch) -> None:
    raw_files = {
        Path("old.wrpl"): "already-processed",
        Path("new.wrpl"): "new-session",
        Path("newer.wrpl"): "newer-session",
    }
    manager = FakeReplayManager(
        raw_files,
        processed_replays={Path("processed.json"): "already-processed"},
    )
    grabber = make_grabber(manager)
    submitted_paths: list[str] = []

    class RecordingExecutor(InlineExecutor):
        def __init__(self, *, max_workers: int, initializer) -> None:
            super().__init__(max_workers=max_workers, initializer=initializer)

        def submit(self, worker, file_path: str) -> Future:
            self.submitted_paths.append(file_path)
            submitted_paths.append(file_path)
            future = Future()
            future.set_result(worker(file_path))
            return future

    monkeypatch.setattr(
        "src.replay_data_grabber.warthog_replay_data_grabber.ProcessPoolExecutor",
        RecordingExecutor,
    )
    monkeypatch.setattr(
        "src.replay_data_grabber.warthog_replay_data_grabber.parse_replay_file_in_worker",
        lambda file_path: Replay(session_id=Path(file_path).stem + "-session"),
    )

    grabber.parse_new_replay_files(Path("raw"), Path("processed"))

    assert submitted_paths == ["new.wrpl", "newer.wrpl"]
    assert [(replay.session_id, overwrite) for replay, overwrite in manager.stored] == [
        ("new-session", False),
        ("newer-session", False),
    ]
