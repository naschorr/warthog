import logging

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Optional, TYPE_CHECKING

from src.replay_data_grabber.configuration import ReplayManagerServiceConfig
from src.replay_data_grabber.models import Replay

if TYPE_CHECKING:
    from src.replay_data_grabber.services.replay_parser_service import ReplayParserService


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

    RAW_REPLAY_FILE_SUFFIX = ".wrpl"
    PROCESSED_REPLAY_FILE_PREFIX = "replay_"
    PROCESSED_REPLAY_FILE_SUFFIX = ".json"

    # Lifecycle

    def __init__(self, config: ReplayManagerServiceConfig, *, replay_parser_service: "ReplayParserService"):
        self._config = config

        self._replay_parser_service = replay_parser_service
        self._raw_replay_dir_path = Path(self._config.raw_replay_dir)
        self._processed_replay_dir_path = Path(self._config.processed_replay_dir)
        self._allow_overwrite = self._config.allow_overwrite

        self._loaded_session_ids, self._loaded_replays = self.load_processed_replays()

    # Properties

    @property
    def loaded_replays(self) -> dict[str, Replay]:
        """Get a copy of all loaded replays."""
        return {session_id: replay for session_id, (path, replay) in self._loaded_replays.items()}

    # Methods

    def load_processed_replay(self, replay_file_path: Path) -> Replay:
        """
        Load a processed replay from a JSON file.

        Args:
            replay_file_path: Path to the processed replay JSON file

        Returns:
            Replay object parsed from the file

        Raises:
            Exception if the file cannot be read or parsed
        """
        with open(replay_file_path, "r", encoding="utf-8") as f:
            replay = Replay.model_validate_json(f.read())
            return replay

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
            candidate_files = list(self._processed_replay_dir_path.glob("*.json"))
            candidate_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            for file_path in candidate_files:
                try:
                    replay = self.load_processed_replay(file_path)
                    session_ids.add(replay.session_id)
                    loaded_replays[replay.session_id] = (file_path, replay)
                except Exception as e:
                    logger.debug(f"Could not parse {file_path} as replay JSON: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error loading recent replay sessions: {e}")

        logger.info(f"Loaded {len(session_ids)} recent replay sessions from {self._processed_replay_dir_path}")
        return (session_ids, loaded_replays)

    def discover_raw_replay_files(self, replay_directory: Optional[Path] = None) -> dict[Path, str]:
        """
        Discover all replay files in a given directory.

        Args:
            replay_directory: Directory to search for replay files

        Returns:
            Dictionary of replay paths to their session IDs for all replay files found in the directory
        """

        if replay_directory is None:
            replay_directory = self._raw_replay_dir_path
        if replay_directory is None or not replay_directory.exists():
            raise ValueError(f"Replay directory does not exist: {replay_directory}")

        replay_files = list(replay_directory.glob(f"*{self.RAW_REPLAY_FILE_SUFFIX}"))
        replay_files.sort(key=lambda path: path.stat().st_birthtime, reverse=True)

        replay_file_session_map = {}
        for replay_file in replay_files:
            try:
                session_id = self._replay_parser_service.get_session_id_from_replay_file(replay_file)
                replay_file_session_map[replay_file] = session_id
            except Exception as e:
                logger.debug(f"Could not get session ID from {replay_file}: {e}")

        return replay_file_session_map

    def discover_processed_replay_files(self, replay_directory: Optional[Path] = None) -> dict[Path, str]:
        """
        Discover all processed replay JSON files in a given directory.

        Args:
            replay_directory: Directory to search for processed replay files
        Returns:
            Dictionary of replay paths to their session IDs for all replay files found in the directory
        """
        if replay_directory is None:
            replay_directory = self._processed_replay_dir_path
        if replay_directory is None or not replay_directory.exists():
            raise ValueError(f"Replay directory does not exist: {replay_directory}")

        replay_files = list(
            replay_directory.glob(f"{self.PROCESSED_REPLAY_FILE_PREFIX}*{self.PROCESSED_REPLAY_FILE_SUFFIX}")
        )
        replay_files.sort(key=lambda path: path.stat().st_birthtime, reverse=True)
        replay_file_session_map = {}
        for replay_file in replay_files:
            try:
                replay = self.load_processed_replay(replay_file)
                replay_file_session_map[replay_file] = replay.session_id
            except Exception as e:
                logger.debug(f"Could not get session ID from {replay_file}: {e}")

        return replay_file_session_map

    def does_replay_exist(self, replay: Replay) -> bool:
        """
        Check if a replay's session ID has already been processed.

        Args:
            replay: Replay object to check

        Returns:
            True if this replay has been seen before
        """
        return replay.session_id in self._loaded_session_ids

    def parse_raw_replay_file(self, replay_file_path: Path) -> Replay:
        """
        Parse a single raw replay file and return the Replay object.

        Args:
            replay_file_path: Path to the .wrpl replay file

        Returns:
            Parsed Replay object
        """
        if not replay_file_path.exists():
            raise FileNotFoundError(f"Replay file does not exist: {replay_file_path}")

        if not replay_file_path.suffix.lower() == self.RAW_REPLAY_FILE_SUFFIX:
            raise ValueError(f"File is not a .wrpl replay file: {replay_file_path}")

        try:
            logger.info(f"Parsing replay file: {replay_file_path}")
            replay = self._replay_parser_service.parse_replay_file(replay_file_path)
            return replay

        except Exception as e:
            raise ValueError(f"Error parsing replay file {replay_file_path}: {e}")

    def ingest_raw_replay_file(self, replay_file_path: Path) -> Optional[Replay]:
        """
        Load and parse a single replay file.

        Args:
            replay_file_path: Path to the .wrpl file

        Returns:
            Parsed Replay object or None if parsing failed
        """
        try:
            replay = self.parse_raw_replay_file(replay_file_path)

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
        Load and parse replay files from a directory.

        Args:
            replay_directory: Directory containing .wrpl files
            only_new: If True, skip replays whose session IDs already exist in processed output.

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

    def store_replay(self, replay: Replay, *, overwrite: bool = False) -> Path:
        """
        Store a replay to the processed replay directory.

        Args:
            replay: Replay object to store
            overwrite: Whether to overwrite the replay if it already exists.

        Returns:
            Path to the stored replay file
        """
        # Ensure the processed replay directory exists
        self._processed_replay_dir_path.mkdir(parents=True, exist_ok=True)

        allow_overwrite = self._allow_overwrite or overwrite
        if allow_overwrite or not self.does_replay_exist(replay):
            replay_file_path = replay.save_to_file(self._processed_replay_dir_path)
            logger.info(f"Stored replay to {replay_file_path}")
            return replay_file_path
        else:
            logger.warning(f"Replay {replay.session_id} already exists, skipping storage")
            path, _ = self._loaded_replays[replay.session_id]
            return path
