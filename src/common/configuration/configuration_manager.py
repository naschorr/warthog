import logging

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Optional

from src.common.utilities import get_root_directory
from src.common.configuration import ConfigurationLoader, WarthogConfig


class ConfigurationManager:

    ## Statics

    _SINGLETON_INSTANCE = None

    ## Lifecycle

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize the configuration manager."""

        # Prevent creating multiple instances directly
        if ConfigurationManager._SINGLETON_INSTANCE is not None:
            logger.warning(
                f"{self.__class__.__name__} is a singleton! Use {self.__class__.__name__}.get_instance() instead."
            )
            return
        else:
            ConfigurationManager._SINGLETON_INSTANCE = self

        # Set the configuration directory
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = get_root_directory() / "src"

        # Init the config loader, load the configuration, and instantiate the final config object
        self._configuration_loader = ConfigurationLoader()
        self._config_data = self._configuration_loader.load_config(self.config_dir)
        self._config = WarthogConfig(**self._config_data)

    @property
    def config(self) -> WarthogConfig:
        """Get the application configuration."""
        return self._config

    ## Methods

    @classmethod
    def _get_instance(cls, config_dir: Optional[str] = None):
        """Get or create the singleton instance of ConfigurationManager."""
        if cls._SINGLETON_INSTANCE is None:
            cls._SINGLETON_INSTANCE = cls(config_dir)
        return cls._SINGLETON_INSTANCE


def get_config(config_dir: Optional[str] = None) -> WarthogConfig:
    """
    One-stop shop to get the application configuration.
    """
    return ConfigurationManager._get_instance(config_dir).config
