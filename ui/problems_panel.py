"""Problems panel for LSP and save-triggered linter diagnostics."""

from __future__ import annotations

from typing import Iterable, Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class ProblemsPanel(QWidget):
    """Compact, keyboard-accessible list of diagnostics."""

    problemActivated = Signal(object)

    HEADERS = ["Quelle", "Datei", "Zeile", "Spalte", "Schwere", "Meldung"]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(len(self.HEADERS))
        self.tree.setHeaderLabels(self.HEADERS)
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setAccessibleName("Problems-Panel")
        self.tree.setAccessibleDescription(
            "LSP- und Linter-Diagnosen. Doppelklick springt zur betroffenen Stelle."
        )
        self.tree.itemDoubleClicked.connect(self._activate_item)
        layout.addWidget(self.tree)

    @property
    def problem_count(self) -> int:
        return self.tree.topLevelItemCount()

    def set_problems(self, problems: Iterable[Mapping]):
        self.tree.clear()
        for problem in problems:
            source = str(problem.get("source") or "LSP")
            path = str(problem.get("path") or "")
            line = int(problem.get("line") or 1)
            col = int(problem.get("col") or 1)
            severity = str(problem.get("severity") or "error")
            message = str(problem.get("message") or "")
            item = QTreeWidgetItem([
                source,
                path,
                str(line),
                str(col),
                severity,
                message,
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, dict(problem))
            self.tree.addTopLevelItem(item)
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(2)
        self.tree.resizeColumnToContents(3)

    def _activate_item(self, item: QTreeWidgetItem, _column: int):
        problem = item.data(0, Qt.ItemDataRole.UserRole)
        if problem:
            self.problemActivated.emit(problem)

