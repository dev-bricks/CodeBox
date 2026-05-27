from __future__ import annotations

from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication, QMessageBox

from core.tabs import TabWidget
from ui.main_window import MainWindow


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_close_tab_keeps_modified_tab_open_when_save_fails():
    _ensure_app()
    widget = TabWidget()
    tab = widget.new_tab()
    tab.is_modified = True

    with (
        patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save),
        patch.object(tab, "save", return_value=False),
    ):
        widget.close_tab(0)

    assert widget.count() == 1
    assert widget.tabs[0] is tab
    assert widget.current_tab() is tab

    widget.close()


def test_run_current_does_not_execute_when_save_fails(tmp_path):
    _ensure_app()

    with patch("features.terminal.TerminalWidget._start_shell", lambda self: None):
        window = MainWindow()

    tab = window.tab_widget.current_tab()
    assert tab is not None

    tab.file_path = tmp_path / "script.py"
    tab.provider = type(
        "DummyProvider",
        (),
        {"get_run_command": staticmethod(lambda file_path: ["python", file_path])},
    )()
    window.output.run_command = Mock()

    with patch.object(tab, "save", return_value=False):
        window.run_current()

    window.output.run_command.assert_not_called()

    window.close()


def test_initial_save_updates_tab_title_and_enables_run(tmp_path):
    _ensure_app()

    with patch("features.terminal.TerminalWidget._start_shell", lambda self: None):
        window = MainWindow()

    tab = window.tab_widget.current_tab()
    assert tab is not None

    target = tmp_path / "script.py"
    tab.editor.setPlainText("print('hi')")

    with patch(
        "ui.main_window.QFileDialog.getSaveFileName",
        return_value=(str(target), "Python (*.py)"),
    ):
        window.save_file()

    current_index = window.tab_widget.currentIndex()
    assert tab.file_path == target
    assert window.tab_widget.tabText(current_index) == "script.py"
    assert window.output.run_btn.isEnabled()

    window.close()


def test_initial_save_failure_restores_untitled_state():
    _ensure_app()

    with patch("features.terminal.TerminalWidget._start_shell", lambda self: None):
        window = MainWindow()

    tab = window.tab_widget.current_tab()
    assert tab is not None
    original_index = window.tab_widget.currentIndex()
    original_label = window.lang_label.text()

    with (
        patch(
            "ui.main_window.QFileDialog.getSaveFileName",
            return_value=("C:/tmp/never-written.py", "Python (*.py)"),
        ),
        patch("pathlib.Path.write_text", side_effect=OSError("disk full")),
        patch("PySide6.QtWidgets.QMessageBox.critical", return_value=None),
    ):
        window.save_file()

    assert tab.file_path is None
    assert window.tab_widget.tabText(original_index) == "Unbenannt"
    assert window.lang_label.text() == original_label
    assert not window.output.run_btn.isEnabled()

    window.close()
