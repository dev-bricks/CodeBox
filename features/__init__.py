# CodeBox Features Module
# Contains: LSP, Linter, PluginManager, Terminal, ProjectView, ThemeManager, RemoteEditor

from .lsp_client import LSPManager, LSPClient
from .linter import LinterManager
from .plugin_manager import PluginManager, PluginInfo
from .terminal import TerminalWidget
from .project_view import ProjectView
from .theme_manager import apply_theme, load_theme, get_available_themes

__all__ = [
    "LSPManager",
    "LSPClient",
    "LinterManager",
    "PluginManager",
    "PluginInfo",
    "TerminalWidget",
    "ProjectView",
    "apply_theme",
    "load_theme",
    "get_available_themes",
]
