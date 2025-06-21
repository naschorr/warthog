import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, TypeVar, Type

from pydantic import BaseModel

# Type variable for model classes
T = TypeVar('T', bound=BaseModel)


class SerializableModel(BaseModel):
    """Base model class with serialization capabilities."""

    def to_json(self) -> str:
        """Convert the model to a JSON string."""
        return self.model_dump_json(indent=2)

    def save_to_file(self, directory: Path) -> Path:
        """
        Save the model to a JSON file in the specified directory.
        Must be implemented by subclasses with appropriate filename logic.
        """
        raise NotImplementedError("Subclasses must implement save_to_file")

    @classmethod
    def from_json(cls: Type[T], json_data: str) -> T:
        """Create a model instance from JSON data."""
        data = json.loads(json_data)
        return cls(**data)

    @classmethod
    def load_from_file(cls: Type[T], file_path: Path) -> T:
        """Load a model instance from a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())