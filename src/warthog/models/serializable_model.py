from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from src.mixins.abstract.to_json import ToJsonMixin
from src.mixins.from_json import FromJsonMixin

# Type variable for model classes
T = TypeVar("T", bound=BaseModel)


class SerializableModel(BaseModel, ToJsonMixin, FromJsonMixin):
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
