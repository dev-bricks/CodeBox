#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrierter Git Diff-Viewer für CodeBox.
Ermöglicht den visuellen Vergleich von Dateiänderungen direkt in der IDE:
- Unified Diff (Vereinheitlicht) mit Syntax-Hervorhebung
- Side-by-Side Diff (Nebeneinander) mit synchronem Scrollen
- Dateiauswahl (alle geänderten Dateien oder Einzelauswahl)
- Staged vs. Unstaged (Arbeitsbaum) Umschaltung
- Chunk-Navigation (Vorherige / Nächste Änderung)
- Direktsprung in den Editor
- Vollständige Barrierefreiheit (WCAG-Kontraste, Screenreader-Attribute)
"""

from __future__ import annotations

import difflib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from features.git_integration import GitFileStatus, GitRepo
    from ui.main_window import MainWindow

logger = logging.getLogger("CodeBox.DiffViewer")


class DiffHighlighter(QSyntaxHighlighter):
    """Syntax-Highlighter für Unified Diff-Ausgaben mit WCAG-konformen Farben."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_formats()

    def _init_formats(self):
        self.added_format = QTextCharFormat()
        self.added_format.setForeground(QColor("#73c991"))  # Kontrastreich hellgrün
        self.added_format.setBackground(QColor("#16381e"))  # Dunkles Grün

        self.removed_format = QTextCharFormat()
        self.removed_format.setForeground(QColor("#f48771"))  # Kontrastreich hellrot
        self.removed_format.setBackground(QColor("#3e1b1b"))  # Dunkles Rot

        self.hunk_format = QTextCharFormat()
        self.hunk_format.setForeground(QColor("#66d9ef"))  # Cyan
        self.hunk_format.setBackground(QColor("#162738"))  # Dunkles Blau
        self.hunk_format.setFontWeight(QFont.Weight.Bold)

        self.header_format = QTextCharFormat()
        self.header_format.setForeground(QColor("#9da5b4"))  # Muted Grau
        self.header_format.setFontItalic(True)

        self.meta_format = QTextCharFormat()
        self.meta_format.setForeground(QColor("#e5c07b"))  # Goldgelb

    def highlightBlock(self, text: str):
        if not text:
            return

        if text.startswith("+++") or text.startswith("---"):
            self.setFormat(0, len(text), self.header_format)
        elif text.startswith("+"):
            self.setFormat(0, len(text), self.added_format)
        elif text.startswith("-"):
            self.setFormat(0, len(text), self.removed_format)
        elif text.startswith("@@"):
            self.setFormat(0, len(text), self.hunk_format)
        elif (
            text.startswith("diff --git")
            or text.startswith("index ")
            or text.startswith("old mode")
            or text.startswith("new mode")
            or text.startswith("similarity index")
            or text.startswith("rename ")
        ):
            self.setFormat(0, len(text), self.meta_format)


class SideBySideHighlighter(QSyntaxHighlighter):
    """Highlighter für Side-by-Side Diff Zeilen (löschen vs. einfügen)."""

    def __init__(self, mode: str, parent=None):
        super().__init__(parent)
        self.mode = mode  # 'old' (left) oder 'new' (right)
        self.change_format = QTextCharFormat()
        if self.mode == "old":
            self.change_format.setForeground(QColor("#f48771"))
            self.change_format.setBackground(QColor("#3e1b1b"))
        else:
            self.change_format.setForeground(QColor("#73c991"))
            self.change_format.setBackground(QColor("#16381e"))

        self.placeholder_format = QTextCharFormat()
        self.placeholder_format.setForeground(QColor("#555555"))

    def highlightBlock(self, text: str):
        if not text:
            return
        # Zeilen mit Marker [~] oder [+] oder [-]
        if text.startswith("[-]") or (self.mode == "old" and text.startswith("[~]")):
            self.setFormat(0, len(text), self.change_format)
        elif text.startswith("[+]") or (self.mode == "new" and text.startswith("[~]")):
            self.setFormat(0, len(text), self.change_format)
        elif text.startswith("[ ] ") and text[4:].strip() == "":
            self.setFormat(0, len(text), self.placeholder_format)


