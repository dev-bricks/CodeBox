#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.debugger import (
    StackFrame,
    WatchExpression,
    parse_pdb_eval_response,
    parse_pdb_stack,
    safe_eval_expression,
)
from core.output import OutputPanel
from ui.debug_panel import DebugPanel
from ui.main_window import MainWindow


@pytest.fixture
def qt_app():
    instance = QApplication.instance()
    if not instance:
        instance = QApplication([])
    return instance


# -------------------------------------------------------------------------
# Core Debugger Logic Tests
# -------------------------------------------------------------------------


def test_stack_frame_properties():
    frame = StackFrame(
        file_path="C:/projects/app/main.py",
        line_number=42,
        function_name="calculate",
        code_line="return x + y",
        is_current=True,
        frame_index=1,
    )
    assert frame.file_name == "main.py"
    assert frame.location() == "main.py:42"
    assert "▶" in frame.display_frame()
    assert "[1] calculate" in frame.display_frame()

    d = frame.to_dict()
    assert d["file_path"] == "C:/projects/app/main.py"
    assert d["line_number"] == 42
    assert d["is_current"] is True


def test_watch_expression_properties():
    watch = WatchExpression(expression="len(items)")
    assert watch.expression == "len(items)"
    assert watch.value == "<nicht ausgewertet>"
    assert watch.status == "pending"

    d = watch.to_dict()
    assert d["expression"] == "len(items)"
    assert d["status"] == "pending"


def test_parse_pdb_stack_windows():
    pdb_output = """  c:\\myproject\\main.py(42)<module>()
-> res = run_calc(10)
> c:\\myproject\\calc.py(15)run_calc()
-> return x * 2
(Pdb) """
    frames = parse_pdb_stack(pdb_output)
    assert len(frames) == 2

    assert frames[0].file_path == "c:\\myproject\\main.py"
    assert frames[0].line_number == 42
    assert frames[0].function_name == "<module>()"
    assert frames[0].code_line == "res = run_calc(10)"
    assert frames[0].is_current is False
    assert frames[0].frame_index == 0

    assert frames[1].file_path == "c:\\myproject\\calc.py"
    assert frames[1].line_number == 15
    assert frames[1].function_name == "run_calc()"
    assert frames[1].code_line == "return x * 2"
    assert frames[1].is_current is True
    assert frames[1].frame_index == 1


def test_parse_pdb_stack_unix():
    pdb_output = """/home/dev/app.py(8)<module>()
-> worker(a, b)
> /home/dev/app.py(3)worker(x=1, y=2)
-> return x + y"""
    frames = parse_pdb_stack(pdb_output)
    assert len(frames) == 2
    assert frames[0].file_path == "/home/dev/app.py"
    assert frames[0].line_number == 8
    assert frames[1].is_current is True
    assert frames[1].line_number == 3
    assert frames[1].function_name == "worker(x=1, y=2)"


def test_parse_pdb_eval_response():
    # Int evaluation
    val, typ, status = parse_pdb_eval_response("x", "42\n(Pdb) ")
    assert val == "42"
    assert typ == "int"
    assert status == "ok"

    # String evaluation
    val, typ, status = parse_pdb_eval_response("name", "'CodeBox'\n")
    assert val == "'CodeBox'"
    assert typ == "str"
    assert status == "ok"

    # Error evaluation
    val, typ, status = parse_pdb_eval_response("bad_var", "*** NameError: name 'bad_var' is not defined\n(Pdb) ")
    assert "NameError" in typ
    assert status == "error"


def test_safe_eval_expression():
    # Math with builtins
    val, typ, status = safe_eval_expression("len([1, 2, 3]) + min(10, 5)")
    assert val == "8"
    assert typ == "int"
    assert status == "ok"

    # Context evaluation
    val, typ, status = safe_eval_expression("a * b", {"a": 6, "b": 7})
    assert val == "42"
    assert typ == "int"
    assert status == "ok"

    # Error handling
    val, typ, status = safe_eval_expression("unknown_variable")
    assert status == "error"
    assert "NameError" in typ


# -------------------------------------------------------------------------
# UI DebugPanel Component Tests
# -------------------------------------------------------------------------


def test_debug_panel_watch_lifecycle(qt_app):
    panel = DebugPanel()
    assert panel.is_session_active() is False

    # Check headers and accessibility
    assert panel.watch_tree.accessibleName() == "Watch-Expressions Tabelle"
    assert panel.stack_tree.accessibleName() == "Call-Stack Tabelle"

    # Add watch
    added = panel.add_watch("total_count")
    assert added is True
    watches = panel.get_watches()
    assert len(watches) == 1
    assert watches[0]["expression"] == "total_count"
    assert watches[0]["status"] == "pending"

    # Set value
    panel.set_watch_value("total_count", "150", "int", "ok")
    watches = panel.get_watches()
    assert watches[0]["value"] == "150"
    assert watches[0]["type_name"] == "int"
    assert watches[0]["status"] == "ok"

    # Evaluate with local context
    panel.add_watch("x + y")
    panel.evaluate_all_local({"x": 10, "y": 20})
    watches_dict = {w["expression"]: w for w in panel.get_watches()}
    assert watches_dict["x + y"]["value"] == "30"
    assert watches_dict["x + y"]["type_name"] == "int"

    # Remove watch
    panel.remove_watch("total_count")
    assert len(panel.get_watches()) == 1
    assert panel.get_watches()[0]["expression"] == "x + y"

    # Clear watches
    panel.clear_watches()
    assert len(panel.get_watches()) == 0


