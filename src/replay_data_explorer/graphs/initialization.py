import json
import sys
import os
import datetime
from pathlib import Path
from collections import Counter, OrderedDict, defaultdict
from typing import Optional
from enum import Enum

# Import third-party libraries
import pandas as pd
import numpy as np

# Import Plotly for interactive visualizations
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

# Import project modules
from src.common.configuration import get_config
from src.common.utilities import get_root_directory
from src.common.enums import BattleType, Country, VehicleType
from src.common.models.vehicle_models import Vehicle
from src.common.factories import ServiceFactory
from src.replay_data_explorer.enums import BattleRatingTier
from src.replay_data_explorer.services import BattleRatingTierClassifier, DataFilterer, DataLoaders, TitleBuilder
from src.replay_data_explorer.common import hex_to_rgba
from src.replay_data_explorer.configuration.graph_configuration import *
from src.replay_data_grabber.models import Player

# Initialize configuration
config = get_config().replay_data_explorer_config

# Initialize replay_data_grabber services
service_factory = ServiceFactory()
vehicle_service = service_factory.get_vehicle_service()
replay_manager_service = service_factory.get_replay_manager_service()

# Initialize replay_data_explorer services and utility functions
battle_rating_tier_classifier = BattleRatingTierClassifier()
data_filterer = DataFilterer()
data_loaders = DataLoaders(replay_manager_service)
title_builder = TitleBuilder()
