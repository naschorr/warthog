from pathlib import Path

from src.common.utilities import get_root_directory


class Validators:

    @staticmethod
    def create_directory_validator(path: Path) -> Path:
        """Ensure the directory exists, creating it if necessary."""
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        elif not path.is_dir():
            raise ValueError(f"Path {path} exists but is not a directory")
        return path

    @staticmethod
    def directory_exists_validator(path: Path) -> Path:
        """Ensure the directory exists."""
        if not path.exists():
            raise ValueError(f"Directory {path} does not exist")
        elif not path.is_dir():
            raise ValueError(f"Path {path} exists but is not a directory")
        return path

    @staticmethod
    def file_exists_validator(path: Path) -> Path:
        """Ensure the file exists."""
        if not path.exists() or not path.is_file():
            raise ValueError(f"File {path} does not exist or is not a file")
        return path

    @staticmethod
    def directory_absolute_validator(path: Path) -> Path:
        """Ensure the directory path is absolute, creating a project-relative path if necessary."""
        if not path.is_absolute():
            path = get_root_directory() / path
        return path
