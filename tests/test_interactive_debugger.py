#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for interactive console input and debugger integration in CodeBox."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.output import OutputPanel
from languages.python_lang import PythonProvider
from ui.main_window import MainWindow


@pytest.fixture
def qt_app():
    instance = QApplication.instance()
    if not instance:
        instance = QApplication([])
    return instance


def test_console_input_history_navigation(qt_app):
    panel = OutputPanel()
    assert panel.history == []
    assert panel.history_index == -1

    # Simulate entering commands
    panel.history.extend(["first_cmd", "second_cmd"])
    panel.history_index = len(panel.history)

    # Press Key_Up on input_edit -> "second_cmd"
    up_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
    panel.input_edit.keyPressEvent(up_event)
    assert panel.input_edit.text() == "second_cmd"
    assert panel.history_index == 1

    # Press Key_Up again -> "first_cmd"
    panel.input_edit.keyPressEvent(up_event)
    assert panel.input_edit.text() == "first_cmd"
    assert panel.history_index == 0

    # Press Key_Down -> "second_cmd"
    down_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
    panel.input_edit.keyPressEvent(down_event)
    assert panel.input_edit.text() == "second_cmd"
    assert panel.history_index == 1

    # Press Key_Down -> blank
    panel.input_edit.keyPressEvent(down_event)
    assert panel.input_edit.text() == ""
    assert panel.history_index == 2


def test_output_panel_input_controls(qt_app):
    panel = OutputPanel()
    assert panel.input_edit is not None
    assert panel.send_btn is not None
    assert panel.is_debugging is False

    # Check accessible attributes
    assert panel.input_edit.accessibleName() == "Prozess-Eingabe"
    assert panel.send_btn.accessibleName() == "Eingabe senden"

    # Test send_input when process is not running (should not crash)
    sent_inputs = []
    panel.inputSent.connect(sent_inputs.append)
    panel.send_input("help")
    assert sent_inputs == ["help"]
    assert "help" in panel.history
    assert panel.input_edit.text() == ""

    panel.show()

    # Test debug mode activation
    panel.set_debug_mode(True)
    assert panel.is_debugging is True
    assert not panel.continue_btn.isHidden()
    assert not panel.step_over_btn.isHidden()
    assert not panel.step_into_btn.isHidden()
    assert not panel.step_out_btn.isHidden()
    assert panel.continue_btn.isEnabled() is True
    assert panel.step_over_btn.isEnabled() is True
    assert panel.step_into_btn.isEnabled() is True
    assert panel.step_out_btn.isEnabled() is True

    # Test clicking debug buttons emits inputSent with appropriate commands
    panel.continue_btn.click()
    assert sent_inputs[-1] == "c"

    panel.step_over_btn.click()
    assert sent_inputs[-1] == "n"

    panel.step_into_btn.click()
    assert sent_inputs[-1] == "s"

    panel.step_out_btn.click()
    assert sent_inputs[-1] == "r"

    # Test turning debug mode off
    panel.set_debug_mode(False)
    assert panel.is_debugging is False
    assert panel.continue_btn.isHidden()
    assert panel.step_over_btn.isHidden()
    assert panel.step_into_btn.isHidden()
    assert panel.step_out_btn.isHidden()

    panel.close()


def test_python_provider_debug_command():
    provider = PythonProvider()
    cmd = provider.get_debug_command("script.py")
    assert cmd is not None
    assert "-u" in cmd
    assert "-m" in cmd
    assert "pdb" in cmd
    assert cmd[-1] == "script.py"


def test_main_window_debugger_actions(qt_app, tmp_path):
    win = MainWindow()
    win.resize(600, 400)
    win.show()

    test_file = tmp_path / "calc.py"
    test_file.write_text("a = 10\nb = 20\nprint(a + b)\n", encoding="utf-8")
    win.open_path(test_file)

    tab = win.get_active_tab()
    assert tab is not None
    assert tab.editor is not None

    # Set a breakpoint on line 2
    tab.editor.set_breakpoints([2])

    # Trigger debug_current
    recorded_calls = []

    def mock_run_command(cmd, is_debug=False, initial_commands=None):
        recorded_calls.append((cmd, is_debug, initial_commands))

    win.output.run_command = mock_run_command

    win.debug_current()
    assert len(recorded_calls) == 1
    cmd, is_debug, initial_cmds = recorded_calls[0]
    assert is_debug is True
    assert initial_cmds == ["b 2"]
    assert cmd[-1] == str(test_file)

    # Test debug step helper methods
    sent_commands = []
    win.output.send_input = lambda text: sent_commands.append(text)

    win.debug_step_over()
    assert sent_commands[-1] == "n"

    win.debug_step_into()
    assert sent_commands[-1] == "s"

    win.debug_step_out()
    assert sent_commands[-1] == "r"

    win.debug_continue()
    assert sent_commands[-1] == "c"

    win.close()
