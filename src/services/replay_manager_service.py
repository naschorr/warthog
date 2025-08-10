import logging

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Optional

from utilities import get_root_directory
from models.replay_models import Replay
from services.replay_parser_service import ReplayParserService


class ReplayManagerService:
    """
    Manages loading, parsing, and caching of War Thunder replay data.

    This service handles the lifecycle of replay files including:
    - Loading replay files from directories
    - Parsing .wrpl files into Replay objects
    - Caching parsed replays to avoid re-processing
    - Tracking recent sessions to avoid duplicates
    """

    # Statics

    REPLAY_FILE_SUFFIX = ".wrpl"

    # Lifecycle

    def __init__(
        self,
        replay_parser_service: ReplayParserService,
        *,
        raw_replay_directory: Optional[Path] = None,
        processed_replay_directory: Path,
        allow_overwrite: bool = False,
    ):
        """
        Initialize the replay manager service.

        Args:
            replay_parser_service: Service for parsing .wrpl files
            processed_replay_directory: Directory containing processed replay files
        """
        self._replay_parser_service = replay_parser_service
        self._allow_overwrite = allow_overwrite

        # Get the raw replay directory
        if raw_replay_directory:
            if raw_replay_directory.is_absolute():
                self._raw_replay_directory = raw_replay_directory
            else:
                self._raw_replay_directory = get_root_directory() / raw_replay_directory
            assert raw_replay_directory.exists(), f"Raw replay directory does not exist: {raw_replay_directory}"
            assert raw_replay_directory.is_dir(), f"Raw replay directory is not a directory: {raw_replay_directory}"
        else:
            # The directory will be provided later
            self._raw_replay_directory = raw_replay_directory

        # Get the processed replay directory
        if processed_replay_directory.is_absolute():
            self._processed_replay_directory = processed_replay_directory
        else:
            self._processed_replay_directory = get_root_directory() / processed_replay_directory
        assert processed_replay_directory.exists(), f"Replay directory does not exist: {processed_replay_directory}"
        assert processed_replay_directory.is_dir(), f"Replay directory is not a directory: {processed_replay_directory}"

        self._loaded_session_ids, self._loaded_replays = self.load_processed_replays()

    # Properties

    @property
    def loaded_replays(self) -> dict[str, Replay]:
        """Get a copy of all loaded replays."""
        return {session_id: replay for session_id, (path, replay) in self._loaded_replays.items()}

    # Methods

    def load_processed_replays(self) -> tuple[set[str], dict[str, tuple[Path, Replay]]]:
        """
        Load recent session IDs from existing JSON files in the output directory.

        Returns:
            Tuple containing session ids for all loaded replays and a dictionary of session ids to Replay objects.
        """
        session_ids = set()
        loaded_replays = {}
        try:
            # Look for JSON files that might be replay-generated
            candidate_files = list(self._processed_replay_directory.glob("*.json"))
            candidate_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            for file_path in candidate_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        replay = Replay.model_validate_json(f.read())

                        session_ids.add(replay.session_id)
                        loaded_replays[replay.session_id] = (file_path, replay)
                except Exception as e:
                    logger.debug(f"Could not parse {file_path} as replay JSON: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error loading recent replay sessions: {e}")

        logger.info(f"Loaded {len(session_ids)} recent replay sessions from {self._processed_replay_directory}")
        return (session_ids, loaded_replays)

    def discover_raw_replay_files(self, replay_directory: Optional[Path] = None) -> list[Path]:
        """
        Discover all replay files in a given directory.

        Args:
            replay_directory: Directory to search for replay files

        Returns:
            List of Paths to replay files found in the directory
        """

        if replay_directory is None:
            replay_directory = self._raw_replay_directory
        if replay_directory is None or not replay_directory.exists():
            raise ValueError(f"Replay directory does not exist: {replay_directory}")

        return list(replay_directory.glob(f"*{self.REPLAY_FILE_SUFFIX}"))

    def does_replay_exist(self, replay: Replay) -> bool:
        """
        Check if a replay's session ID has already been processed.

        Args:
            replay: Replay object to check

        Returns:
            True if this replay has been seen before
        """
        return replay.session_id in self._loaded_session_ids

    def ingest_raw_replay_file(self, replay_file_path: Path) -> Optional[Replay]:
        """
        Load and parse a single replay file.

        Args:
            replay_file_path: Path to the .wrpl file

        Returns:
            Parsed Replay object or None if parsing failed
        """
        if not replay_file_path.exists():
            logger.error(f"Replay file does not exist: {replay_file_path}")
            return None

        if not replay_file_path.suffix.lower() == self.REPLAY_FILE_SUFFIX:
            logger.warning(f"File is not a .wrpl replay file: {replay_file_path}")
            return None

        try:
            logger.info(f"Parsing replay file: {replay_file_path}")
            replay = self._replay_parser_service.parse_replay_file(replay_file_path)

            if replay:
                logger.debug(f"Loaded replay for {replay_file_path.name}")
                # Don't overwrite existing replays unless allowed
                if self._allow_overwrite or not self.does_replay_exist(replay):
                    self._loaded_session_ids.add(replay.session_id)
                    self._loaded_replays[replay.session_id] = (replay_file_path, replay)

            return replay

        except Exception as e:
            logger.error(f"Error parsing replay file {replay_file_path}: {e}")
            return None

    def ingest_raw_replay_files_from_directory(self, replay_directory: Path) -> dict[str, Replay]:
        """
        Load and parse all replay files from a directory.

        Args:
            replay_directory: Directory containing .wrpl files

        Returns:
            Dictionary mapping of session IDs to Replay objects from replays loaded from the directory
        """
        if not replay_directory.exists():
            logger.error(f"Replay directory does not exist: {replay_directory}")
            return {}

        if not replay_directory.is_dir():
            logger.error(f"Path is not a directory: {replay_directory}")
            return {}

        replay_files = self.discover_raw_replay_files(replay_directory)
        if not replay_files:
            logger.warning(f"No replay files found in {replay_directory}")
            return {}

        logger.info(f"Found {len(replay_files)} replay files in {replay_directory}")

        loaded_replays: dict[str, Replay] = {}
        for replay_file in replay_files:
            try:
                replay = self.ingest_raw_replay_file(replay_file)
                if replay:
                    loaded_replays[replay.session_id] = replay
            except Exception as e:
                logger.error(f"Error loading replay file {replay_file}: {e}")
                continue

        logger.info(f"Successfully loaded {len(loaded_replays)} replay files from {replay_directory}")
        return loaded_replays

    def store_replay(self, replay: Replay) -> Path:
        """
        Store a replay to the processed replay directory.

        Args:
            replay: Replay object to store

        Returns:
            Path to the stored replay file
        """
        # Ensure the processed replay directory exists
        self._processed_replay_directory.mkdir(parents=True, exist_ok=True)

        # Save the replay to a file
        if self._allow_overwrite or not self.does_replay_exist(replay):
            replay_file_path = replay.save_to_file(self._processed_replay_directory)
            logger.info(f"Stored replay to {replay_file_path}")
            return replay_file_path
        else:
            logger.warning(f"Replay {replay.session_id} already exists, skipping storage")
            path, _ = self._loaded_replays[replay.session_id]
            return path

        return None
