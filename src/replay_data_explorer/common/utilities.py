def hex_to_rgba(hex_string: str, alpha: float = 1.0) -> str:
    """
    Converts hex color string to rgba color string with optional alpha channel transparency
    """
    rgba = tuple([int(hex_string.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)] + [alpha])

    return f"rgba{rgba}"
