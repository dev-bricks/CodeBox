#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Output-Panel - Ausführung, interaktive Ein-/Ausgabe und Debugger-Steuerung"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit
)
from PySide6.QtCore import QProcess, Signal, Qt
from PySide6.QtGui import QFont, QColor, QTextCursor, QTextCharFormat, QKeyEvent


class ConsoleInput(QLineEdit):
    """Eingabezeile mit Pfeiltasten-Befehlshistorie für das OutputPanel."""

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


class OutputPanel(QWidget):
    """Panel für Programm-Ausgabe, interaktive Eingabe und Debugger-Steuerung."""

    processFinished = Signal(int, str)  # exit_code, output
    inputSent = Signal(str)  # text sent to process or entered

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process: Optional[QProcess] = None
        self.is_debugging: bool = False
        self.history: List[str] = []
        self.history_index: int = -1
        self._initial_commands: List[str] = []
        self._current_program: str = "Programm"
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)
        self.status_label = QLabel("Bereit")
        self.status_label.setAccessibleName("Ausführungsstatus")
        self.status_label.setAccessibleDescription(
            "Zeigt, ob ein Programm gestartet wurde, läuft oder beendet ist."
        )
        toolbar.addWidget(self.status_label)
        toolbar.addStretch()

        # Debugger-Steuerungsknöpfe
        self.continue_btn = QPushButton("Weiter (F5)")
        self.continue_btn.setToolTip("Ausführung im Debugger bis zum nächsten Breakpoint fortsetzen (c)")
        self.continue_btn.setAccessibleName("Debugger: Weiter")
        self.continue_btn.setAccessibleDescription(
            "Sendet den Befehl 'c' (continue) an den aktiven Debugger."
        )
        self.continue_btn.clicked.connect(lambda: self.send_input("c"))
        toolbar.addWidget(self.continue_btn)

        self.step_over_btn = QPushButton("Schritt (F10)")
        self.step_over_btn.setToolTip("Nächste Zeile ausführen ohne in Unterfunktionen zu springen (n)")
        self.step_over_btn.setAccessibleName("Debugger: Einzelschritt (Step Over)")
        self.step_over_btn.setAccessibleDescription(
            "Sendet den Befehl 'n' (next) an den aktiven Debugger."
        )
        self.step_over_btn.clicked.connect(lambda: self.send_input("n"))
        toolbar.addWidget(self.step_over_btn)

        self.step_into_btn = QPushButton("Hinein (F11)")
        self.step_into_btn.setToolTip("In die aufgerufene Funktion hineinspringen (s)")
        self.step_into_btn.setAccessibleName("Debugger: Hineinspringen (Step Into)")
        self.step_into_btn.setAccessibleDescription(
            "Sendet den Befehl 's' (step into) an den aktiven Debugger."
        )
        self.step_into_btn.clicked.connect(lambda: self.send_input("s"))
        toolbar.addWidget(self.step_into_btn)

        self.step_out_btn = QPushButton("Heraus (Shift+F11)")
        self.step_out_btn.setToolTip("Bis zum Rücksprung aus der aktuellen Funktion ausführen (r)")
        self.step_out_btn.setAccessibleName("Debugger: Herausspringen (Step Out)")
        self.step_out_btn.setAccessibleDescription(
            "Sendet den Befehl 'r' (return/step out) an den aktiven Debugger."
        )
        self.step_out_btn.clicked.connect(lambda: self.send_input("r"))
        toolbar.addWidget(self.step_out_btn)

        self.run_btn = QPushButton("Ausführen")
        self.run_btn.setEnabled(False)
        self.run_btn.setToolTip("Aktuelle Datei ausführen")
        self.run_btn.setAccessibleName("Aktuelle Datei ausführen")
        self.run_btn.setAccessibleDescription(
            "Startet die aktuell geöffnete Datei, sobald ein passender Sprachprovider verfügbar ist."
        )
        toolbar.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stoppen")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("Laufenden Prozess stoppen")
        self.stop_btn.setAccessibleName("Ausführung stoppen")
        self.stop_btn.setAccessibleDescription(
            "Beendet den aktuell laufenden Prozess im Ausgabebereich."
        )
        self.stop_btn.clicked.connect(self.stop_process)
        toolbar.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("Leeren")
        self.clear_btn.setToolTip("Ausgabe leeren")
        self.clear_btn.setAccessibleName("Ausgabe leeren")
        self.clear_btn.setAccessibleDescription(
            "Entfernt alle bisherigen Meldungen aus dem Ausgabebereich."
        )
        self.clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)

        # Output-Text
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setToolTip("Programm-Ausgabe und Fehlermeldungen")
        self.output.setAccessibleName("Programmausgabe")
        self.output.setAccessibleDescription(
            "Zeigt Standardausgabe, Fehlerausgabe und Prozessstatus der ausgeführten Datei."
        )
        self.output.setFont(QFont("Consolas", 10))
        self.output.setStyleSheet(
            "QTextEdit { background-color: #1a1a1a; color: #d4d4d4; border: none; }"
        )
        layout.addWidget(self.output)

        # Interaktive Eingabeleiste (stdin)
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(4, 2, 4, 4)

        self.input_edit = ConsoleInput()
        self.input_edit.setPlaceholderText("Eingabe oder Debug-Befehl an Prozess senden (Enter)...")
        self.input_edit.setToolTip("Text oder Befehl an stdin des aktiven Programms oder Debuggers übergeben")
        self.input_edit.setAccessibleName("Prozess-Eingabe")
        self.input_edit.setAccessibleDescription(
            "Ermöglicht Tastatureingaben für interaktive Skripte und Debugger-Befehle."
        )
        self.input_edit.returnPressed.connect(self._on_send_clicked)
        self.input_edit.historyUp.connect(self._history_up)
        self.input_edit.historyDown.connect(self._history_down)
        input_layout.addWidget(self.input_edit)

        self.send_btn = QPushButton("Senden")
        self.send_btn.setEnabled(False)
        self.send_btn.setToolTip("Eingabe an den Prozess übergeben")
        self.send_btn.setAccessibleName("Eingabe senden")
        self.send_btn.setAccessibleDescription("Sendet die Eingabezeile an die Standard-Eingabe des Programms.")
        self.send_btn.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # Initialer Debug-Status (ausgeblendet)
        self.set_debug_mode(False)

    def is_running(self) -> bool:
        """Prüft, ob aktuell ein Prozess ausgeführt wird."""
        return bool(
            self.process
            and hasattr(self.process, "state")
            and self.process.state() == QProcess.ProcessState.Running
        )

    def set_debug_mode(self, enabled: bool):
        """Aktiviert oder deaktiviert die Debugger-Steuerungsknöpfe."""
        self.is_debugging = enabled
        for btn in (self.continue_btn, self.step_over_btn, self.step_into_btn, self.step_out_btn):
            btn.setVisible(enabled)
            btn.setEnabled(enabled)

    def _history_up(self):
        """Navigiert zum vorherigen Befehl in der Historie."""
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.input_edit.setText(self.history[self.history_index])

    def _history_down(self):
        """Navigiert zum nächsten Befehl in der Historie."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.input_edit.setText(self.history[self.history_index])
        else:
            self.history_index = len(self.history)
            self.input_edit.clear()

    def _on_send_clicked(self):
        text = self.input_edit.text()
        self.send_input(text)
        self.input_edit.clear()

    def send_input(self, text: Optional[str] = None) -> bool:
        """Sendet Text an stdin des laufenden Prozesses und pflegt die Historie."""
        if text is None:
            text = self.input_edit.text()
            self.input_edit.clear()

        if text and (not self.history or self.history[-1] != text):
            self.history.append(text)
            self.history_index = len(self.history)

        self.inputSent.emit(text if text is not None else "")

        if not self.is_running():
            self.append_text(f"\n[Kein aktiver Prozess für Eingabe '{text}']\n", color="#ffaa00")
            return False

        # Im Ausgabebereich protokollieren
        self.append_text(f"> {text}\n", color="#4ec9b0")

        # An Prozess senden (mit Newline)
        encoded = f"{text}\n".encode("utf-8", errors="replace")
        written = self.process.write(encoded)
        return bool(written != -1)

    def run_command(
        self,
        command: list,
        is_debug: bool = False,
        initial_commands: Optional[List[str]] = None,
    ):
        """Startet einen Prozess mit dem gegebenen Kommando"""
        if not command:
            self.status_label.setText("Kein Befehl zum Ausführen")
            self.stop_btn.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.set_debug_mode(False)
            return

        self._initial_commands = list(initial_commands or [])

        if self.process:
            for sig in (
                self.process.readyReadStandardOutput,
                self.process.readyReadStandardError,
                self.process.finished,
                self.process.errorOccurred,
            ):
                try:
                    sig.disconnect()
                except (TypeError, RuntimeError):
                    pass
            if hasattr(self.process, "state") and self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.kill()
                self.process.waitForFinished(1000)

        self.output.clear()
        mode_str = "Debuggen" if is_debug else "Ausführung"
        self.status_label.setText(f"{mode_str}: {' '.join(command)}")
        self.stop_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.set_debug_mode(is_debug)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)

        program = command[0]
        self._current_program = program
        args = command[1:] if len(command) > 1 else []
        self.process.start(program, args)

    def stop_process(self):
        if self.process and hasattr(self.process, "state") and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
            self.append_text("\n--- Prozess abgebrochen ---\n", color="#ff8888")
            self.stop_btn.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.set_debug_mode(False)

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
        if self._initial_commands and self.is_running():
            cmds = list(self._initial_commands)
            self._initial_commands.clear()
            for cmd in cmds:
                self.send_input(cmd)

    def _on_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
        self.append_text(data, color="#ff8888")

    def _on_finished(self, exit_code, exit_status):
        self.stop_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.set_debug_mode(False)
        status = "erfolgreich" if exit_code == 0 else f"mit Code {exit_code}"
        self.status_label.setText(f"Beendet {status}")
        self.append_text(f"\n--- Prozess beendet ({status}) ---\n",
                         color="#88ff88" if exit_code == 0 else "#ff8888")
        self.processFinished.emit(exit_code, self.output.toPlainText())

    def _on_error(self, error):
        self.stop_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.set_debug_mode(False)
        program = getattr(self, "_current_program", "Programm")
        if error == QProcess.ProcessError.FailedToStart:
            self.status_label.setText("Fehler: Programm konnte nicht gestartet werden")
            self.append_text(
                f"\n--- Fehler: Programm '{program}' konnte nicht gestartet werden (Befehl nicht gefunden oder keine Ausführungsrechte) ---\n",
                color="#ff8888",
            )
            self.processFinished.emit(-1, self.output.toPlainText())
        elif error == QProcess.ProcessError.Crashed:
            self.status_label.setText("Fehler: Prozess abgestürzt")
            self.append_text(f"\n--- Fehler: Prozess '{program}' ist abgestürzt ---\n", color="#ff8888")

    def closeEvent(self, event):
        if self.process and hasattr(self.process, "state") and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        super().closeEvent(event)

