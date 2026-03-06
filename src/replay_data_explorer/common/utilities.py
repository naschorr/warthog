def get_graph_width(flavor: str = "default") -> int:
    """Return the standard graph width for the given flavor, falling back to the default."""
    from src.replay_data_explorer.configuration.graph_configuration import PLOTLY_GRAPH_WIDTH

    return PLOTLY_GRAPH_WIDTH.get(flavor, PLOTLY_GRAPH_WIDTH["default"])


def hex_to_rgba(hex_string: str, alpha: float = 1.0) -> str:
    """
    Converts hex color string to rgba color string with optional alpha channel transparency
    """
    rgba = tuple([int(hex_string.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)] + [alpha])

    return f"rgba{rgba}"
