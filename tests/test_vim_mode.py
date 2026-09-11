#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit Tests für das modulare Vim-Keybindings System (Normal, Insert, Visual) in CodeBox."""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from core.editor import CodeEditor
from core.vim_mode import (
    VimMode,
    VimEngine,
    find_next_word_start,
    find_prev_word_start,
    find_next_word_end,
)
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.shortcuts_dialog import ShortcutsDialog, SHORTCUTS_DATA


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _send_key(editor: CodeEditor, key: Qt.Key, text: str = "", modifiers=Qt.KeyboardModifier.NoModifier):
    """Hilfsfunktion zum Senden eines QKeyEvent an den Editor."""
    event = QKeyEvent(QKeyEvent.Type.KeyPress, key, modifiers, text)
    editor.keyPressEvent(event)


def _type_chars(editor: CodeEditor, chars: str):
    """Hilfsfunktion zum nacheinander Senden von Zeichen im Normal-Mode."""
    for ch in chars:
        if ch.isdigit():
            key = getattr(Qt.Key, f"Key_{ch}", Qt.Key.Key_unknown)
            modifiers = Qt.KeyboardModifier.NoModifier
        elif ch.isalpha():
            key = getattr(Qt.Key, f"Key_{ch.upper()}", Qt.Key.Key_unknown)
            modifiers = Qt.KeyboardModifier.ShiftModifier if ch.isupper() else Qt.KeyboardModifier.NoModifier
        elif ch == ">":
            key = Qt.Key.Key_Greater
            modifiers = Qt.KeyboardModifier.ShiftModifier
        elif ch == "<":
            key = Qt.Key.Key_Less
            modifiers = Qt.KeyboardModifier.NoModifier
        else:
            key = Qt.Key.Key_unknown
            modifiers = Qt.KeyboardModifier.NoModifier
        _send_key(editor, key, ch, modifiers)


def test_vim_word_navigation_helpers():
    """Testet die Algorithmen zur Wort-Grenzen-Erkennung."""
    text = "hello   world.foo_bar(123)"
    # Wortanfänge:
    # 'hello' -> start=0, len=5
    # spaces: 5, 6, 7
    # 'world' -> start=8
    # '.' -> punct at 13
    # 'foo_bar' -> word at 14
    # '(' -> punct at 21
    # '123' -> word at 22
    assert find_next_word_start(text, 0) == 8
    assert find_next_word_start(text, 4) == 8
    assert find_next_word_start(text, 8) == 13
    assert find_next_word_start(text, 13) == 14
    assert find_next_word_start(text, 22) == 25
    assert find_next_word_start(text, 25) == len(text)

    # find_prev_word_start
    assert find_prev_word_start(text, 8) == 0
    assert find_prev_word_start(text, 10) == 8
    assert find_prev_word_start(text, 14) == 13
    assert find_prev_word_start(text, 13) == 8

    # find_next_word_end
    # 'hello' ends at 4
    assert find_next_word_end(text, 0) == 4
    # from 4, next word end is 'world' which ends at 12
    assert find_next_word_end(text, 4) == 12
    # '.' is single char punct at 13
    assert find_next_word_end(text, 12) == 13


def test_vim_mode_enum():
    """Prüft die definierten Zustände des VimMode Enums."""
    assert VimMode.NORMAL.value == "NORMAL"
    assert VimMode.INSERT.value == "INSERT"
    assert VimMode.VISUAL.value == "VISUAL"
    assert VimMode.VISUAL_LINE.value == "VISUAL_LINE"


def test_vim_engine_enable_disable(qapp):
    """Testet das Aktivieren und Deaktivieren des Vim-Modus."""
    editor = CodeEditor()
    engine = editor.vim_engine
    assert not engine.is_enabled()
    assert not editor.is_vim_mode_enabled()

    editor.set_vim_mode_enabled(True)
    assert engine.is_enabled()
    assert editor.is_vim_mode_enabled()
    assert engine.get_mode() == VimMode.NORMAL

    editor.set_vim_mode_enabled(False)
    assert not engine.is_enabled()
    assert not editor.is_vim_mode_enabled()


