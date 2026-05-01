"""Central application metadata for CodeBox."""

from pathlib import Path


APP_NAME = "CodeBox"
APP_VERSION = "0.1.0"
DEFAULT_WINDOW_TEMPLATE = f"{APP_NAME} v{APP_VERSION}"
__version__ = APP_VERSION


def format_window_title(current_file: str | Path | None = None) -> str:
    """Build a consistent window title for the main window."""
    if not current_file:
        return DEFAULT_WINDOW_TEMPLATE
    return f"{DEFAULT_WINDOW_TEMPLATE} - {Path(current_file).name}"
