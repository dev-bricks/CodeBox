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


if __name__ == "__main__":
    unittest.main()
