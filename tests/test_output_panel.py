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
        mock_old.errorOccurred.disconnect.assert_called_once_with()
        mock_old.kill.assert_called_once()

    def test_run_command_no_disconnect_when_no_prior_process(self):
        """Ohne vorherigen Prozess darf kein disconnect() aufgerufen werden."""
        self.panel.process = None

        with patch("core.output.QProcess") as mock_cls:
            mock_new = MagicMock()
            mock_cls.return_value = mock_new
            self.panel.run_command(["echo", "test"])

    def test_run_command_rejects_empty_command(self):
        """Leere Provider-Kommandos dürfen nicht per IndexError crashen."""
        with patch("core.output.QProcess") as mock_cls:
            self.panel.run_command([])

        mock_cls.assert_not_called()
        self.assertFalse(self.panel.stop_btn.isEnabled())
        self.assertIn("Kein Befehl", self.panel.status_label.text())

    def test_run_command_stop_btn_enabled_after_start(self):
        """stop_btn muss nach run_command() aktiviert sein."""
        with patch("core.output.QProcess") as mock_cls:
            mock_cls.return_value = MagicMock()
            self.panel.run_command(["echo", "test"])

        self.assertTrue(
            self.panel.stop_btn.isEnabled(),
            "stop_btn muss nach run_command() enabled sein",
        )

    def test_output_controls_expose_accessible_context(self):
        """Ausgabe-Controls brauchen deutsche Labels und Assistenzkontext."""
        self.assertEqual(self.panel.run_btn.text(), "Ausführen")
        self.assertEqual(self.panel.run_btn.toolTip(), "Aktuelle Datei ausführen")
        self.assertEqual(self.panel.run_btn.accessibleName(), "Aktuelle Datei ausführen")
        self.assertIn("Sprachprovider", self.panel.run_btn.accessibleDescription())

        self.assertEqual(self.panel.stop_btn.text(), "Stoppen")
        self.assertEqual(self.panel.stop_btn.accessibleName(), "Ausführung stoppen")
        self.assertIn("laufenden Prozess", self.panel.stop_btn.accessibleDescription())

        self.assertEqual(self.panel.clear_btn.text(), "Leeren")
        self.assertEqual(self.panel.clear_btn.accessibleName(), "Ausgabe leeren")
        self.assertIn("Meldungen", self.panel.clear_btn.accessibleDescription())

    def test_run_command_failed_to_start_disables_stop_btn_and_emits_finished(self):
        """Wenn ein Programm nicht gestartet werden kann, muss stop_btn deaktiviert,
        der Status aktualisiert und ein Fehler ausgegeben werden."""
        emitted_results = []
        self.panel.processFinished.connect(lambda code, text: emitted_results.append((code, text)))

        self.panel._current_program = "non_existent_compiler_xyz"
        self.panel.stop_btn.setEnabled(True)
        self.panel._on_error(QProcess.ProcessError.FailedToStart)

        self.assertFalse(self.panel.stop_btn.isEnabled(), "stop_btn muss nach FailedToStart deaktiviert sein")
        self.assertIn("Fehler", self.panel.status_label.text())
        self.assertIn("nicht gestartet werden", self.panel.output.toPlainText())
        self.assertEqual(len(emitted_results), 1)
        self.assertEqual(emitted_results[0][0], -1)

    def test_run_command_crashed_updates_status(self):
        """Absturz eines Prozesses muss im Statuslabel und Output protokolliert werden."""
        self.panel._current_program = "crashing_app"
        self.panel.stop_btn.setEnabled(True)
        self.panel._on_error(QProcess.ProcessError.Crashed)

        self.assertFalse(self.panel.stop_btn.isEnabled())
        self.assertIn("abgestürzt", self.panel.status_label.text())
        self.assertIn("abgestürzt", self.panel.output.toPlainText())

    def test_output_panel_close_event_terminates_running_process(self):
        """Beim Schließen des Panels muss ein aktiver Prozess beendet werden."""
        mock_proc = MagicMock()
        mock_proc.state.return_value = QProcess.ProcessState.Running
        self.panel.process = mock_proc

        self.panel.close()
        mock_proc.kill.assert_called_once()
        mock_proc.waitForFinished.assert_called_once_with(1000)


if __name__ == "__main__":
    unittest.main()
