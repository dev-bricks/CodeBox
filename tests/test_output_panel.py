"""Regressionstests für core/output.py — OutputPanel."""
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QProcess

from core.output import OutputPanel


def _ensure_app():
    return QApplication.instance() or QApplication([])


class OutputPanelSignalTests(unittest.TestCase):
    def setUp(self):
        _ensure_app()
        self.panel = OutputPanel()

    def tearDown(self):
        self.panel.close()

    def test_run_command_disconnects_old_process_signals(self):
        """Regression (B-004): run_command() muss alle Signale des alten
        Prozesses trennen, bevor er ersetzt wird — sonst feuert _on_finished
        des alten Prozesses auf den neuen Prozess und setzt stop_btn fälschlich
        auf disabled."""
        mock_old = MagicMock()
        mock_old.state.return_value = QProcess.ProcessState.Running
        self.panel.process = mock_old

        with patch("core.output.QProcess") as mock_cls:
            mock_new = MagicMock()
            mock_cls.return_value = mock_new
            self.panel.run_command(["echo", "test"])

        mock_old.readyReadStandardOutput.disconnect.assert_called_once_with()
        mock_old.readyReadStandardError.disconnect.assert_called_once_with()
        mock_old.finished.disconnect.assert_called_once_with()
        mock_old.kill.assert_called_once()

    def test_run_command_no_disconnect_when_no_prior_process(self):
        """Ohne vorherigen Prozess darf kein disconnect() aufgerufen werden."""
        self.panel.process = None

        with patch("core.output.QProcess") as mock_cls:
            mock_new = MagicMock()
            mock_cls.return_value = mock_new
            self.panel.run_command(["echo", "test"])

    def test_run_command_stop_btn_enabled_after_start(self):
        """stop_btn muss nach run_command() aktiviert sein."""
        with patch("core.output.QProcess") as mock_cls:
            mock_cls.return_value = MagicMock()
            self.panel.run_command(["echo", "test"])

        self.assertTrue(
            self.panel.stop_btn.isEnabled(),
            "stop_btn muss nach run_command() enabled sein",
        )


if __name__ == "__main__":
    unittest.main()
