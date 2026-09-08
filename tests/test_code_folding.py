#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit Tests für das Code-Folding System in CodeBox."""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent

from core.editor import CodeEditor
from core.folding import FoldDetector
from languages import PythonProvider


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_fold_detector_python_simple():
    code = """def hello():
    print("Hello")
    print("World")

class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hi {self.name}"
"""
    regions = FoldDetector.detect_python(code)
    assert len(regions) >= 3

    # def hello(): lines 0 to 2
    hello_reg = next(r for r in regions if r.name == "hello")
    assert hello_reg.start_line == 0
    assert hello_reg.end_line == 2
    assert hello_reg.kind == "function"

    # class Greeter: lines 4 to 9
    greeter_reg = next(r for r in regions if r.name == "Greeter")
    assert greeter_reg.start_line == 4
    assert greeter_reg.end_line == 9
    assert greeter_reg.kind == "class"

    # def greet: lines 8 to 9
    greet_reg = next(r for r in regions if r.name == "greet")
    assert greet_reg.start_line == 8
    assert greet_reg.end_line == 9
    assert greet_reg.kind == "function"


def test_fold_detector_python_async():
    code = """async def fetch_data():
    x = 1
    return x
"""
    regions = FoldDetector.detect_python(code)
    assert len(regions) == 1
    assert regions[0].name == "fetch_data"
    assert regions[0].start_line == 0
    assert regions[0].end_line == 2


def test_fold_detector_braces():
    code = """function add(a, b) {
    const sum = a + b;
    return sum;
}

class Calculator {
    multiply(a, b) {
        return a * b;
    }
}
"""
    regions = FoldDetector.detect_braces(code)
    assert len(regions) >= 3

    add_reg = next(r for r in regions if r.name == "add")
    assert add_reg.start_line == 0
    assert add_reg.end_line == 3

    calc_reg = next(r for r in regions if r.name == "Calculator")
    assert calc_reg.start_line == 5
    assert calc_reg.end_line == 9


def test_fold_detector_braces_ignore_strings_and_comments():
    code = """function test() {
    // some comment with { and }
    const str = "hello { bracket } world";
    return true;
}
"""
    regions = FoldDetector.detect_braces(code)
    assert len(regions) == 1
    assert regions[0].start_line == 0
    assert regions[0].end_line == 4


def test_editor_folding_toggle(qapp):
    editor = CodeEditor()
    editor.set_provider(PythonProvider())
    code = """def first():
    a = 1
    b = 2

def second():
    c = 3
    d = 4
"""
    editor.setPlainText(code)
    editor.update_folds()

    assert editor.is_line_foldable(0)
    assert not editor.is_line_folded(0)
    assert editor.is_line_foldable(4)

    # Zeile 0 einklappen
    success = editor.toggle_fold(0)
    assert success is True
    assert editor.is_line_folded(0)

    # Zeile 0 bleibt sichtbar, Zeilen 1 und 2 sind versteckt
    doc = editor.document()
    assert doc.findBlockByNumber(0).isVisible() is True
    assert doc.findBlockByNumber(1).isVisible() is False
    assert doc.findBlockByNumber(2).isVisible() is False
    # Zeile 4 bleibt sichtbar
    assert doc.findBlockByNumber(4).isVisible() is True

    # Erneut umschalten -> wieder sichtbar
    editor.toggle_fold(0)
    assert not editor.is_line_folded(0)
    assert doc.findBlockByNumber(1).isVisible() is True
    assert doc.findBlockByNumber(2).isVisible() is True


def test_editor_fold_all_unfold_all(qapp):
    editor = CodeEditor()
    editor.set_provider(PythonProvider())
    code = """def func_one():
    x = 10
    y = 20

def func_two():
    z = 30
"""
    editor.setPlainText(code)
    editor.update_folds()

    assert editor.is_line_foldable(0)
    assert editor.is_line_foldable(4)

    # Alles einklappen
    editor.fold_all()
    assert editor.is_line_folded(0)
    assert editor.is_line_folded(4)

    doc = editor.document()
    assert doc.findBlockByNumber(0).isVisible() is True
    assert doc.findBlockByNumber(1).isVisible() is False
    assert doc.findBlockByNumber(2).isVisible() is False
    assert doc.findBlockByNumber(4).isVisible() is True
    assert doc.findBlockByNumber(5).isVisible() is False

    # Alles ausklappen
    editor.unfold_all()
    assert not editor.is_line_folded(0)
    assert not editor.is_line_folded(4)
    assert doc.findBlockByNumber(1).isVisible() is True
    assert doc.findBlockByNumber(5).isVisible() is True


def test_folding_cursor_safety(qapp):
    editor = CodeEditor()
    editor.set_provider(PythonProvider())
    code = """def safe_test():
    step1 = 1
    step2 = 2
"""
    editor.setPlainText(code)
    editor.update_folds()

    # Cursor auf Zeile 2 setzen (in den versteckten Bereich)
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(2).position())
    editor.setTextCursor(cursor)
    assert editor.textCursor().blockNumber() == 2

    # Block einklappen
    editor.toggle_fold(0)

    # Cursor muss auf Zeile 0 (den sichtbaren Header) verschoben worden sein
    assert editor.textCursor().blockNumber() == 0


def test_toggle_fold_at_cursor(qapp):
    editor = CodeEditor()
    editor.set_provider(PythonProvider())
    code = """def at_cursor():
    val = 42
    return val
"""
    editor.setPlainText(code)
    editor.update_folds()

    # Cursor auf Zeile 1 innerhalb der Funktion
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position())
    editor.setTextCursor(cursor)

    # toggle_fold_at_cursor findet die umschließende Region
    res = editor.toggle_fold_at_cursor()
    assert res is True
    assert editor.is_line_folded(0)


def test_gutter_click_toggles_fold(qapp):
    editor = CodeEditor()
    editor.resize(400, 300)
    editor.show()
    editor.set_provider(PythonProvider())
    code = """def click_me():
    a = 1
    b = 2
"""
    editor.setPlainText(code)
    editor.update_folds()

    # Simuliere Klick im LineNumberArea auf Höhe der ersten Zeile
    gutter = editor.lineNumberArea
    pos = QPointF(float(gutter.width() - 5), 5.0)
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos,
        pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    gutter.mousePressEvent(event)

    assert editor.is_line_folded(0)


def test_mainwindow_folding_actions(qapp):
    from ui.main_window import MainWindow
    window = MainWindow()
    tab = window.tab_widget.current_tab()
    editor = tab.editor
    editor.set_provider(PythonProvider())
    editor.setPlainText("def sample():\n    return 10\n")
    editor.update_folds()

    assert editor.is_line_foldable(0)

    # Test MainWindow._fold_all
    window._fold_all()
    assert editor.is_line_folded(0)

    # Test MainWindow._unfold_all
    window._unfold_all()
    assert not editor.is_line_folded(0)

    # Test MainWindow._toggle_fold_current
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)
    window._toggle_fold_current()
    assert editor.is_line_folded(0)
    window.close()