def test_debug_panel_keyboard_events(qt_app):
    panel = DebugPanel()
    panel.add_watch("test_var")
    assert panel.watch_tree.topLevelItemCount() == 1

    item = panel.watch_tree.topLevelItem(0)
    panel.watch_tree.setCurrentItem(item)

    # Press Delete on watch tree
    del_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    panel.watch_tree.keyPressEvent(del_event)
    assert panel.watch_tree.topLevelItemCount() == 0

    # Test CallStack keyboard Enter
    frames = [
        StackFrame(file_path="foo.py", line_number=10, function_name="bar", code_line="pass")
    ]
    panel.set_call_stack(frames)
    assert panel.stack_tree.topLevelItemCount() == 1

    activated_frames = []
    panel.frameActivated.connect(lambda f, line: activated_frames.append((f, line)))

    stack_item = panel.stack_tree.topLevelItem(0)
    panel.stack_tree.setCurrentItem(stack_item)

    enter_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)
    panel.stack_tree.keyPressEvent(enter_event)
    assert activated_frames == [("foo.py", 10)]


def test_debug_panel_call_stack_loading(qt_app):
    panel = DebugPanel()
    stack_text = """  main.py(5)<module>()
-> test()
> utils.py(12)test()
-> return 42"""
    panel.load_call_stack_text(stack_text)

    assert panel.is_session_active() is True
    assert panel.stack_count_label.text() == "(2 Frames)"
    assert panel.stack_tree.topLevelItemCount() == 2

    top_item = panel.stack_tree.topLevelItem(1)
    assert "utils.py" in top_item.text(2)
    assert top_item.text(3) == "12"

    # Jump top / current frame
    jumped = []
    panel.frameActivated.connect(lambda f, line: jumped.append((f, line)))
    panel._jump_to_current_frame()
    assert len(jumped) == 1
    assert jumped[0] == ("utils.py", 12)

    # Clear debug data
    panel.clear_debug_data()
    assert panel.stack_tree.topLevelItemCount() == 0
    assert panel.stack_count_label.text() == "(0 Frames)"


def test_debug_panel_quick_eval(qt_app):
    panel = DebugPanel()
    panel.eval_input.setText("10 * 5")
    panel._on_eval_clicked()

    assert "= 50" in panel.eval_result_label.text()
    assert panel.add_eval_to_watch_btn.isEnabled() is True

    # Add evaluated to watch list
    panel._on_add_eval_to_watch()
    watches = panel.get_watches()
    assert any(w["expression"] == "10 * 5" for w in watches)


def test_debug_panel_output_attachment(qt_app):
    output = OutputPanel()
    debug = DebugPanel()
    debug.attach_output_panel(output)

    assert debug.is_session_active() is False

    # Simulate stepping command sent
    output.send_input("n")
    assert debug.is_session_active() is True

    # Simulate process finished
    output._on_finished(0, 0)
    assert debug.is_session_active() is False


# -------------------------------------------------------------------------
# MainWindow Integration Tests
# -------------------------------------------------------------------------


def test_main_window_debug_panel_integration(qt_app, tmp_path):
    win = MainWindow()
    win.resize(800, 600)
    win.show()

    # Verify DebugPanel is added to bottom_tabs
    assert hasattr(win, "debug_panel")
    assert win.bottom_tabs.count() == 5
    assert win.bottom_tabs.tabText(4) == "Debugger"
    assert "Überwachungsausdrücke" in win.bottom_tabs.tabToolTip(4)

    # Test show_debug_panel
    win.show_debug_panel()
    assert win.bottom_tabs.currentWidget() == win.debug_panel

    # Test add_watch_expression
    win.add_watch_expression("user_token")
    watches = win.debug_panel.get_watches()
    assert len(watches) == 1
    assert watches[0]["expression"] == "user_token"

    # Test frame activation jumps to file and line in editor
    test_code_file = tmp_path / "service.py"
    test_code_file.write_text("def do_service():\n    step_1 = True\n    return step_1\n", encoding="utf-8")
    win.open_path(test_code_file)

    win._on_debug_frame_activated(str(test_code_file), line_number=2)
    tab = win.get_active_tab()
    assert tab is not None
    assert tab.editor.textCursor().blockNumber() == 1  # 0-based for line 2

    # Verify run_menu has debugger actions
    actions = [a.text() for a in win.run_menu.actions()]
    assert "Debugger-Panel anzeigen" in actions
    assert "Ausdruck überwachen..." in actions
    assert "Aufruf-Stapel aktualisieren" in actions

    # Verify editor context menu emits addWatchRequested
    requested_watches = []
    tab.editor.addWatchRequested.connect(requested_watches.append)
    tab.editor.addWatchRequested.emit("my_sample_var")
    assert "my_sample_var" in requested_watches

    win.close()