def test_vim_normal_navigation_hjkl(qapp):
    """Testet elementare h/j/k/l Navigation im Normal-Modus."""
    editor = CodeEditor()
    editor.setPlainText("Zeile 1\nZeile 2\nZeile 3")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'l' nach rechts
    _send_key(editor, Qt.Key.Key_L, "l")
    assert editor.textCursor().position() == 1

    # 'h' nach links
    _send_key(editor, Qt.Key.Key_H, "h")
    assert editor.textCursor().position() == 0

    # 'j' nach unten
    _send_key(editor, Qt.Key.Key_J, "j")
    assert editor.textCursor().blockNumber() == 1

    # 'k' nach oben
    _send_key(editor, Qt.Key.Key_K, "k")
    assert editor.textCursor().blockNumber() == 0


def test_vim_normal_word_movement_wbe(qapp):
    """Testet w, b und e Navigation im Normal-Modus."""
    editor = CodeEditor()
    editor.setPlainText("alpha beta gamma")
    editor.set_vim_mode_enabled(True)
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'w' springt zu 'beta' (Index 6)
    _send_key(editor, Qt.Key.Key_W, "w")
    assert editor.textCursor().position() == 6

    # 'w' springt zu 'gamma' (Index 11)
    _send_key(editor, Qt.Key.Key_W, "w")
    assert editor.textCursor().position() == 11

    # 'b' springt zurück zu 'beta' (Index 6)
    _send_key(editor, Qt.Key.Key_B, "b")
    assert editor.textCursor().position() == 6

    # 'e' springt zum Ende von 'beta' (Index 9)
    _send_key(editor, Qt.Key.Key_E, "e")
    assert editor.textCursor().position() == 9


def test_vim_normal_line_navigation_0_caret_dollar(qapp):
    """Testet 0, ^ und $ Navigation im Normal-Modus."""
    editor = CodeEditor()
    editor.setPlainText("    def my_func():")
    editor.set_vim_mode_enabled(True)

    # Cursor in die Mitte setzen
    cursor = editor.textCursor()
    cursor.setPosition(8)
    editor.setTextCursor(cursor)

    # '0' springt ganz an den Zeilenanfang (Spalte 0)
    _send_key(editor, Qt.Key.Key_0, "0")
    assert editor.textCursor().position() == 0

    # '^' springt zum ersten nicht-Whitespace Zeichen (Spalte 4)
    _send_key(editor, Qt.Key.Key_AsciiCircum, "^")
    assert editor.textCursor().position() == 4

    # '$' springt ans Zeilenende (auf das letzte Zeichen im Normal-Modus)
    _send_key(editor, Qt.Key.Key_Dollar, "$")
    assert editor.textCursor().position() == len("    def my_func():") - 1


def test_vim_normal_gg_and_g(qapp):
    """Testet Dokumentensprünge gg und G."""
    editor = CodeEditor()
    editor.setPlainText("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'G' springt zur letzten Zeile
    _send_key(editor, Qt.Key.Key_G, "G", Qt.KeyboardModifier.ShiftModifier)
    assert editor.textCursor().blockNumber() == 4

    # 'gg' springt zur ersten Zeile
    _type_chars(editor, "gg")
    assert editor.textCursor().blockNumber() == 0


def test_vim_count_multiplier(qapp):
    """Testet Multiplikatoren (z. B. 3w, 3j)."""
    editor = CodeEditor()
    editor.setPlainText("one two three four five six seven")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # '3w' springt um 3 Wörter nach vorne (zu 'four')
    _type_chars(editor, "3w")
    pos = editor.textCursor().position()
    assert editor.toPlainText()[pos:pos + 4] == "four"


def test_vim_mode_transitions_insert_normal(qapp):
    """Testet Umschalten zwischen NORMAL und INSERT mit i, Escape, Ctrl+[."""
    editor = CodeEditor()
    editor.setPlainText("world")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)
    assert editor.vim_engine.get_mode() == VimMode.NORMAL

    # 'i' wechselt in INSERT
    _send_key(editor, Qt.Key.Key_I, "i")
    assert editor.vim_engine.get_mode() == VimMode.INSERT

    # Escape wechselt zurück in NORMAL
    _send_key(editor, Qt.Key.Key_Escape)
    assert editor.vim_engine.get_mode() == VimMode.NORMAL

    # 'i' erneut drücken, dann mit Ctrl+[ verlassen
    _send_key(editor, Qt.Key.Key_I, "i")
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    _send_key(editor, Qt.Key.Key_BracketLeft, "[", Qt.KeyboardModifier.ControlModifier)
    assert editor.vim_engine.get_mode() == VimMode.NORMAL


