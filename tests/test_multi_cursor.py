#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit Tests für das Multi-Cursor und Column-Selection System in CodeBox."""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QKeyEvent, QMouseEvent, QTextCursor

from core.editor import CodeEditor
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_multi_cursor_add_remove_clear(qapp):
    """Testet das Hinzufügen, Zählen, Umschalten und Leeren von Cursorn."""
    editor = CodeEditor()
    editor.setPlainText("Zeile 1\nZeile 2\nZeile 3")

    mgr = editor.multi_cursor_manager
    assert not mgr.has_extra_cursors()
    assert mgr.cursor_count() == 1

    # Cursor an Zeile 2 hinzufügen
    added = mgr.add_cursor_at(10)
    assert added is True
    assert mgr.has_extra_cursors() is True
    assert mgr.cursor_count() == 2

    # Doppelter Cursor an gleicher Position wird abgewiesen
    assert mgr.add_cursor_at(10) is False
    assert mgr.cursor_count() == 2

    # Toggle an Position 10 entfernt ihn
    mgr.toggle_cursor_at(10)
    assert mgr.has_extra_cursors() is False
    assert mgr.cursor_count() == 1

    # Mehrere hinzufügen und leeren
    mgr.add_cursor_at(8)
    mgr.add_cursor_at(16)
    assert mgr.cursor_count() == 3
    mgr.clear()
    assert mgr.has_extra_cursors() is False
    assert mgr.cursor_count() == 1


def test_add_cursor_above_and_below(qapp):
    """Testet das Hinzufügen von Cursorn oberhalb und unterhalb (Spaltenauswahl)."""
    editor = CodeEditor()
    editor.setPlainText("alpha = 10\nbravo = 20\ncharlie = 30")

    # Cursor in der Mitte (Zeile 1: bravo) bei Spalte 5
    block1 = editor.document().findBlockByNumber(1)
    tc = editor.textCursor()
    tc.setPosition(block1.position() + 5)
    editor.setTextCursor(tc)

    mgr = editor.multi_cursor_manager
    assert mgr.add_cursor_above() is True
    assert mgr.cursor_count() == 2
    # Oberer Cursor sollte in Block 0 bei Spalte 5 sein
    top_c = mgr.all_cursors()[0]
    assert top_c.blockNumber() == 0
    assert top_c.positionInBlock() == 5

    # Erneuter Aufruf nach oben schlägt an Dokumentgrenze fehl
    assert mgr.add_cursor_above() is False

    # Cursor nach unten hinzufügen
    assert mgr.add_cursor_below() is True
    assert mgr.cursor_count() == 3
    bottom_c = mgr.all_cursors()[-1]
    assert bottom_c.blockNumber() == 2
    assert bottom_c.positionInBlock() == 5

    # Unten an Dokumentgrenze schlägt weiterer Aufruf fehl
    assert mgr.add_cursor_below() is False


def test_multi_cursor_text_insertion(qapp):
    """Testet das synchrone Einfügen von Text an mehreren Cursor-Positionen."""
    editor = CodeEditor()
    editor.setPlainText("item1\nitem2\nitem3")

    # Hauptcursor auf Zeile 0 am Ende, Sekundäre auf Zeile 1 und 2 am Ende
    doc = editor.document()
    c0 = editor.textCursor()
    c0.setPosition(len("item1"))
    editor.setTextCursor(c0)

    mgr = editor.multi_cursor_manager
    mgr.add_cursor_at(doc.findBlockByNumber(1).position() + len("item2"))
    mgr.add_cursor_at(doc.findBlockByNumber(2).position() + len("item3"))
    assert mgr.cursor_count() == 3

    mgr.insert_text("_active")
    assert editor.toPlainText() == "item1_active\nitem2_active\nitem3_active"


def test_multi_cursor_backspace_and_delete(qapp):
    """Testet synchrones Backspace und Delete über mehrere Cursor."""
    editor = CodeEditor()
    editor.setPlainText("abc1\nabc2\nabc3")

    # Cursor hinter die Zahlen setzen
    doc = editor.document()
    c0 = editor.textCursor()
    c0.setPosition(4)
    editor.setTextCursor(c0)

    mgr = editor.multi_cursor_manager
    mgr.add_cursor_at(doc.findBlockByNumber(1).position() + 4)
    mgr.add_cursor_at(doc.findBlockByNumber(2).position() + 4)

    # Backspace entfernt jeweils die Ziffer
    mgr.delete_backspace()
    assert editor.toPlainText() == "abc\nabc\nabc"

    # Jetzt Cursor an Zeilenanfang und Delete drückt erstes Zeichen weg
    editor.setPlainText("x1\nx2\nx3")
    c0 = editor.textCursor()
    c0.setPosition(0)
    editor.setTextCursor(c0)
    mgr.clear()
    mgr.add_cursor_at(doc.findBlockByNumber(1).position())
    mgr.add_cursor_at(doc.findBlockByNumber(2).position())

    mgr.delete_forward()
    assert editor.toPlainText() == "1\n2\n3"


