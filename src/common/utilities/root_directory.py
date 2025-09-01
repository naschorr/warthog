from pathlib import Path


def get_root_directory() -> Path:
    """Get the root directory of the project."""
    return Path(__file__).parent.parent.parent.parent.resolve()
