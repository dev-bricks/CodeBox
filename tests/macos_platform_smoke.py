#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduzierbarer macOS-Plattform-Smoke für CodeBox.

Der Smoke deckt den macOS-Desktop-Pfad ab:
- offscreen Start des PySide6-Hauptfensters
- Dateiöffnen mit echten Umlauten ohne LSP-Zwang
- macOS-Pfad für Projektbaum/`open -R`
- macOS-Terminalpfad mit `bash`
- lokale Run-Command-Auslösung für Python-Dateien
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from features.project_view import ProjectView
from features.terminal import TerminalWidget
import features.terminal as terminal_module
from ui.main_window import MainWindow
from version import format_window_title


class SmokeFailure(RuntimeError):
    pass


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _ensure_app() -> QApplication:
    return QApplication.instance() or QApplication([])


class _DummySignal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)


class _FakeQProcess:
    class ProcessState:
        NotRunning = "not_running"
        Running = "running"

    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.cwd = None
        self.start_args = None
        self.writes: list[bytes] = []
        self._state = self.ProcessState.NotRunning
        self.readyReadStandardOutput = _DummySignal()
        self.readyReadStandardError = _DummySignal()
        self.finished = _DummySignal()

    def setWorkingDirectory(self, cwd: str) -> None:
        self.cwd = cwd

    def start(self, program: str, args: list[str]) -> None:
        self.start_args = (program, args)
        self._state = self.ProcessState.Running

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    def state(self):
        return self._state

    def kill(self) -> None:
        self._state = self.ProcessState.NotRunning

    def waitForFinished(self, _timeout: int) -> bool:
        self._state = self.ProcessState.NotRunning
        return True


def _exercise_window_open_and_run() -> None:
    print("Test 1: Offscreen-Hauptfenster öffnet Datei und löst Run-Command aus")
    app = _ensure_app()
    with tempfile.TemporaryDirectory(prefix="codebox-macos-window-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        project_dir = tmpdir / "Projekt Übersicht"
        project_dir.mkdir(parents=True)
        script_path = project_dir / "überblick.py"
        script_path.write_text("print('Grüße aus macOS')\n", encoding="utf-8")

        with mock.patch("features.terminal.TerminalWidget._start_shell", lambda self: None):
            window = MainWindow()
            try:
                window._lsp_manager.get_client = lambda _language: None
                window.show()
                app.processEvents()

                _assert(window.windowTitle() == format_window_title(), window.windowTitle())
                opened_tab = window.open_path(script_path)
                app.processEvents()

                _assert(opened_tab is not None, "Datei wurde nicht geöffnet.")
                _assert(
                    opened_tab.editor.toPlainText() == "print('Grüße aus macOS')\n",
                    "Editorinhalt stimmt nicht.",
                )
                _assert(window.windowTitle() == format_window_title(script_path), window.windowTitle())
                _assert(window.lang_label.text() == "Python", window.lang_label.text())
                _assert(window.project_view._root_path == project_dir, window.project_view._root_path)
                _assert(window.terminal.cwd_label.text() == str(project_dir), window.terminal.cwd_label.text())
                _assert(window.output.run_btn.isEnabled(), "Run-Button blieb deaktiviert.")

                captured: list[list[str]] = []
                window.output.run_command = lambda command: captured.append(command)
                window.run_current()

                _assert(captured == [["python", "-u", str(script_path)]], repr(captured))
            finally:
                window.close()
                app.processEvents()
    print("PASS: Dateiöffnung, Umlaute und Run-Command funktionieren\n")


def _exercise_macos_reveal_in_finder() -> None:
    print("Test 2: Projektbaum verwendet unter macOS open -R")
    with tempfile.TemporaryDirectory(prefix="codebox-macos-explorer-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        project_dir = tmpdir / "Projekt Übersicht"
        project_dir.mkdir(parents=True)
        file_path = project_dir / "überblick.py"
        file_path.write_text("print('ok')\n", encoding="utf-8")

        panel = ProjectView()
        with mock.patch.object(sys, "platform", "darwin"), mock.patch("subprocess.Popen") as popen_mock:
            panel._reveal_in_explorer(file_path)

        _assert(
            popen_mock.call_args.args[0] == ["open", "-R", str(file_path)],
            repr(popen_mock.call_args),
        )
    print("PASS: macOS-Finder-Pfad ist korrekt\n")


def _exercise_macos_terminal() -> None:
    print("Test 3: Terminal nutzt unter macOS bash und cd")
    app = _ensure_app()
    with tempfile.TemporaryDirectory(prefix="codebox-macos-terminal-") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        start_dir = tmpdir / "Start Ä"
        next_dir = tmpdir / "Ziel Ö"
        start_dir.mkdir(parents=True)
        next_dir.mkdir(parents=True)

        with mock.patch.object(terminal_module, "QProcess", _FakeQProcess), mock.patch.object(
            terminal_module.sys,
            "platform",
            "darwin",
        ):
            widget = TerminalWidget(working_dir=str(start_dir))
            try:
                app.processEvents()
                items = [widget.shell_combo.itemText(i) for i in range(widget.shell_combo.count())]
                _assert(items == ["bash", "zsh", "sh"], repr(items))
                _assert(widget.process.start_args == ("bash", ["--norc"]), repr(widget.process.start_args))
                _assert(widget.process.cwd == str(start_dir), widget.process.cwd)

                widget.set_working_dir(str(next_dir))
                _assert(widget.cwd_label.text() == str(next_dir), widget.cwd_label.text())
                _assert(
                    widget.process.writes[-1] == f'cd "{next_dir}"\n'.encode("utf-8"),
                    repr(widget.process.writes),
                )
            finally:
                widget.close()
                app.processEvents()
    print("PASS: macOS-Terminalpfad ist korrekt\n")


def main() -> int:
    print("=== CodeBox macOS Platform Smoke ===\n")
    _exercise_window_open_and_run()
    _exercise_macos_reveal_in_finder()
    _exercise_macos_terminal()
    print("=== ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
