import json
from abc import ABC
from typing import Type, TypeVar

T = TypeVar("T", bound="FromJsonMixin")


class FromJsonMixin(ABC):
    @classmethod
    def from_json(cls: Type[T], json_data: str) -> T:
        """Create a class instance from JSON data."""
        data = json.loads(json_data)
        return cls(**data)

    @classmethod
    def from_json_file(cls: Type[T], file_path: str) -> T:
        """Create a class instance from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = f.read()
        return cls.from_json(json_data)
