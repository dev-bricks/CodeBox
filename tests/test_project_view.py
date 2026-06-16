"""Regressionstests für ProjectView und Pfadsync im Hauptfenster."""
from pathlib import Path
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QApplication, QMessageBox

from features.project_view import ProjectView
from ui.main_window import MainWindow


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


def test_project_view_root_follows_current_file_directory(tmp_path):
    """Regression (B-009): Der Projektbaum muss beim Dateiwechsel auf einen
    anderen Ordner dem aktuell geöffneten Tab folgen."""
    _ensure_app()
    first_dir = tmp_path / "eins"
    second_dir = tmp_path / "zwei"
    first_dir.mkdir()
    second_dir.mkdir()
    first_file = first_dir / "alpha.py"
    second_file = second_dir / "beta.py"
    first_file.write_text("print('eins')\n", encoding="utf-8")
    second_file.write_text("print('zwei')\n", encoding="utf-8")

    with patch("features.terminal.TerminalWidget._start_shell", lambda self: None):
        window = MainWindow()

    try:
        window.open_path(first_file)
        assert window.project_view._root_path == first_dir

        window.open_path(second_file)
        assert window.project_view._root_path == second_dir
    finally:
        window.close()
