"""
Models for War Thunder replay data.
"""

from .kill_detail import KillDetail
from .death_detail import DeathDetail
from .deaths import Deaths
from .kills import Kills
from .player import Player
from .replay import Replay

__all__ = ["DeathDetail", "Deaths", "KillDetail", "Kills", "Player", "Replay"]
