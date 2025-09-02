from pathlib import Path
from typing import Optional

from src.common.utilities import JsonTools, get_root_directory


class ConfigurationLoader:

    # Statics

    DEV = "dev"  # Configuration naming strings
    PROD = "prod"
    CONFIG = "config"
    CONFIG_NAME = "config.json"  # The name of the config file
    PROD_CONFIG_NAME = "config.prod.json"  # The name of the prod config file
    DEV_CONFIG_NAME = "config.dev.json"  # The name of the dev config file

    # Methods

    @staticmethod
    def _load_config_chunks(directory_path: Optional[Path] = None) -> dict:
        """
        Loads configuration data from the given directory (or the app's root if not provided) into a dictionary. The
        expected prod, dev, and config configuration files are loaded separately and combined into the same dict under
        different keys ("dev", "prod", "config").
        """

        path = directory_path or get_root_directory()
        config = {}

        dev_config_path = Path.joinpath(path, ConfigurationLoader.DEV_CONFIG_NAME)
        if dev_config_path.exists():
            config[ConfigurationLoader.DEV] = JsonTools.load_json(dev_config_path)

        prod_config_path = Path.joinpath(path, ConfigurationLoader.PROD_CONFIG_NAME)
        if prod_config_path.exists():
            config[ConfigurationLoader.PROD] = JsonTools.load_json(prod_config_path)

        config_path = Path.joinpath(path, ConfigurationLoader.CONFIG_NAME)
        if config_path.exists():
            config[ConfigurationLoader.CONFIG] = JsonTools.load_json(config_path)

        return config

    @staticmethod
    def load_config(directory_path: Optional[Path] = None) -> dict:
        """
        Parses one or more JSON configuration files to build a dictionary with proper precedence for configuring the program
        """

        root_config_chunks = ConfigurationLoader._load_config_chunks(get_root_directory())

        config_chunks = {}
        if directory_path is not None:
            config_chunks = ConfigurationLoader._load_config_chunks(directory_path)

        ## Build up a configuration hierarchy, allowing for global configuration if desired
        config = root_config_chunks.get(ConfigurationLoader.CONFIG, {})
        config |= config_chunks.get(ConfigurationLoader.CONFIG, {})
        config |= root_config_chunks.get(ConfigurationLoader.PROD, {})
        config |= root_config_chunks.get(ConfigurationLoader.DEV, {})
        config |= config_chunks.get(ConfigurationLoader.PROD, {})
        config |= config_chunks.get(ConfigurationLoader.DEV, {})

        return config
