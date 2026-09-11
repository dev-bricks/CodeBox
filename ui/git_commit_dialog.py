#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Staging & Commit-Dialog für CodeBox.

Ermöglicht das Bereitstellen (Staging), Zurücknehmen (Unstaging),
Verwerfen und Committen von Dateiänderungen direkt aus der CodeBox-Benutzeroberfläche:
- Zweiteilige Ansicht für Staged und Unstaged Änderungen
- Datei-Diff-Aufruf für beliebige geänderte Dateien
- Direkte Tastaturunterstützung (Ctrl+Enter zum Committen)
- Vollständige Barrierefreiheit (WCAG-Kontraste, Screenreader-Attribute)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from features.git_integration import GitFileStatus, GitRepo

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = logging.getLogger("CodeBox.GitCommitDialog")


class GitCommitDialog(QDialog):
    """Dialog für Git-Staging und Commit-Erstellung."""

    committed = Signal(str)
    status_changed = Signal()

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        git_repo: Optional[GitRepo] = None,
        initial_file: Optional[Path] = None,
        parent: Optional[QWidget] = None,
        main_window: Optional["MainWindow"] = None,
    ):
        super().__init__(parent)
        self.repo_root = Path(repo_root) if repo_root else (Path.cwd() if not git_repo else git_repo.repo_path)
        self.git_repo = git_repo if git_repo is not None else GitRepo(str(self.repo_root))
        self.initial_file = Path(initial_file) if initial_file else None
        self.main_window = main_window

        self.staged_items: List[Tuple[str, GitFileStatus]] = []
        self.unstaged_items: List[Tuple[str, GitFileStatus]] = []

        self.setWindowTitle("Git Commit - CodeBox")
        self.setObjectName("git_commit_dialog")
        self.setAccessibleName("Git Commit Dialog")
        self.setAccessibleDescription(
            "Dialog zum Bereitstellen von Dateiänderungen und Erstellen von Git-Commits"
        )
        self.resize(860, 640)
        self.setMinimumSize(600, 450)

        self._setup_ui()
        self._setup_shortcuts()
        self.refresh()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # Header: Repo path and branch info
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.lbl_repo_info = QLabel("Repository:")
        self.lbl_repo_info.setObjectName("git_commit_repo_info")
        self.lbl_repo_info.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_repo_info.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(self.lbl_repo_info, 1)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.setObjectName("git_commit_refresh_btn")
        self.btn_refresh.setToolTip("Git-Status aktualisieren (F5)")
        self.btn_refresh.setAccessibleName("Git-Status aktualisieren")
        self.btn_refresh.setAccessibleDescription("Liest den aktuellen Status des Git-Repositorys neu ein")
        self.btn_refresh.clicked.connect(self.refresh)
        header_layout.addWidget(self.btn_refresh)

        root_layout.addLayout(header_layout)

        # Main splitter (Vertical: Files Lists top, Commit message bottom)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)

        # Top half: Horizontal splitter for Staged vs Unstaged
        files_splitter = QSplitter(Qt.Orientation.Horizontal)
        files_splitter.setChildrenCollapsible(False)

        # --- Left Panel: Staged Files ---
        staged_widget = QWidget()
        staged_layout = QVBoxLayout(staged_widget)
        staged_layout.setContentsMargins(0, 0, 0, 0)
        staged_layout.setSpacing(6)

        staged_header = QHBoxLayout()
        self.lbl_staged_title = QLabel("Bereitgestellt (Staged): 0")
        self.lbl_staged_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_staged_title.setStyleSheet("color: #73c991;")
        staged_header.addWidget(self.lbl_staged_title, 1)

        self.btn_unstage_all = QPushButton("Alle unstagen")
        self.btn_unstage_all.setObjectName("git_commit_unstage_all_btn")
        self.btn_unstage_all.setToolTip("Alle Dateien aus dem Staging-Bereich entfernen")
        self.btn_unstage_all.setAccessibleName("Alle Dateien unstagen")
        self.btn_unstage_all.clicked.connect(self._on_unstage_all)
        staged_header.addWidget(self.btn_unstage_all)
        staged_layout.addLayout(staged_header)

        self.list_staged = QListWidget()
        self.list_staged.setObjectName("git_commit_staged_list")
        self.list_staged.setFont(QFont("Consolas", 10))
        self.list_staged.setAccessibleName("Staged Dateien")
        self.list_staged.setAccessibleDescription(
            "Liste der zum Commit bereitgestellten Dateien. Doppelklick hebt das Staging auf."
        )
        self.list_staged.itemDoubleClicked.connect(self._on_staged_item_double_clicked)
        self.list_staged.itemSelectionChanged.connect(self._update_action_buttons_state)
        staged_layout.addWidget(self.list_staged, 1)

        staged_actions = QHBoxLayout()
        self.btn_unstage_selected = QPushButton("Aus Staging entfernen")
        self.btn_unstage_selected.setObjectName("git_commit_unstage_selected_btn")
        self.btn_unstage_selected.setToolTip("Ausgewählte Datei aus dem Staging-Bereich entfernen")
        self.btn_unstage_selected.setAccessibleName("Ausgewählte Datei unstagen")
        self.btn_unstage_selected.clicked.connect(self._on_unstage_selected)
        staged_actions.addWidget(self.btn_unstage_selected)

        self.btn_diff_staged = QPushButton("Diff (Staged)")
        self.btn_diff_staged.setObjectName("git_commit_diff_staged_btn")
        self.btn_diff_staged.setToolTip("Diff der ausgewählten Datei im Staging-Bereich anzeigen")
        self.btn_diff_staged.setAccessibleName("Staged Diff anzeigen")
        self.btn_diff_staged.clicked.connect(self._on_diff_staged)
        staged_actions.addWidget(self.btn_diff_staged)
        staged_layout.addLayout(staged_actions)

        files_splitter.addWidget(staged_widget)

        # --- Right Panel: Unstaged Files ---
        unstaged_widget = QWidget()
        unstaged_layout = QVBoxLayout(unstaged_widget)
        unstaged_layout.setContentsMargins(0, 0, 0, 0)
        unstaged_layout.setSpacing(6)

        unstaged_header = QHBoxLayout()
        self.lbl_unstaged_title = QLabel("Nicht bereitgestellt (Unstaged): 0")
        self.lbl_unstaged_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_unstaged_title.setStyleSheet("color: #e2c08d;")
        unstaged_header.addWidget(self.lbl_unstaged_title, 1)

        self.btn_stage_all = QPushButton("Alle stagen")
        self.btn_stage_all.setObjectName("git_commit_stage_all_btn")
        self.btn_stage_all.setToolTip("Alle geänderten und neuen Dateien stagen (git add -A)")
        self.btn_stage_all.setAccessibleName("Alle Dateien stagen")
        self.btn_stage_all.clicked.connect(self._on_stage_all)
        unstaged_header.addWidget(self.btn_stage_all)
        unstaged_layout.addLayout(unstaged_header)

        self.list_unstaged = QListWidget()
        self.list_unstaged.setObjectName("git_commit_unstaged_list")
        self.list_unstaged.setFont(QFont("Consolas", 10))
        self.list_unstaged.setAccessibleName("Nicht bereitgestellte Dateien")
        self.list_unstaged.setAccessibleDescription(
            "Liste der geänderten Arbeitsbaum-Dateien. Doppelklick stellt die Datei bereit."
        )
        self.list_unstaged.itemDoubleClicked.connect(self._on_unstaged_item_double_clicked)
        self.list_unstaged.itemSelectionChanged.connect(self._update_action_buttons_state)
        unstaged_layout.addWidget(self.list_unstaged, 1)

        unstaged_actions = QHBoxLayout()
        self.btn_stage_selected = QPushButton("Stagen")
        self.btn_stage_selected.setObjectName("git_commit_stage_selected_btn")
        self.btn_stage_selected.setToolTip("Ausgewählte Datei zum Commit bereitstellen")
        self.btn_stage_selected.setAccessibleName("Ausgewählte Datei stagen")
        self.btn_stage_selected.clicked.connect(self._on_stage_selected)
        unstaged_actions.addWidget(self.btn_stage_selected)

        self.btn_discard_selected = QPushButton("Verwerfen...")
        self.btn_discard_selected.setObjectName("git_commit_discard_selected_btn")
        self.btn_discard_selected.setToolTip("Lokale Änderungen an der ausgewählten Datei unwiderruflich verwerfen")
        self.btn_discard_selected.setAccessibleName("Änderungen verwerfen")
        self.btn_discard_selected.clicked.connect(self._on_discard_selected)
        unstaged_actions.addWidget(self.btn_discard_selected)

        self.btn_diff_unstaged = QPushButton("Diff")
        self.btn_diff_unstaged.setObjectName("git_commit_diff_unstaged_btn")
        self.btn_diff_unstaged.setToolTip("Diff der ausgewählten Arbeitsbaum-Datei anzeigen")
        self.btn_diff_unstaged.setAccessibleName("Arbeitsbaum Diff anzeigen")
        self.btn_diff_unstaged.clicked.connect(self._on_diff_unstaged)
        unstaged_actions.addWidget(self.btn_diff_unstaged)
        unstaged_layout.addLayout(unstaged_actions)

        files_splitter.addWidget(unstaged_widget)
        files_splitter.setSizes([420, 420])

        main_splitter.addWidget(files_splitter)

        # --- Bottom Panel: Commit Message & Submit ---
        commit_widget = QWidget()
        commit_layout = QVBoxLayout(commit_widget)
        commit_layout.setContentsMargins(0, 8, 0, 0)
        commit_layout.setSpacing(6)

        msg_header = QHBoxLayout()
        lbl_msg = QLabel("Commit-Nachricht:")
        lbl_msg.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_msg.setStyleSheet("color: #cccccc;")
        msg_header.addWidget(lbl_msg)

        self.lbl_char_count = QLabel("0 Zeichen")
        self.lbl_char_count.setStyleSheet("color: #888888; font-size: 11px;")
        msg_header.addStretch()
        msg_header.addWidget(self.lbl_char_count)
        commit_layout.addLayout(msg_header)

        self.txt_message = QPlainTextEdit()
        self.txt_message.setObjectName("git_commit_message_input")
        self.txt_message.setPlaceholderText(
            "Kurze Zusammenfassung (erste Zeile)\n\nAusführlichere Beschreibung der Änderungen..."
        )
        self.txt_message.setFont(QFont("Consolas", 10))
        self.txt_message.setAccessibleName("Commit-Nachricht")
        self.txt_message.setAccessibleDescription(
            "Eingabefeld für die Git-Commit-Nachricht. Drücken Sie Strg+Enter zum Committen."
        )
        self.txt_message.textChanged.connect(self._on_message_changed)
        commit_layout.addWidget(self.txt_message, 1)

        # Footer Actions
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("git_commit_status_lbl")
        self.lbl_status.setStyleSheet("font-size: 12px;")
        footer_layout.addWidget(self.lbl_status, 1)

        self.btn_cancel = QPushButton("Schließen")
        self.btn_cancel.setObjectName("git_commit_cancel_btn")
        self.btn_cancel.setAccessibleName("Dialog schließen")
        self.btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self.btn_cancel)

        self.btn_commit = QPushButton("Commit erstellen (Ctrl+Enter)")
        self.btn_commit.setObjectName("git_commit_submit_btn")
        self.btn_commit.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        self.btn_commit.setAccessibleName("Commit ausführen")
        self.btn_commit.setAccessibleDescription("Führt den Git-Commit mit den bereitgestellten Dateien aus")
        self.btn_commit.clicked.connect(self._on_commit)
        footer_layout.addWidget(self.btn_commit)

        commit_layout.addLayout(footer_layout)
        main_splitter.addWidget(commit_widget)

        main_splitter.setSizes([360, 220])
        root_layout.addWidget(main_splitter)

    def _setup_shortcuts(self):
        shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        shortcut_refresh.activated.connect(self.refresh)

        # Ctrl+Return and Ctrl+Enter to trigger commit
        shortcut_commit1 = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_commit1.activated.connect(self._on_commit)
        shortcut_commit2 = QShortcut(QKeySequence("Ctrl+Enter"), self)
        shortcut_commit2.activated.connect(self._on_commit)

    def refresh(self):
        """Aktualisiert Git-Status und füllt die Listen neu."""
        if not self.git_repo or not self.git_repo.is_git_repo():
            self.lbl_repo_info.setText(f"Repository: {self.repo_root.name} (Kein Git-Repository)")
            self.list_staged.clear()
            self.list_unstaged.clear()
            self.btn_commit.setEnabled(False)
            return

        branch = self.git_repo.get_branch()
        self.lbl_repo_info.setText(f"Repository: {self.repo_root.name}  |  Branch: {branch}")

        status_dict = self.git_repo.get_status()
        self.staged_items = []
        self.unstaged_items = []

        for rel_path, status in sorted(status_dict.items()):
            if status.is_staged:
                self.staged_items.append((rel_path, status))
            if status.is_modified or status.is_untracked or status.is_deleted:
                self.unstaged_items.append((rel_path, status))

        self._populate_list(self.list_staged, self.staged_items, is_staged=True)
        self._populate_list(self.list_unstaged, self.unstaged_items, is_staged=False)

        self.lbl_staged_title.setText(f"Bereitgestellt (Staged): {len(self.staged_items)}")
        self.lbl_unstaged_title.setText(f"Nicht bereitgestellt (Unstaged): {len(self.unstaged_items)}")

        self.btn_unstage_all.setEnabled(len(self.staged_items) > 0)
        self.btn_stage_all.setEnabled(len(self.unstaged_items) > 0)

        # Highlight initial file if provided
        if self.initial_file:
            try:
                rel = self.initial_file.relative_to(self.repo_root).as_posix()
                self._select_path_in_lists(rel)
            except ValueError:
                pass

        self._update_action_buttons_state()

    def _populate_list(self, list_widget: QListWidget, items: List[Tuple[str, GitFileStatus]], is_staged: bool):
        list_widget.clear()
        for rel_path, status in items:
            badge = self._format_status_badge(status, is_staged)
            item = QListWidgetItem(f"{badge}  {rel_path}")
            item.setData(Qt.ItemDataRole.UserRole, rel_path)

            if "[D]" in badge:
                item.setForeground(QColor("#f48771"))  # Rot
            elif "[A]" in badge or "[?]" in badge:
                item.setForeground(QColor("#73c991"))  # Grün
            else:
                item.setForeground(QColor("#e2c08d"))  # Gelb/Orange

            list_widget.addItem(item)

    def _format_status_badge(self, status: GitFileStatus, is_staged: bool) -> str:
        if is_staged:
            code = status.index_status
            if code == "A":
                return "[A]"
            elif code == "D":
                return "[D]"
            elif code == "R":
                return "[R]"
            return "[M]"
        else:
            if status.is_untracked:
                return "[?]"
            elif status.is_deleted:
                return "[D]"
            return "[M]"

    def _select_path_in_lists(self, rel_path: str):
        for i in range(self.list_staged.count()):
            item = self.list_staged.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == rel_path:
                self.list_staged.setCurrentItem(item)
                return
        for i in range(self.list_unstaged.count()):
            item = self.list_unstaged.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == rel_path:
                self.list_unstaged.setCurrentItem(item)
                return

    def _on_message_changed(self):
        text = self.txt_message.toPlainText()
        char_count = len(text)
        line_count = len(text.splitlines()) if text else 0
        self.lbl_char_count.setText(f"{char_count} Zeichen ({line_count} Zeilen)")
        self._update_action_buttons_state()

    def _update_action_buttons_state(self):
        has_staged = len(self.staged_items) > 0
        has_msg = bool(self.txt_message.toPlainText().strip())
        self.btn_commit.setEnabled(has_staged and has_msg)

        cur_staged = self.list_staged.currentItem()
        self.btn_unstage_selected.setEnabled(cur_staged is not None)
        self.btn_diff_staged.setEnabled(cur_staged is not None)

        cur_unstaged = self.list_unstaged.currentItem()
        self.btn_stage_selected.setEnabled(cur_unstaged is not None)
        self.btn_discard_selected.setEnabled(cur_unstaged is not None)
        self.btn_diff_unstaged.setEnabled(cur_unstaged is not None)

    def _on_staged_item_double_clicked(self, item: QListWidgetItem):
        rel_path = item.data(Qt.ItemDataRole.UserRole)
        if rel_path:
            self._unstage_file(rel_path)

    def _on_unstaged_item_double_clicked(self, item: QListWidgetItem):
        rel_path = item.data(Qt.ItemDataRole.UserRole)
        if rel_path:
            self._stage_file(rel_path)

    def _on_stage_selected(self):
        item = self.list_unstaged.currentItem()
        if item:
            rel_path = item.data(Qt.ItemDataRole.UserRole)
            if rel_path:
                self._stage_file(rel_path)

    def _on_unstage_selected(self):
        item = self.list_staged.currentItem()
        if item:
            rel_path = item.data(Qt.ItemDataRole.UserRole)
            if rel_path:
                self._unstage_file(rel_path)

    def _on_stage_all(self):
        if self.git_repo.stage_all():
            self.lbl_status.setText("Alle Änderungen bereitgestellt.")
            self.lbl_status.setStyleSheet("color: #73c991;")
            self.refresh()
            self.status_changed.emit()
        else:
            self.lbl_status.setText("Fehler beim Stagen aller Dateien.")
            self.lbl_status.setStyleSheet("color: #f48771;")

    def _on_unstage_all(self):
        if self.git_repo.unstage_all():
            self.lbl_status.setText("Staging für alle Dateien aufgehoben.")
            self.lbl_status.setStyleSheet("color: #73c991;")
            self.refresh()
            self.status_changed.emit()
        else:
            self.lbl_status.setText("Fehler beim Aufheben des Stagings.")
            self.lbl_status.setStyleSheet("color: #f48771;")

    def _stage_file(self, rel_path: str):
        if self.git_repo.stage_file(rel_path):
            self.lbl_status.setText(f"Bereitgestellt: {rel_path}")
            self.lbl_status.setStyleSheet("color: #73c991;")
            self.refresh()
            self._select_path_in_lists(rel_path)
            self.status_changed.emit()
        else:
            self.lbl_status.setText(f"Fehler beim Stagen von {rel_path}")
            self.lbl_status.setStyleSheet("color: #f48771;")

    def _unstage_file(self, rel_path: str):
        if self.git_repo.unstage_file(rel_path):
            self.lbl_status.setText(f"Staging aufgehoben: {rel_path}")
            self.lbl_status.setStyleSheet("color: #73c991;")
            self.refresh()
            self._select_path_in_lists(rel_path)
            self.status_changed.emit()
        else:
            self.lbl_status.setText(f"Fehler beim Unstagen von {rel_path}")
            self.lbl_status.setStyleSheet("color: #f48771;")

    def _on_discard_selected(self):
        item = self.list_unstaged.currentItem()
        if not item:
            return
        rel_path = item.data(Qt.ItemDataRole.UserRole)
        if not rel_path:
            return

        reply = QMessageBox.question(
            self,
            "Änderungen verwerfen",
            f"Möchten Sie alle Änderungen an '{rel_path}' wirklich unwiderruflich verwerfen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.git_repo.discard_file_changes(rel_path):
                self.lbl_status.setText(f"Änderungen verworfen: {rel_path}")
                self.lbl_status.setStyleSheet("color: #73c991;")
                self.refresh()
                self.status_changed.emit()
            else:
                self.lbl_status.setText(f"Fehler beim Verwerfen von {rel_path}")
                self.lbl_status.setStyleSheet("color: #f48771;")

    def _on_diff_staged(self):
        item = self.list_staged.currentItem()
        rel_path = item.data(Qt.ItemDataRole.UserRole) if item else None
        self._open_diff_viewer(rel_path=rel_path, staged=True)

    def _on_diff_unstaged(self):
        item = self.list_unstaged.currentItem()
        rel_path = item.data(Qt.ItemDataRole.UserRole) if item else None
        self._open_diff_viewer(rel_path=rel_path, staged=False)

    def _open_diff_viewer(self, rel_path: Optional[str], staged: bool):
        try:
            from ui.diff_viewer import GitDiffDialog

            init_file = (self.repo_root / rel_path) if rel_path else None
            dialog = GitDiffDialog(
                main_window=self.main_window,
                repo_root=self.repo_root,
                initial_file=init_file,
                staged=staged,
                parent=self,
            )
            dialog.exec()
            self.refresh()
        except Exception as e:
            logger.exception("Konnte Git Diff-Viewer nicht öffnen: %s", e)
            QMessageBox.warning(self, "Diff-Viewer Fehler", f"Konnte Diff-Viewer nicht öffnen:\n{e}")

    def _on_commit(self):
        """Führt den Commit aus."""
        if not self.btn_commit.isEnabled():
            return

        msg = self.txt_message.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, "Leere Nachricht", "Bitte geben Sie eine Commit-Nachricht ein.")
            return

        if not self.staged_items:
            QMessageBox.warning(
                self,
                "Keine Änderungen bereitgestellt",
                "Es wurden keine Dateien für den Commit bereitgestellt (Staged).\n"
                "Bitte stagen Sie mindestens eine Datei.",
            )
            return

        success, output = self.git_repo.commit(msg)
        if success:
            self.lbl_status.setText("Commit erfolgreich erstellt!")
            self.lbl_status.setStyleSheet("color: #73c991; font-weight: bold;")
            self.committed.emit(msg)
            self.status_changed.emit()
            self.accept()
        else:
            self.lbl_status.setText(f"Commit fehlgeschlagen: {output}")
            self.lbl_status.setStyleSheet("color: #f48771; font-weight: bold;")
            QMessageBox.critical(self, "Commit-Fehler", f"Git-Commit ist fehlgeschlagen:\n\n{output}")