def test_vim_insert_variants_a_I_A_o_O(qapp):
    """Testet die alternativen Einstiege in den INSERT Modus: a, I, A, o, O."""
    editor = CodeEditor()
    editor.setPlainText("  hello")
    editor.set_vim_mode_enabled(True)

    # 'a' fügt nach dem Zeichen ein
    cursor = editor.textCursor()
    cursor.setPosition(2)  # auf 'h'
    editor.setTextCursor(cursor)
    _send_key(editor, Qt.Key.Key_A, "a")
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    assert editor.textCursor().position() == 3
    _send_key(editor, Qt.Key.Key_Escape)

    # 'I' springt zum ersten Zeichen und geht in Insert
    _send_key(editor, Qt.Key.Key_I, "I", Qt.KeyboardModifier.ShiftModifier)
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    assert editor.textCursor().position() == 2
    _send_key(editor, Qt.Key.Key_Escape)

    # 'A' springt ans Zeilenende und geht in Insert
    _send_key(editor, Qt.Key.Key_A, "A", Qt.KeyboardModifier.ShiftModifier)
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    assert editor.textCursor().position() == len("  hello")
    _send_key(editor, Qt.Key.Key_Escape)

    # 'o' öffnet neue Zeile darunter
    _send_key(editor, Qt.Key.Key_O, "o")
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    assert editor.textCursor().blockNumber() == 1
    _send_key(editor, Qt.Key.Key_Escape)

    # 'O' öffnet neue Zeile darüber
    _send_key(editor, Qt.Key.Key_O, "O", Qt.KeyboardModifier.ShiftModifier)
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    assert editor.textCursor().blockNumber() == 1


def test_vim_delete_x_X(qapp):
    """Testet x (Delete unter Cursor) und X (Backspace vor Cursor)."""
    editor = CodeEditor()
    editor.setPlainText("abcde")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(2)  # auf 'c'
    editor.setTextCursor(cursor)

    # 'x' löscht 'c' -> "abde"
    _send_key(editor, Qt.Key.Key_X, "x")
    assert editor.toPlainText() == "abde"

    # 'X' löscht 'b' -> "ade"
    _send_key(editor, Qt.Key.Key_X, "X", Qt.KeyboardModifier.ShiftModifier)
    assert editor.toPlainText() == "ade"


def test_vim_delete_line_dd_and_multiplier(qapp):
    """Testet Zeilenlöschung mit dd und Multiplikator."""
    editor = CodeEditor()
    editor.setPlainText("Zeile 1\nZeile 2\nZeile 3\nZeile 4")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'dd' löscht Zeile 1
    _type_chars(editor, "dd")
    assert editor.toPlainText() == "Zeile 2\nZeile 3\nZeile 4"

    # '2dd' löscht Zeile 2 und Zeile 3
    _type_chars(editor, "2dd")
    assert editor.toPlainText() == "Zeile 4"


def test_vim_delete_word_dw_de(qapp):
    """Testet dw und de."""
    editor = CodeEditor()
    editor.setPlainText("foo bar baz")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'dw' löscht "foo "
    _type_chars(editor, "dw")
    assert editor.toPlainText() == "bar baz"

    # 'de' löscht "bar"
    _type_chars(editor, "de")
    assert editor.toPlainText() == " baz"


def test_vim_delete_line_bounds_d0_d_dollar(qapp):
    """Testet d0, d$ und D."""
    editor = CodeEditor()
    editor.setPlainText("left middle right")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(5)  # Anfang von 'middle'
    editor.setTextCursor(cursor)

    # 'D' löscht bis Zeilenende
    _send_key(editor, Qt.Key.Key_D, "D", Qt.KeyboardModifier.ShiftModifier)
    assert editor.toPlainText() == "left "

    # 'd0' löscht zum Zeilenanfang
    _type_chars(editor, "d0")
    assert editor.toPlainText() == ""


def test_vim_change_cw_cc_C_s(qapp):
    """Testet Change-Aktionen cw, cc, C, s."""
    editor = CodeEditor()
    editor.setPlainText("hello world")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'cw' ändert das Wort und wechselt in INSERT
    _type_chars(editor, "cw")
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    assert editor.toPlainText() == " world"
    _send_key(editor, Qt.Key.Key_Escape)

    # 'cc' ändert die ganze Zeile (behält Einrückung bei)
    _type_chars(editor, "cc")
    assert editor.vim_engine.get_mode() == VimMode.INSERT
    assert editor.toPlainText() == " "
    _send_key(editor, Qt.Key.Key_Escape)


