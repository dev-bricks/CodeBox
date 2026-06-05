"""Regressionstests für ProjectView in features/project_view.py."""
from pathlib import Path
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QApplication, QMessageBox

from features.project_view import ProjectView


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_new_file_in_shows_error_on_write_failure(tmp_path):
    """Regression (B-008): _new_file_in() muss OSError abfangen und eine
    Fehlermeldung zeigen, statt die Ausnahme unkontrolliert zu propagieren."""
    _ensure_app()
    view = ProjectView()

    directory = tmp_path / "projekt"
    directory.mkdir()

    with (
        patch("PySide6.QtWidgets.QInputDialog.getText",
              return_value=("neue_datei.py", True)),
        patch("pathlib.Path.write_text", side_effect=OSError("Schreibgeschützt")),
        patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critical,
    ):
        view._new_file_in(directory)

    mock_critical.assert_called_once()
    args = mock_critical.call_args[0]
    assert "Schreibgeschützt" in args[2] or "Schreibgeschützt" in str(args)

    view.close()


def test_new_file_in_emits_signal_on_success(tmp_path):
    """_new_file_in() öffnet die neue Datei, wenn das Anlegen erfolgreich war."""
    _ensure_app()
    view = ProjectView()

    directory = tmp_path / "projekt"
    directory.mkdir()

    emitted = []
    view.fileDoubleClicked.connect(emitted.append)

    with patch("PySide6.QtWidgets.QInputDialog.getText",
               return_value=("test.py", True)):
        view._new_file_in(directory)

    assert len(emitted) == 1
    assert emitted[0].name == "test.py"

    view.close()
