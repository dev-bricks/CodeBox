#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Output-Panel - Ausfuehrung und Debug-Ausgabe"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
)
from PySide6.QtCore import QProcess, Signal
from PySide6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat


class OutputPanel(QWidget):
    """Panel fuer Programm-Ausgabe und Ausfuehrung"""

    processFinished = Signal(int, str)  # exit_code, output

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        self.status_label = QLabel("Bereit")
        toolbar.addWidget(self.status_label)
        toolbar.addStretch()

        self.run_btn = QPushButton("Run")
        self.run_btn.setEnabled(False)
        toolbar.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_process)
        toolbar.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)

        # Output-Text
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet(
            "QTextEdit { background-color: #1a1a1a; color: #d4d4d4; border: none; }"
        )
        layout.addWidget(self.output)

    def run_command(self, command: list):
        """Startet einen Prozess mit dem gegebenen Kommando"""
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.stop_process()

        self.output.clear()
        self.status_label.setText(f"Ausfuehrung: {' '.join(command)}")
        self.stop_btn.setEnabled(True)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)

        program = command[0]
        args = command[1:] if len(command) > 1 else []
        self.process.start(program, args)

    def stop_process(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.append_text("\n--- Prozess abgebrochen ---\n", color="#ff8888")

    def clear(self):
        self.output.clear()

    def append_text(self, text: str, color: str = None):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if color:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            cursor.setCharFormat(fmt)
        cursor.insertText(text)
        if color:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#d4d4d4"))
            cursor.setCharFormat(fmt)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _on_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        self.append_text(data)

    def _on_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.append_text(data, color="#ff8888")

    def _on_finished(self, exit_code, exit_status):
        self.stop_btn.setEnabled(False)
        status = "erfolgreich" if exit_code == 0 else f"mit Code {exit_code}"
        self.status_label.setText(f"Beendet {status}")
        self.append_text(f"\n--- Prozess beendet ({status}) ---\n",
                         color="#88ff88" if exit_code == 0 else "#ff8888")
        self.processFinished.emit(exit_code, self.output.toPlainText())