def test_vim_yank_and_paste_line_and_word(qapp):
    """Testet yy, yw, p und P."""
    editor = CodeEditor()
    editor.setPlainText("Zeile A\nZeile B")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'yy' kopiert Zeile A
    _type_chars(editor, "yy")
    assert editor.vim_engine._register_text == "Zeile A\n"
    assert editor.vim_engine._register_is_line is True

    # 'p' fügt nach Zeile A ein
    _send_key(editor, Qt.Key.Key_P, "p")
    assert editor.toPlainText() == "Zeile A\nZeile A\nZeile B"

    # Wort kopieren mit yw
    cursor.setPosition(0)
    editor.setTextCursor(cursor)
    _type_chars(editor, "yw")
    assert editor.vim_engine._register_text.startswith("Zeile")
    assert editor.vim_engine._register_is_line is False


def test_vim_replace_char(qapp):
    """Testet r<char> zum Ersetzen eines einzelnen Zeichens."""
    editor = CodeEditor()
    editor.setPlainText("cxt")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(1)  # auf 'x'
    editor.setTextCursor(cursor)

    # 'ra' ersetzt 'x' durch 'a' -> "cat"
    _type_chars(editor, "ra")
    assert editor.toPlainText() == "cat"
    assert editor.vim_engine.get_mode() == VimMode.NORMAL


def test_vim_toggle_case(qapp):
    """Testet ~ zum Umschalten der Groß-/Kleinschreibung."""
    editor = CodeEditor()
    editor.setPlainText("abc")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # '~' macht 'a' zu 'A' und rückt Cursor vor
    _send_key(editor, Qt.Key.Key_AsciiTilde, "~")
    assert editor.toPlainText() == "Abc"


def test_vim_join_lines(qapp):
    """Testet J zum Verbinden zweier Zeilen."""
    editor = CodeEditor()
    editor.setPlainText("Zeile 1\nZeile 2")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    _send_key(editor, Qt.Key.Key_J, "J", Qt.KeyboardModifier.ShiftModifier)
    assert editor.toPlainText() == "Zeile 1 Zeile 2"


def test_vim_indent_unindent(qapp):
    """Testet >> und << zum Ein- und Ausrücken."""
    editor = CodeEditor()
    editor.setPlainText("code")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # '>>' rückt ein
    _type_chars(editor, ">>")
    assert editor.toPlainText().startswith("    ")

    # '<<' rückt aus
    _type_chars(editor, "<<")
    assert editor.toPlainText() == "code"


def test_vim_undo_redo(qapp):
    """Testet u und Ctrl+R."""
    editor = CodeEditor()
    editor.setPlainText("initial")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # Lösche Zeichen mit 'x'
    _send_key(editor, Qt.Key.Key_X, "x")
    assert editor.toPlainText() == "nitial"

    # 'u' macht Rückgängig
    _send_key(editor, Qt.Key.Key_U, "u")
    assert editor.toPlainText() == "initial"

    # Ctrl+R wiederholt
    _send_key(editor, Qt.Key.Key_R, "r", Qt.KeyboardModifier.ControlModifier)
    assert editor.toPlainText() == "nitial"


def test_vim_visual_mode_char_and_line(qapp):
    """Testet Eintritt und Auswahl im Visual und Visual-Line Modus."""
    editor = CodeEditor()
    editor.setPlainText("Hello World\nLine Two")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # 'v' wechselt in VISUAL
    _send_key(editor, Qt.Key.Key_V, "v")
    assert editor.vim_engine.get_mode() == VimMode.VISUAL

    # 'l' erweitert die Auswahl
    _send_key(editor, Qt.Key.Key_L, "l")
    assert editor.textCursor().hasSelection()

    # Escape verlässt VISUAL
    _send_key(editor, Qt.Key.Key_Escape)
    assert editor.vim_engine.get_mode() == VimMode.NORMAL
    assert not editor.textCursor().hasSelection()

    # 'V' wechselt in VISUAL_LINE
    _send_key(editor, Qt.Key.Key_V, "V", Qt.KeyboardModifier.ShiftModifier)
    assert editor.vim_engine.get_mode() == VimMode.VISUAL_LINE
    assert editor.textCursor().hasSelection()

    # Escape verlässt VISUAL_LINE
    _send_key(editor, Qt.Key.Key_Escape)
    assert editor.vim_engine.get_mode() == VimMode.NORMAL