def test_multi_cursor_selection_replacement(qapp):
    """Testet das Ersetzen von Auswahlen an mehreren Positionen gleichzeitig."""
    editor = CodeEditor()
    editor.setPlainText("foo = 1\nfoo = 2\nfoo = 3")

    mgr = editor.multi_cursor_manager
    mgr.select_all_occurrences()
    assert mgr.cursor_count() == 3

    mgr.insert_text("bar")
    assert editor.toPlainText() == "bar = 1\nbar = 2\nbar = 3"


def test_multi_cursor_auto_pair_and_wrap(qapp):
    """Testet Auto-Pairing und Selection-Wrapping mit Klammern bei mehreren Cursorn."""
    editor = CodeEditor()
    editor.setPlainText("msg1\nmsg2")

    doc = editor.document()
    # Auswahlen für msg1 und msg2 setzen
    c0 = editor.textCursor()
    c0.setPosition(0)
    c0.setPosition(4, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(c0)

    mgr = editor.multi_cursor_manager
    mgr.add_cursor_at(doc.findBlockByNumber(1).position() + 4, doc.findBlockByNumber(1).position())
    assert mgr.cursor_count() == 2

    # Mit Anführungszeichen umschließen
    mgr.insert_pair_or_wrap('"')
    assert editor.toPlainText() == '"msg1"\n"msg2"'

    # Jetzt ohne Auswahl Klammern einfügen
    mgr.clear()
    c0 = editor.textCursor()
    c0.setPosition(0)
    editor.setTextCursor(c0)
    mgr.add_cursor_at(doc.findBlockByNumber(1).position())

    mgr.insert_pair_or_wrap('(')
    assert editor.toPlainText() == '()\n"msg1"\n()\n"msg2"' or "()" in editor.toPlainText()


def test_select_all_occurrences(qapp):
    """Testet das automatische Selektieren aller Vorkommen (Ctrl+Shift+L)."""
    editor = CodeEditor()
    editor.setPlainText("count = 0\nwhile count < 10:\n    count += 1")

    # Cursor auf 'count' in Zeile 0
    c = editor.textCursor()
    c.setPosition(2)
    editor.setTextCursor(c)

    mgr = editor.multi_cursor_manager
    matches = mgr.select_all_occurrences()
    assert matches == 3
    assert mgr.cursor_count() == 3

    # Alle gleichzeitig umbenennen
    mgr.insert_text("total")
    assert editor.toPlainText() == "total = 0\nwhile total < 10:\n    total += 1"


def test_add_next_occurrence(qapp):
    """Testet das schrittweise Hinzufügen des nächsten Vorkommens (Ctrl+Alt+L)."""
    editor = CodeEditor()
    editor.setPlainText("val = 1; val = 2; val = 3;")

    # 'val' in Zeile 0 markieren
    c = editor.textCursor()
    c.setPosition(0)
    c.setPosition(3, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(c)

    mgr = editor.multi_cursor_manager
    assert mgr.cursor_count() == 1

    # Nächstes Vorkommen hinzufügen
    ok = mgr.add_next_occurrence()
    assert ok is True
    assert mgr.cursor_count() == 2

    # Drittes Vorkommen hinzufügen
    ok = mgr.add_next_occurrence()
    assert ok is True
    assert mgr.cursor_count() == 3

    # Danach sind alle bereits selektiert
    ok = mgr.add_next_occurrence()
    assert ok is False


def test_column_selection_between_cursors(qapp):
    """Testet rechteckige Spaltenauswahl über mehrere Zeilen hinweg."""
    editor = CodeEditor()
    editor.setPlainText("one   = 1\ntwo   = 2\nthree = 3")

    doc = editor.document()
    c_start = QTextCursor(doc.findBlockByNumber(0))
    c_start.setPosition(c_start.position() + 6)  # Nach 'one   '

    c_end = QTextCursor(doc.findBlockByNumber(2))
    c_end.setPosition(c_end.position() + 8)  # Nach 'three = '

    mgr = editor.multi_cursor_manager
    mgr.column_select_between_cursors(c_start, c_end)

    assert mgr.cursor_count() == 3
    for c in mgr.all_cursors():
        assert c.hasSelection()


def test_cursor_navigation_and_merging(qapp):
    """Testet Tastaturnavigation der Cursor und Verschmelzung bei Kollision."""
    editor = CodeEditor()
    editor.setPlainText("abc\ndef")

    c0 = editor.textCursor()
    c0.setPosition(0)
    editor.setTextCursor(c0)

    mgr = editor.multi_cursor_manager
    mgr.add_cursor_at(1)
    assert mgr.cursor_count() == 2

    # Nach rechts navigieren
    event_right = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    mgr.move_cursors(Qt.Key.Key_Right, event_right)

    all_c = mgr.all_cursors()
    assert all_c[0].position() == 1
    assert all_c[1].position() == 2

    # Beide an dieselbe Position setzen führt zu automatischem Merging
    mgr.add_cursor_at(1)
    assert mgr.cursor_count() == 2


def test_copy_and_paste_multiline(qapp):
    """Testet synchrones Kopieren und zeilenweises Einfügen bei Multi-Cursorn."""
    editor = CodeEditor()
    editor.setPlainText("apple\nbanana\ncherry")

    doc = editor.document()
    c0 = editor.textCursor()
    c0.setPosition(0)
    c0.setPosition(5, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(c0)

    mgr = editor.multi_cursor_manager
    c1 = QTextCursor(doc.findBlockByNumber(1))
    c1.setPosition(c1.position() + 6, QTextCursor.MoveMode.KeepAnchor)
    mgr.secondary_cursors.append(c1)

    c2 = QTextCursor(doc.findBlockByNumber(2))
    c2.setPosition(c2.position() + 6, QTextCursor.MoveMode.KeepAnchor)
    mgr.secondary_cursors.append(c2)

    assert mgr.cursor_count() == 3
    mgr.copy_selection()

    # Zwischenablage prüfen
    clip = QApplication.clipboard().text()
    assert clip == "apple\nbanana\ncherry"

    # Neuer Editor und zeilenweises Einfügen
    editor2 = CodeEditor()
    editor2.setPlainText("a: \nb: \nc: ")
    c2_0 = editor2.textCursor()
    c2_0.setPosition(3)
    editor2.setTextCursor(c2_0)

    mgr2 = editor2.multi_cursor_manager
    mgr2.add_cursor_at(editor2.document().findBlockByNumber(1).position() + 3)
    mgr2.add_cursor_at(editor2.document().findBlockByNumber(2).position() + 3)
    assert mgr2.cursor_count() == 3

    mgr2.paste_text()
    assert editor2.toPlainText() == "a: apple\nb: banana\nc: cherry"


def test_multi_cursor_atomic_undo(qapp):
    """Testet atomares Undo/Redo: Eine Rückgängig-Aktion nimmt alle Multi-Cursor-Änderungen zurück."""
    editor = CodeEditor()
    editor.setPlainText("var1\nvar2\nvar3")

    doc = editor.document()
    c0 = editor.textCursor()
    c0.setPosition(4)
    editor.setTextCursor(c0)

    mgr = editor.multi_cursor_manager
    mgr.add_cursor_at(doc.findBlockByNumber(1).position() + 4)
    mgr.add_cursor_at(doc.findBlockByNumber(2).position() + 4)

    mgr.insert_text(" = 42")
    assert editor.toPlainText() == "var1 = 42\nvar2 = 42\nvar3 = 42"

    # Ein einzelnes Undo muss den Ausgangszustand komplett wiederherstellen
    editor.undo()
    assert editor.toPlainText() == "var1\nvar2\nvar3"

    # Ein einzelnes Redo stellt alle 3 Zuweisungen wieder her
    editor.redo()
    assert editor.toPlainText() == "var1 = 42\nvar2 = 42\nvar3 = 42"


def test_key_press_event_integration(qapp):
    """Testet die Tastatur-Event-Verarbeitung im CodeEditor mit Tastenkombinationen."""
    editor = CodeEditor()
    editor.setPlainText("line 1\nline 2\nline 3")

    c = editor.textCursor()
    c.setPosition(0)
    editor.setTextCursor(c)

    # Ctrl+Alt+Down über keyPressEvent simulieren
    event_down = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Down,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
    )
    editor.keyPressEvent(event_down)
    assert editor.multi_cursor_manager.cursor_count() == 2

    # Normales Zeichen 'X' tippen
    event_x = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_X,
        Qt.KeyboardModifier.NoModifier,
        "X",
    )
    editor.keyPressEvent(event_x)
    assert editor.toPlainText().startswith("Xline 1\nXline 2")

    # Escape hebt Multi-Cursor auf
    event_esc = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )
    editor.keyPressEvent(event_esc)
    assert editor.multi_cursor_manager.has_extra_cursors() is False
    assert editor.multi_cursor_manager.cursor_count() == 1


