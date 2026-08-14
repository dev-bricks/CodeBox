"""Headless UI checks for the integrated Problems panel."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.problems_panel import ProblemsPanel


def _app():
    return QApplication.instance() or QApplication([])


def test_problems_panel_lists_and_activates_diagnostics():
    _app()
    panel = ProblemsPanel()
    activated = []
    panel.problemActivated.connect(activated.append)
    problem = {
        "source": "ruff",
        "path": "sample.py",
        "line": 2,
        "col": 4,
        "severity": "warning",
        "message": "unused import",
    }
    panel.set_problems([problem])
    assert panel.problem_count == 1
    assert panel.tree.topLevelItem(0).text(5) == "unused import"
    panel.tree.itemDoubleClicked.emit(panel.tree.topLevelItem(0), 0)
    assert activated == [problem]
    panel.close()

