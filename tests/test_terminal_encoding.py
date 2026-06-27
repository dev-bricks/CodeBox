"""Tests für terminal.py Encoding-Konsistenz."""
import sys
import types
import unittest
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QApplication

from features.terminal import TerminalWidget


def _ensure_app():
    return QApplication.instance() or QApplication([])


class TerminalEncodingTests(unittest.TestCase):
    def setUp(self):
        _ensure_app()

    def _make_widget(self, shell: str = "cmd") -> TerminalWidget:
        with patch.object(TerminalWidget, "_start_shell", lambda self: None):
            widget = TerminalWidget()
        widget.shell_combo.setCurrentText(shell)
        return widget

    # --- _input_encoding ---

    @unittest.skipUnless(sys.platform == "win32", "Windows-only")
    def test_input_encoding_cmd_is_cp1252(self):
        """Regression (B-002): cmd-Shell muss cp1252 zurückgeben."""
        widget = self._make_widget("cmd")
        self.assertEqual(widget._input_encoding(), "cp1252")
        widget.close()

    @unittest.skipUnless(sys.platform == "win32", "Windows-only")
    def test_input_encoding_powershell_is_utf8(self):
        """PowerShell-Shell soll utf-8 verwenden."""
        widget = self._make_widget("powershell")
        self.assertEqual(widget._input_encoding(), "utf-8")
        widget.close()

    # --- set_working_dir encoding-Konsistenz ---

    @unittest.skipUnless(sys.platform == "win32", "Windows-only")
    def test_set_working_dir_uses_same_encoding_as_execute_command(self):
        """Regression (B-002): set_working_dir() muss dieselbe Encoding-Logik
        wie _execute_command() nutzen — zuvor wurde utf-8 hart codiert,
        _execute_command() aber cp1252 fuer cmd."""
        widget = self._make_widget("cmd")

        # Prozess-Mock im Running-Zustand
        from PySide6.QtCore import QProcess
        written = []
        mock_proc = MagicMock()
        mock_proc.state.return_value = QProcess.ProcessState.Running
        mock_proc.write.side_effect = lambda data: written.append(data)
        widget.process = mock_proc

        path_with_umlaut = "C:/Benutzer/Schüler/Projekte"
        widget.set_working_dir(path_with_umlaut)

        self.assertEqual(len(written), 1)
        encoded_cmd = written[0]
        # Muss mit cp1252 codiert sein (nicht utf-8 hard-coded)
        expected = f'cd /d "{path_with_umlaut}"\n'.encode("cp1252", errors="replace")
        self.assertEqual(encoded_cmd, expected,
                         "set_working_dir() muss denselben cp1252-Encoding-Pfad wie _execute_command() nutzen")
        widget.close()


class TerminalStartShellTests(unittest.TestCase):
    """Regressionstests für _start_shell() Signal-Verwaltung (B-012)."""

    def setUp(self):
        _ensure_app()

    def _make_widget_no_shell(self) -> TerminalWidget:
        """Erzeugt ein TerminalWidget ohne echten Shell-Start."""
        with patch.object(TerminalWidget, "_start_shell", lambda self: None):
            return TerminalWidget()

    def test_start_shell_disconnects_old_process_signals(self):
        """Regression (B-012): _start_shell() muss alle Signale des alten
        Prozesses trennen, bevor er ersetzt wird — sonst feuert _on_finished
        des alten Prozesses auf den neuen Zustand und erzeugt z. B. einen
        spuriösen 'Shell beendet'-Eintrag im neuen Terminal-Output."""
        from PySide6.QtCore import QProcess as RealQProcess

        widget = self._make_widget_no_shell()

        mock_old = MagicMock()
        mock_old.state.return_value = RealQProcess.ProcessState.Running
        widget.process = mock_old

        with patch("features.terminal.QProcess") as mock_cls:
            mock_cls.return_value = MagicMock()
            widget._start_shell()

        mock_old.readyReadStandardOutput.disconnect.assert_called_once_with()
        mock_old.readyReadStandardError.disconnect.assert_called_once_with()
        mock_old.finished.disconnect.assert_called_once_with()
        mock_old.kill.assert_called_once()
        widget.close()

    def test_start_shell_no_kill_when_already_stopped(self):
        """Ist der alte Prozess bereits beendet, darf kill() nicht aufgerufen werden."""
        from PySide6.QtCore import QProcess as RealQProcess

        widget = self._make_widget_no_shell()

        mock_old = MagicMock()
        mock_old.state.return_value = RealQProcess.ProcessState.NotRunning
        widget.process = mock_old

        with patch("features.terminal.QProcess") as mock_cls:
            # Echten Enum weiterreichen, damit der state()-Vergleich in
            # _start_shell korrekt ausgewertet werden kann.
            mock_cls.ProcessState = RealQProcess.ProcessState
            mock_cls.return_value = MagicMock()
            widget._start_shell()

        mock_old.kill.assert_not_called()
        widget.close()

    def test_start_shell_no_disconnect_when_no_prior_process(self):
        """Ohne vorherigen Prozess darf kein disconnect() aufgerufen werden."""
        widget = self._make_widget_no_shell()
        widget.process = None

        with patch("features.terminal.QProcess") as mock_cls:
            mock_cls.return_value = MagicMock()
            widget._start_shell()
        # Kein AttributeError, kein Kill-Aufruf — Test besteht wenn kein Fehler
        widget.close()


if __name__ == "__main__":
    unittest.main()
