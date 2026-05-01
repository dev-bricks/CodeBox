#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integriertes Terminal für CodeBox

Bietet ein eingebettetes Terminal-Widget als QWidget,
das Shell-Befehle ausführen und interaktiv nutzen kann.
"""

import sys
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Qt, QProcess, Signal
from PySide6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QKeyEvent


class TerminalInput(QLineEdit):
    """Eingabezeile mit Befehls-History."""

    historyUp = Signal()
    historyDown = Signal()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Up:
            self.historyUp.emit()
            return
        if event.key() == Qt.Key_Down:
            self.historyDown.emit()
            return
        super().keyPressEvent(event)


class TerminalWidget(QWidget):
    """Integriertes Terminal-Widget für CodeBox.

    Startet eine Shell (cmd/powershell/bash) und ermöglicht
    interaktive Befehlseingabe.
    """

    def __init__(self, parent=None, working_dir: str = None):
        super().__init__(parent)
        self.working_dir = working_dir or os.getcwd()
        self.process: QProcess = None
        self.history: list = []
        self.history_index = -1

        self._setup_ui()
        self._start_shell()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)

        self.shell_combo = QComboBox()
        self._populate_shells()
        self.shell_combo.currentTextChanged.connect(self._restart_shell)
        toolbar.addWidget(QLabel("Shell:"))
        toolbar.addWidget(self.shell_combo)

        toolbar.addStretch()

        self.cwd_label = QLabel(self.working_dir)
        self.cwd_label.setStyleSheet("color: #888; font-size: 10px;")
        toolbar.addWidget(self.cwd_label)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedWidth(50)
        btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(btn_clear)

        layout.addLayout(toolbar)

        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet(
            "QTextEdit { background-color: #0c0c0c; color: #cccccc; border: none; }"
        )
        layout.addWidget(self.output)

        # Input
        input_row = QHBoxLayout()
        input_row.setContentsMargins(4, 0, 4, 4)

        self.prompt_label = QLabel(">")
        self.prompt_label.setStyleSheet("color: #4ec9b0; font-family: Consolas;")
        input_row.addWidget(self.prompt_label)

        self.input = TerminalInput()
        self.input.setFont(QFont("Consolas", 10))
        self.input.setStyleSheet(
            "QLineEdit { background: #1a1a1a; color: #cccccc; border: 1px solid #333; padding: 4px; }"
        )
        self.input.returnPressed.connect(self._execute_command)
        self.input.historyUp.connect(self._history_up)
        self.input.historyDown.connect(self._history_down)
        input_row.addWidget(self.input)

        layout.addLayout(input_row)

    def _populate_shells(self):
        """Füllt die Shell-Auswahl basierend auf dem OS."""
        if sys.platform == "win32":
            self.shell_combo.addItems(["cmd", "powershell"])
        else:
            self.shell_combo.addItems(["bash", "zsh", "sh"])

    def _get_shell_command(self) -> tuple:
        """Gibt Shell-Programm und Argumente zurück."""
        shell = self.shell_combo.currentText()
        if shell == "cmd":
            return ("cmd.exe", ["/Q"])
        elif shell == "powershell":
            return ("powershell.exe", ["-NoLogo", "-NoProfile"])
        elif shell == "bash":
            return ("bash", ["--norc"])
        elif shell == "zsh":
            return ("zsh", ["--no-rcs"])
        return ("sh", [])

    def _start_shell(self):
        """Startet den Shell-Prozess."""
        if self.process:
            self.process.kill()
            self.process.waitForFinished(1000)

        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.working_dir)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)

        program, args = self._get_shell_command()
        self.process.start(program, args)
        self.append_text(f"--- {program} gestartet ---\n", "#4ec9b0")

    def _restart_shell(self):
        """Neustart mit anderer Shell."""
        self.clear()
        self._start_shell()

    def _execute_command(self):
        """Führt den eingegebenen Befehl aus."""
        cmd = self.input.text().strip()
        if not cmd:
            return

        # History
        self.history.append(cmd)
        self.history_index = len(self.history)

        # Befehl anzeigen
        self.append_text(f"> {cmd}\n", "#4ec9b0")
        self.input.clear()

        # An den Prozess senden
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            encoding = 'utf-8' if sys.platform != 'win32' else 'cp1252'
            self.process.write(f"{cmd}\n".encode(encoding, errors='replace'))

    def _history_up(self):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.input.setText(self.history[self.history_index])

    def _history_down(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.input.setText(self.history[self.history_index])
        else:
            self.history_index = len(self.history)
            self.input.clear()

    def append_text(self, text: str, color: str = None):
        """Fügt Text zum Output hinzu. Farbe wird pro Segment gesetzt (kein Dokument-Override)."""
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if color:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            cursor.setCharFormat(fmt)
        cursor.insertText(text)
        if color:
            # Standardfarbe wiederherstellen
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#cccccc"))
            cursor.setCharFormat(fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def clear(self):
        self.output.clear()

    def set_working_dir(self, path: str):
        """Ändert das Arbeitsverzeichnis."""
        self.working_dir = path
        self.cwd_label.setText(path)
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            if sys.platform == "win32":
                self.process.write(f"cd /d \"{path}\"\n".encode('utf-8'))
            else:
                self.process.write(f"cd \"{path}\"\n".encode('utf-8'))

    def _on_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.append_text(data)

    def _on_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.append_text(data, "#ff8888")

    def _on_finished(self, exit_code, exit_status):
        self.append_text(f"\n--- Shell beendet (Code {exit_code}) ---\n", "#888888")

    def closeEvent(self, event):
        if self.process:
            self.process.kill()
            self.process.waitForFinished(1000)
        super().closeEvent(event)
