from pathlib import Path
from typing import Optional, TYPE_CHECKING

from src.replay_data_grabber.models import Replay

if TYPE_CHECKING:
    from src.replay_data_grabber.services.replay_parser_service import ReplayParserService


_replay_parser_service: Optional["ReplayParserService"] = None


def initialize_replay_parser_worker() -> None:
    global _replay_parser_service

    from src.common.factories import ServiceFactory

    _replay_parser_service = ServiceFactory().get_replay_parser_service()


def parse_replay_file_in_worker(file_path: str) -> Replay:
    replay_parser_service = _replay_parser_service
    if replay_parser_service is None:
        initialize_replay_parser_worker()
        replay_parser_service = _replay_parser_service
    if replay_parser_service is None:
        raise RuntimeError("Replay parser worker was not initialized")

    return replay_parser_service.parse_replay_file(Path(file_path))