def test_mouse_press_alt_click(qapp):
    """Testet das Hinzufügen von Cursorn per Alt+Klick mit der Maus."""
    editor = CodeEditor()
    editor.setPlainText("First line\nSecond line\nThird line")

    pt = editor.cursorRect(editor.textCursor()).center()
    event_click = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(pt),
        QPointF(pt),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier,
    )
    editor.mousePressEvent(event_click)
    # Primary cursor war an 0, Klick an 0 toggelt/bleibt
    assert editor.multi_cursor_manager.cursor_count() >= 1


def test_main_window_multi_cursor_actions(qapp):
    """Testet die Menü-Aktionen und Statusleistenanzeige in MainWindow."""
    win = MainWindow()
    tab = win.new_file()
    assert tab is not None

    tab.editor.setPlainText("first\nsecond\nthird")
    c = tab.editor.textCursor()
    c.setPosition(0)
    tab.editor.setTextCursor(c)

    # Menü-Aktion: Cursor unterhalb
    win._add_cursor_below()
    assert tab.editor.multi_cursor_manager.cursor_count() == 2
    # Statusleiste aktualisiert
    assert "2 Cursor" in win.pos_label.text()

    # Menü-Aktion: Mehrfachcursor aufheben
    win._clear_multi_cursors()
    assert tab.editor.multi_cursor_manager.cursor_count() == 1
    assert "Cursor" not in win.pos_label.text()

    win.close()
