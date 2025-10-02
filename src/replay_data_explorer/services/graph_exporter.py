import os
from pathlib import Path
from typing import Optional
from datetime import datetime

import plotly.graph_objects as go
import plotly.io as pio

from src.replay_data_explorer.configuration.configuration_models import GraphExportConfig


class GraphExporter:
    """
    Utility class for exporting Plotly graphs to files.
    """

    def __init__(self, *, graph_export_config: GraphExportConfig):
        """
        Initialize the graph exporter.

        Args:
            graph_export_config: Configuration for graph export.
        """
        self._graph_export_config = graph_export_config
        self._export_png = graph_export_config.enable_png_export

        # Create output directory if it doesn't exist
        self._graph_export_config.output_directory_path.mkdir(parents=True, exist_ok=True)

        # Set up image export engine (kaleido is recommended)
        if self._export_png:
            pio.kaleido.scope.default_format = "png"

    def save_as_png(self, graph: go.Figure, filename: str) -> Optional[Path]:
        """
        Save a Plotly figure as PNG.

        Args:
            graph: Plotly figure to save
            filename: Name of the file (without extension)

        Returns:
            Path to saved file or None if failed
        """
        if not self._export_png:
            return None

        filepath = self._graph_export_config.output_directory_path / f"{filename}.png"
        graph.write_image(
            str(filepath),
            format="png",
            width=self._graph_export_config.png_width,
            height=self._graph_export_config.png_height,
            scale=self._graph_export_config.png_scale,
        )

        return filepath
