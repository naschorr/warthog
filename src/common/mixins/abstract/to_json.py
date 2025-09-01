from abc import ABC, abstractmethod


class ToJsonMixin(ABC):
    @abstractmethod
    def to_json(self) -> str:
        raise NotImplementedError()
