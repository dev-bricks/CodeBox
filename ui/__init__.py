# CodeBox UI Module
from .main_window import MainWindow
from .problems_panel import ProblemsPanel
from .plugins_dialog import PluginsDialog
from .shortcuts_dialog import ShortcutsDialog
from .search_dialog import FindReplaceDialog
from .diff_viewer import DiffViewerDialog

__all__ = [
    "MainWindow",
    "ProblemsPanel",
    "PluginsDialog",
    "ShortcutsDialog",
    "FindReplaceDialog",
    "DiffViewerDialog",
]
