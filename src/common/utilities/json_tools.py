import json
from pathlib import Path


class JsonTools:
    """
    Utility class for JSON operations.
    """

    @staticmethod
    def load_json(file_path: Path) -> dict:
        """
        Load JSON data from a file with consistent error handling.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to load JSON from {file_path}: {e}")

    @staticmethod
    def save_json(data: dict, file_path: Path, indent: int = 4) -> None:
        """
        Save data to a JSON file with consistent formatting.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=indent, ensure_ascii=True)