def test_vim_visual_operations_delete_yank_case_indent(qapp):
    """Testet Aktionen in VISUAL: d, y, c, ~, u, U, >, <."""
    editor = CodeEditor()
    editor.setPlainText("hello world")
    editor.set_vim_mode_enabled(True)

    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)

    # Markiere die ersten 5 Zeichen ("hello")
    _send_key(editor, Qt.Key.Key_V, "v")
    for _ in range(4):
        _send_key(editor, Qt.Key.Key_L, "l")

    # 'U' macht Grossbuchstaben
    _send_key(editor, Qt.Key.Key_U, "U", Qt.KeyboardModifier.ShiftModifier)
    assert editor.toPlainText() == "HELLO world"
    assert editor.vim_engine.get_mode() == VimMode.NORMAL

    # Erneut markieren und löschen mit 'd'
    cursor.setPosition(0)
    editor.setTextCursor(cursor)
    _send_key(editor, Qt.Key.Key_V, "v")
    for _ in range(4):
        _send_key(editor, Qt.Key.Key_L, "l")
    _send_key(editor, Qt.Key.Key_D, "d")
    assert editor.toPlainText() == " world"


def test_vim_editor_integration(qapp):
    """Testet die CodeEditor-Methoden set_vim_mode_enabled und Block-Cursor-Steuerung."""
    editor = CodeEditor()
    assert not editor.is_vim_mode_enabled()

    editor.set_vim_mode_enabled(True)
    assert editor.is_vim_mode_enabled()
    # Normal Mode hat Block-Cursor (Breite > 2)
    assert editor.cursorWidth() > 2

    # In Insert-Mode wechseln
    _send_key(editor, Qt.Key.Key_I, "i")
    # Insert Mode hat Standard-Strichcursor (Breite 2)
    assert editor.cursorWidth() == 2

    # Zurück zu Normal-Mode
    _send_key(editor, Qt.Key.Key_Escape)
    assert editor.cursorWidth() > 2


def test_vim_main_window_toggle_and_statusbar(qapp):
    """Testet die MainWindow-Integration für Vim-Modus."""
    win = MainWindow()
    assert hasattr(win, "vim_label")
    assert hasattr(win, "act_vim_mode")

    # Standardmäßig aus
    win._settings["vim_mode"] = False
    win._apply_settings()
    assert not win.act_vim_mode.isChecked()
    assert win.vim_label.isHidden()

    # Umschalten via toggle_vim_mode()
    win.toggle_vim_mode(True)
    assert win.act_vim_mode.isChecked()
    assert win._settings["vim_mode"] is True
    active_tab = win.get_active_tab()
    assert active_tab.editor.is_vim_mode_enabled()
    assert not win.vim_label.isHidden()
    assert "NORMAL" in win.vim_label.text()

    # Wieder deaktivieren
    win.toggle_vim_mode(False)
    assert not win.act_vim_mode.isChecked()
    assert not active_tab.editor.is_vim_mode_enabled()
    assert win.vim_label.isHidden()

    win.close()


def test_vim_settings_dialog(qapp):
    """Testet die Vim-Modus Checkbox im Einstellungen-Dialog."""
    dialog = SettingsDialog()
    assert hasattr(dialog, "vim_mode_cb")

    dialog.vim_mode_cb.setChecked(True)
    out = dialog.get_settings()
    assert out.get("vim_mode") is True
    dialog.close()


def test_vim_shortcuts_dialog(qapp):
    """Testet die Vollständigkeit der Vim-Tastenkürzel in SHORTCUTS_DATA."""
    categories = [cat for cat, _, _, _ in SHORTCUTS_DATA]
    assert "Vim-Modus" in categories

    vim_shortcuts = [item for item in SHORTCUTS_DATA if item[0] == "Vim-Modus"]
    assert len(vim_shortcuts) >= 8

    # Prüfe, ob Ctrl+Alt+V unter Bearbeiten vorhanden ist
    edit_shortcuts = [item for item in SHORTCUTS_DATA if item[0] == "Bearbeiten" and "Vim" in item[1]]
    assert len(edit_shortcuts) == 1
    assert edit_shortcuts[0][2] == "Ctrl+Alt+V"
