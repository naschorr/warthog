import logging

logging.getLogger(__name__)

from typing import TypeVar, Generic

from pydantic import BaseModel, ValidationError

# Type variable for the configuration model
T = TypeVar("T", bound=BaseModel)


class KwargConfiguration(Generic[T]):
    """
    Base class for classes that should be configured via Pydantic models, and optional kwarg overrides.

    Kwargs provided during initialization will overwrite corresponding attributes in the model.
    Uses Pydantic's validation to ensure all updates are valid.
    """

    # Lifecycle

    def __init__(self, config: T, **kwargs):
        self._config = config
        self._kwargs = kwargs

        if self._kwargs:
            self._overwrite_config_with_kwargs(**self._kwargs)

    # Methods

    def _overwrite_config_with_kwargs(self, **kwargs):
        """
        Overwrite config attributes with kwargs, using Pydantic validation.
        """
        # Get current config as dict
        current_data = self._config.model_dump()

        # Update with kwargs, but only for fields that exist in the model
        valid_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in self._config.__class__.model_fields and value is not None
        }

        if valid_kwargs:
            current_data.update(valid_kwargs)

            # Create new model instance with validation
            try:
                self._config = self._config.__class__.model_validate(current_data)
            except ValidationError as e:
                raise ValueError(f"Invalid configuration values: {e}")