def compute_side_by_side(
    old_text: str, new_text: str
) -> Tuple[List[str], List[str]]:
    """Berechnet zeilenweise synchronisierte Ansichten für Alt und Neu."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    left_result = []
    right_result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                left_result.append(f"    {old_lines[i]}")
            for j in range(j1, j2):
                right_result.append(f"    {new_lines[j]}")
        elif tag == "delete":
            count = i2 - i1
            for i in range(i1, i2):
                left_result.append(f"[-] {old_lines[i]}")
            for _ in range(count):
                right_result.append("[ ] ")
        elif tag == "insert":
            count = j2 - j1
            for _ in range(count):
                left_result.append("[ ] ")
            for j in range(j1, j2):
                right_result.append(f"[+] {new_lines[j]}")
        elif tag == "replace":
            left_count = i2 - i1
            right_count = j2 - j1
            max_count = max(left_count, right_count)

            for idx in range(max_count):
                if idx < left_count:
                    left_result.append(f"[~] {old_lines[i1 + idx]}")
                else:
                    left_result.append("[ ] ")

                if idx < right_count:
                    right_result.append(f"[~] {new_lines[j1 + idx]}")
                else:
                    right_result.append("[ ] ")

    return left_result, right_result


class DiffViewerDialog(QDialog):
    """Haupt-Dialog für Git Diff-Vergleiche in CodeBox."""

    fileOpenRequested = Signal(Path)

    def __init__(
        self,
        main_window: Optional["MainWindow"] = None,
        repo_root: Optional[Path] = None,
        initial_file: Optional[Path] = None,
        staged: bool = False,
        parent: Optional[QWidget] = None,
    ):
        actual_parent = parent if parent is not None else (main_window if isinstance(main_window, QWidget) else None)
        super().__init__(actual_parent)
        self.main_window = main_window
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.initial_file = initial_file
        self.is_staged = staged
        self.statuses: Dict[str, "GitFileStatus"] = {}
        self._syncing_scroll = False

        self.setWindowTitle("CodeBox - Git Diff-Viewer")
        self.setObjectName("diff_viewer_dialog")
        self.setAccessibleName("Git Diff-Viewer")
        self.setAccessibleDescription("Zeigt Code-Unterschiede zwischen Arbeitsverzeichnis, Staging-Bereich und Git-Repository an")
        self.resize(880, 620)
        self.setMinimumSize(640, 420)

        self._setup_ui()
        self.refresh_diff(select_file=initial_file)

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # ---- Zeile 1: Filter und Optionen ----
        top_bar1 = QHBoxLayout()
        top_bar1.setSpacing(8)

        lbl_file = QLabel("Datei:")
        lbl_file.setToolTip("Zu vergleichende Datei auswählen")
        top_bar1.addWidget(lbl_file)

        self.file_combo = QComboBox()
        self.file_combo.setObjectName("diff_file_combo")
        self.file_combo.setMinimumWidth(260)
        self.file_combo.setToolTip("Wählen Sie eine bestimmte Datei oder das gesamte Repository")
        self.file_combo.setAccessibleName("Geänderte Dateien")
        self.file_combo.setAccessibleDescription("Auswahl der anzuzeigenden Datei für den Git-Diff-Vergleich")
        self.file_combo.currentIndexChanged.connect(self._on_file_selection_changed)
        top_bar1.addWidget(self.file_combo, 1)

        self.staged_checkbox = QCheckBox("Staged (--cached)")
        self.staged_checkbox.setObjectName("diff_staged_checkbox")
        self.staged_checkbox.setChecked(self.is_staged)
        self.staged_checkbox.setToolTip("Zeigt Änderungen im Staging-Bereich (Index) anstelle des Arbeitsbaums")
        self.staged_checkbox.setAccessibleName("Nur gestagte Änderungen anzeigen")
        self.staged_checkbox.setAccessibleDescription("Schaltet zwischen Arbeitsverzeichnis und Staging-Bereich für den Diff-Vergleich um")
        self.staged_checkbox.toggled.connect(self._on_staged_toggled)
        top_bar1.addWidget(self.staged_checkbox)

        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("diff_mode_combo")
        self.mode_combo.addItem("Vereinheitlicht (Unified)", "unified")
        self.mode_combo.addItem("Nebeneinander (Side-by-Side)", "side_by_side")
        self.mode_combo.setToolTip("Ansichtsmodus umschalten")
        self.mode_combo.setAccessibleName("Ansichtsmodus")
        self.mode_combo.setAccessibleDescription("Wählt zwischen der vereinheitlichten und der geteilten Diff-Ansicht")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        top_bar1.addWidget(self.mode_combo)

        self.btn_open_editor = QPushButton("Im Editor öffnen")
        self.btn_open_editor.setObjectName("diff_open_btn")
        self.btn_open_editor.setToolTip("Aktuell ausgewählte Datei im Haupteditor öffnen")
        self.btn_open_editor.setAccessibleName("Datei im Editor öffnen")
        self.btn_open_editor.setAccessibleDescription("Öffnet die ausgewählte Datei direkt im CodeBox-Editor")
        self.btn_open_editor.clicked.connect(self.open_selected_in_editor)
        top_bar1.addWidget(self.btn_open_editor)

        root_layout.addLayout(top_bar1)

        # ---- Zeile 2: Navigation & Statistiken ----
        top_bar2 = QHBoxLayout()
        top_bar2.setSpacing(6)

        self.btn_prev = QPushButton("↑ Vorherige Änderung")
        self.btn_prev.setObjectName("diff_prev_btn")
        self.btn_prev.setShortcut(QKeySequence("Alt+Up"))
        self.btn_prev.setToolTip("Springt zur vorherigen geänderten Stelle (Alt+Up)")
        self.btn_prev.setAccessibleName("Vorheriger Diff-Block")
        self.btn_prev.setAccessibleDescription("Springt zur vorherigen Hunk-Markierung im Diff")
        self.btn_prev.clicked.connect(self.prev_chunk)
        top_bar2.addWidget(self.btn_prev)

        self.btn_next = QPushButton("↓ Nächste Änderung")
        self.btn_next.setObjectName("diff_next_btn")
        self.btn_next.setShortcut(QKeySequence("Alt+Down"))
        self.btn_next.setToolTip("Springt zur nächsten geänderten Stelle (Alt+Down)")
        self.btn_next.setAccessibleName("Nächster Diff-Block")
        self.btn_next.setAccessibleDescription("Springt zur nächsten Hunk-Markierung im Diff")
        self.btn_next.clicked.connect(self.next_chunk)
        top_bar2.addWidget(self.btn_next)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.setObjectName("diff_refresh_btn")
        self.btn_refresh.setShortcut(QKeySequence("F5"))
        self.btn_refresh.setToolTip("Diff und Status neu von Git abrufen (F5)")
        self.btn_refresh.setAccessibleName("Diff aktualisieren")
        self.btn_refresh.setAccessibleDescription("Liest den Git-Status und die Diff-Daten neu ein")
        self.btn_refresh.clicked.connect(lambda: self.refresh_diff())
        top_bar2.addWidget(self.btn_refresh)

        top_bar2.addStretch(1)

        self.stats_label = QLabel("Keine Änderungen")
        self.stats_label.setObjectName("diff_stats_label")
        self.stats_label.setAccessibleName("Diff-Statistik")
        self.stats_label.setAccessibleDescription("Zusammenfassung der hinzugefügten und gelöschten Zeilen")
        self.stats_label.setStyleSheet("font-size: 11px; padding: 2px 6px; background: #252526; border-radius: 3px;")
        top_bar2.addWidget(self.stats_label)

        root_layout.addLayout(top_bar2)

        # ---- Zentralbereich: QStackedWidget ----
        self.stack = QStackedWidget()

        # View 0: Unified Diff
        self.unified_view = QPlainTextEdit()
        self.unified_view.setObjectName("diff_unified_view")
        self.unified_view.setReadOnly(True)
        self.unified_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.unified_view.setFont(font)
        self.unified_view.setAccessibleName("Vereinheitlichte Diff-Ansicht")
        self.unified_view.setAccessibleDescription("Zeigt alle Code-Änderungen in einer fortlaufenden Ansicht")
        self.unified_highlighter = DiffHighlighter(self.unified_view.document())
        self.stack.addWidget(self.unified_view)

        # View 1: Side-by-Side Diff
        self.side_by_side_widget = QWidget()
        sbs_layout = QVBoxLayout(self.side_by_side_widget)
        sbs_layout.setContentsMargins(0, 0, 0, 0)
        sbs_layout.setSpacing(4)

        headers_layout = QHBoxLayout()
        self.lbl_base_title = QLabel("Basis (HEAD / Index)")
        self.lbl_base_title.setStyleSheet("color: #f48771; font-weight: bold; font-size: 11px;")
        headers_layout.addWidget(self.lbl_base_title, 1)

        self.lbl_mod_title = QLabel("Aktuell (Arbeitsbaum / Staged)")
        self.lbl_mod_title.setStyleSheet("color: #73c991; font-weight: bold; font-size: 11px;")
        headers_layout.addWidget(self.lbl_mod_title, 1)
        sbs_layout.addLayout(headers_layout)

        self.sbs_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.base_view = QPlainTextEdit()
        self.base_view.setObjectName("diff_base_view")
        self.base_view.setReadOnly(True)
        self.base_view.setFont(font)
        self.base_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.base_view.setAccessibleName("Basis-Code")
        self.base_view.setAccessibleDescription("Ursprünglicher Stand der Datei vor Änderungen")
        self.base_highlighter = SideBySideHighlighter("old", self.base_view.document())
        self.sbs_splitter.addWidget(self.base_view)

        self.mod_view = QPlainTextEdit()
        self.mod_view.setObjectName("diff_modified_view")
        self.mod_view.setReadOnly(True)
        self.mod_view.setFont(font)
        self.mod_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.mod_view.setAccessibleName("Geänderter Code")
        self.mod_view.setAccessibleDescription("Aktueller Stand der Datei mit neuen Änderungen")
        self.mod_highlighter = SideBySideHighlighter("new", self.mod_view.document())
        self.sbs_splitter.addWidget(self.mod_view)

        # Synchrones Scrollen
        self.base_view.verticalScrollBar().valueChanged.connect(self._sync_scroll_from_base)
        self.mod_view.verticalScrollBar().valueChanged.connect(self._sync_scroll_from_mod)

        sbs_layout.addWidget(self.sbs_splitter)
        self.stack.addWidget(self.side_by_side_widget)

        root_layout.addWidget(self.stack, 1)

        # ---- Statusleiste am unteren Rand ----
        bottom_layout = QHBoxLayout()
        self.status_info_label = QLabel(f"Repo: {self.repo_root.name}")
        self.status_info_label.setStyleSheet("color: #888888; font-size: 11px;")
        bottom_layout.addWidget(self.status_info_label)

        bottom_layout.addStretch(1)

        self.btn_close = QPushButton("Schließen")
        self.btn_close.setObjectName("diff_close_btn")
        self.btn_close.setToolTip("Schließt das Diff-Viewer-Fenster (Esc)")
        self.btn_close.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_close)

        root_layout.addLayout(bottom_layout)

    def _sync_scroll_from_base(self, value: int):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.mod_view.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    def _sync_scroll_from_mod(self, value: int):
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.base_view.verticalScrollBar().setValue(value)
        self._syncing_scroll = False

    def _get_git_repo(self) -> Optional["GitRepo"]:
        try:
            from features.git_integration import GitRepo
            repo = GitRepo(str(self.repo_root))
            if repo.is_git_repo():
                return repo
        except Exception as e:
            logger.debug("GitRepo konnte nicht geladen werden: %s", e)
        return None

    def refresh_diff(self, select_file: Optional[Path] = None):
        """Liest Status und Diff neu ein und aktualisiert die Anzeige."""
        repo = self._get_git_repo()
        if not repo:
            self.file_combo.clear()
            self.file_combo.addItem("Kein Git-Repository gefunden", "")
            self.unified_view.setPlainText("Kein gültiges Git-Repository unter: " + str(self.repo_root))
            self.stats_label.setText("Kein Git-Repo")
            self.btn_open_editor.setEnabled(False)
            return

        branch = repo.get_branch()
        self.status_info_label.setText(f"Repo: {self.repo_root.name}  [{branch}]")

        # Status neu abrufen
        self.statuses = repo.get_status()

        # Dateiauswahl aktualisieren
        current_data = self.file_combo.currentData()
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItem("(Alle geänderten Dateien)", "__ALL__")

        target_index = 0
        idx = 1

        # Sortierte Pfade einfügen
        for path_key, status in sorted(self.statuses.items()):
            icon = status.status_icon or "M"
            label = f"[{icon}] {path_key}"
            self.file_combo.addItem(label, path_key)

            if select_file:
                try:
                    rel = select_file.resolve().relative_to(self.repo_root.resolve()).as_posix()
                    if rel == path_key:
                        target_index = idx
                except ValueError:
                    pass
            elif current_data == path_key:
                target_index = idx
            idx += 1

        self.file_combo.setCurrentIndex(target_index)
        self.file_combo.blockSignals(False)

        self._render_current_diff()

    def _on_file_selection_changed(self, _index: int):
        self._render_current_diff()

    def _on_staged_toggled(self, checked: bool):
        self.is_staged = checked
        self._render_current_diff()

    def _on_mode_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        self._render_current_diff()

    def _render_current_diff(self):
        repo = self._get_git_repo()
        if not repo:
            return

        selected_data = self.file_combo.currentData()
        is_all = selected_data in ("__ALL__", None, "")
        filepath = None if is_all else str(selected_data)

        self.btn_open_editor.setEnabled(not is_all)

        mode = self.mode_combo.currentData()

        # Unified Diff holen
        diff_text = repo.get_diff(filepath=filepath, staged=self.is_staged)

        if not diff_text:
            msg = "Keine Unterschiede gefunden (Arbeitsbaum und Index sind identisch)."
            self.unified_view.setPlainText(msg)
            self.base_view.setPlainText("")
            self.mod_view.setPlainText("")
            self.stats_label.setText("Keine Änderungen")
            return

        # Statistiken berechnen
        additions, deletions, chunks = self._calculate_stats(diff_text)
        stats_html = (
            f"<b style='color:#73c991'>+{additions}</b>  "
            f"<b style='color:#f48771'>-{deletions}</b>  |  "
            f"{chunks} Blöcke"
        )
        self.stats_label.setText(stats_html)

        # In Unified View schreiben
        self.unified_view.setPlainText(diff_text)

        # Side-by-Side View vorbereiten wenn aktiv
        if mode == "side_by_side":
            self._render_side_by_side(repo, filepath)

    def _calculate_stats(self, diff_text: str) -> Tuple[int, int, int]:
        additions = 0
        deletions = 0
        chunks = 0
        for line in diff_text.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            elif line.startswith("+"):
                additions += 1
            elif line.startswith("-"):
                deletions += 1
            elif line.startswith("@@"):
                chunks += 1
        return additions, deletions, chunks

    def _render_side_by_side(self, repo: "GitRepo", filepath: Optional[str]):
        """Rendert den Side-by-Side Diff für eine gewählte Datei."""
        if not filepath:
            self.base_view.setPlainText("Bitte wählen Sie eine einzelne Datei für die Side-by-Side-Ansicht aus.")
            self.mod_view.setPlainText("Bitte wählen Sie eine einzelne Datei für die Side-by-Side-Ansicht aus.")
            return

        old_content = ""
        if self.is_staged:
            old_content = repo.get_file_content_at_head(filepath) or ""
            new_content = repo.get_file_content_in_index(filepath) or ""
        else:
            old_content = repo.get_file_content_in_index(filepath)
            if old_content is None:
                old_content = repo.get_file_content_at_head(filepath) or ""

            disk_path = self.repo_root / filepath
            if disk_path.is_file():
                try:
                    new_content = disk_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    new_content = ""
            else:
                new_content = ""

        left_lines, right_lines = compute_side_by_side(old_content, new_content)
        self.base_view.setPlainText("\n".join(left_lines))
        self.mod_view.setPlainText("\n".join(right_lines))

    def next_chunk(self):
        """Springt zur nächsten Hunk-Markierung."""
        current_mode = self.mode_combo.currentData()
        if current_mode == "unified":
            cursor = self.unified_view.textCursor()
            current_line = cursor.blockNumber()
            doc = self.unified_view.document()

            found_block = None
            for i in range(current_line + 1, doc.blockCount()):
                block = doc.findBlockByNumber(i)
                if block.text().startswith("@@"):
                    found_block = block
                    break

            if not found_block:
                for i in range(0, current_line + 1):
                    block = doc.findBlockByNumber(i)
                    if block.text().startswith("@@"):
                        found_block = block
                        break

            if found_block:
                cursor.setPosition(found_block.position())
                self.unified_view.setTextCursor(cursor)
                self.unified_view.centerCursor()
        else:
            cursor = self.mod_view.textCursor()
            current_line = cursor.blockNumber()
            doc = self.mod_view.document()

            found_block = None
            for i in range(current_line + 1, doc.blockCount()):
                block = doc.findBlockByNumber(i)
                if block.text().startswith("[+]") or block.text().startswith("[~]"):
                    found_block = block
                    break

            if not found_block:
                for i in range(0, current_line + 1):
                    block = doc.findBlockByNumber(i)
                    if block.text().startswith("[+]") or block.text().startswith("[~]"):
                        found_block = block
                        break

            if found_block:
                cursor.setPosition(found_block.position())
                self.mod_view.setTextCursor(cursor)
                self.mod_view.centerCursor()
                self.base_view.verticalScrollBar().setValue(self.mod_view.verticalScrollBar().value())

    def prev_chunk(self):
        """Springt zur vorherigen Hunk-Markierung."""
        current_mode = self.mode_combo.currentData()
        if current_mode == "unified":
            cursor = self.unified_view.textCursor()
            current_line = cursor.blockNumber()
            doc = self.unified_view.document()

            found_block = None
            for i in range(current_line - 1, -1, -1):
                block = doc.findBlockByNumber(i)
                if block.text().startswith("@@"):
                    found_block = block
                    break

            if not found_block:
                for i in range(doc.blockCount() - 1, current_line - 1, -1):
                    block = doc.findBlockByNumber(i)
                    if block.text().startswith("@@"):
                        found_block = block
                        break

            if found_block:
                cursor.setPosition(found_block.position())
                self.unified_view.setTextCursor(cursor)
                self.unified_view.centerCursor()
        else:
            cursor = self.mod_view.textCursor()
            current_line = cursor.blockNumber()
            doc = self.mod_view.document()

            found_block = None
            for i in range(current_line - 1, -1, -1):
                block = doc.findBlockByNumber(i)
                if block.text().startswith("[+]") or block.text().startswith("[~]"):
                    found_block = block
                    break

            if not found_block:
                for i in range(doc.blockCount() - 1, current_line - 1, -1):
                    block = doc.findBlockByNumber(i)
                    if block.text().startswith("[+]") or block.text().startswith("[~]"):
                        found_block = block
                        break

            if found_block:
                cursor.setPosition(found_block.position())
                self.mod_view.setTextCursor(cursor)
                self.mod_view.centerCursor()
                self.base_view.verticalScrollBar().setValue(self.mod_view.verticalScrollBar().value())

    def open_selected_in_editor(self):
        """Öffnet die aktuell ausgewählte Datei im Haupteditor."""
        selected_data = self.file_combo.currentData()
        if not selected_data or selected_data == "__ALL__":
            return

        target_path = self.repo_root / str(selected_data)
        self.fileOpenRequested.emit(target_path)
        if self.main_window and hasattr(self.main_window, "open_path"):
            self.main_window.open_path(target_path)
        self.accept()
