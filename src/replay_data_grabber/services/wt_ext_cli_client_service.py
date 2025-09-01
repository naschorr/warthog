import logging

logger = logging.getLogger(__name__)

import os
import subprocess
import json
from pathlib import Path
from typing import Optional

from src.common.utilities import get_root_directory


class WtExtCliClientService:
    """
    Service for managing the external wt_ext_cli client for extracting data from War Thunder .blk files.
    """

    # Statics

    ROOT_DIR = get_root_directory()

    # Lifecycle

    def __init__(self, wt_ext_cli_path: Optional[Path] = None):
        if wt_ext_cli_path and wt_ext_cli_path.exists():
            self._wt_ext_cli_path = wt_ext_cli_path
        else:
            self._wt_ext_cli_path = self._find_wt_ext_cli(self.ROOT_DIR)

    # Methods

    def _find_wt_ext_cli(self, recursive_search_root: Path) -> Path:
        """
        Find the wt_ext_cli executable in the specified directory, traversing subdirectories.
        """
        # Shortcut, it's recommended to install wt_ext_cli somewhere inside in root/src/bin
        shortcut_search_root = self.ROOT_DIR / "src" / "bin"
        if shortcut_search_root.exists():
            for root, dirs, files in os.walk(shortcut_search_root):
                for filename in files:
                    if "wt_ext_cli" in filename:
                        wt_ext_cli_path = Path(root) / filename
                        logger.info(f"Found wt_ext_cli at {wt_ext_cli_path}")
                        return wt_ext_cli_path

        # The file might be somewhere else, so search everything inside the root
        for root, dirs, files in os.walk(recursive_search_root):
            for filename in files:
                if "wt_ext_cli" in filename:
                    wt_ext_cli_path = Path(root) / filename
                    logger.info(f"Found wt_ext_cli at {wt_ext_cli_path}")
                    return wt_ext_cli_path

        raise FileNotFoundError(
            "wt_ext_cli executable not found. Please download and place it in the 'src/bin' directory."
        )

    def unpack_raw_blk(self, data: bytes) -> dict:
        """
        Unpack raw blk data using the wt_ext_cli executable and return the processed data as a JSON dictionary.
        """
        try:
            result = subprocess.run(
                [
                    self._wt_ext_cli_path,
                    "--unpack_raw_blk",
                    "--stdout",
                    "--format",
                    "Json",
                    "--stdin",
                ],
                input=data,
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8", errors="ignore") if result.stderr else "Unknown error"
                raise RuntimeError(f"wt_ext_cli failed with return code {result.returncode}: {error_msg}")

            return json.loads(result.stdout)

        except subprocess.TimeoutExpired:
            raise RuntimeError("wt_ext_cli timed out after 30 seconds")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse wt_ext_cli JSON output: {e}")
