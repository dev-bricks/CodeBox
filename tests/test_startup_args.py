from unittest.mock import patch

import main


def test_parse_launch_args_supports_open_flag_and_positional(tmp_path):
    target = tmp_path / "script.py"

    startup_path, qt_args = main.parse_launch_args(
        ["--open", str(target), "--platform", "offscreen"]
    )
    assert startup_path == target
    assert qt_args == ["--platform", "offscreen"]

    startup_path, qt_args = main.parse_launch_args([str(target)])
    assert startup_path == target
    assert qt_args == []


def test_main_opens_startup_file_from_open_flag(tmp_path):
    target = tmp_path / "script.py"
    target.write_text("print('hi')\n", encoding="utf-8")
    captured = []

    with (
        patch("features.terminal.TerminalWidget._start_shell", lambda self: None),
        patch("ui.main_window.MainWindow.show", lambda self: captured.append(self)),
        patch("PySide6.QtWidgets.QApplication.exec", return_value=0),
    ):
        exit_code = main.main(["--open", str(target)])

    assert exit_code == 0
    assert len(captured) == 1

    window = captured[0]
    try:
        assert window.tab_widget.count() == 1
        tab = window.tab_widget.current_tab()
        assert tab is not None
        assert tab.file_path == target
        assert window.tab_widget.tabText(window.tab_widget.currentIndex()) == "script.py"
    finally:
        window.close()
