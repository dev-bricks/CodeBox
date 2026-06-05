"""Tests für auto-close Verhalten des CodeEditor."""
import unittest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import QEvent

from core.editor import CodeEditor


def _ensure_app():
    return QApplication.instance() or QApplication([])


def _key_event(key: str) -> QKeyEvent:
    """Erzeugt ein QKeyEvent für ein einzelnes Zeichen."""
    return QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, key)


class AutoCloseQuoteTests(unittest.TestCase):
    def setUp(self):
        _ensure_app()
        self.editor = CodeEditor()

    def tearDown(self):
        self.editor.close()

    def test_double_quote_auto_closes(self):
        """Tippen von \" soll \"\" einfügen und Cursor zwischen die Anführungszeichen setzen."""
        self.editor.setPlainText("")
        self.editor.keyPressEvent(_key_event('"'))
        text = self.editor.toPlainText()
        self.assertEqual(text, '""', f"Erwartet '\"\"', bekommen: {text!r}")
        cursor = self.editor.textCursor()
        self.assertEqual(cursor.position(), 1, "Cursor muss zwischen den Anführungszeichen stehen")

    def test_double_quote_skip_closing_when_next_char_is_quote(self):
        """Regression (B-003): Tippen von \" wenn das nächste Zeichen bereits \" ist,
        darf NICHT weitere Anführungszeichen einfügen, sondern muss den Cursor überspringen."""
        # Ausgangszustand: "" mit Cursor zwischen den Anführungszeichen (Position 1)
        self.editor.setPlainText('""')
        cursor = self.editor.textCursor()
        cursor.setPosition(1)
        self.editor.setTextCursor(cursor)

        self.editor.keyPressEvent(_key_event('"'))

        text = self.editor.toPlainText()
        self.assertEqual(text, '""',
                         f"Kein neues Anführungszeichen erwartet, bekommen: {text!r}")
        self.assertEqual(self.editor.textCursor().position(), 2,
                         "Cursor muss hinter das schließende Anführungszeichen gesprungen sein")

    def test_single_quote_skip_closing_when_next_char_is_single_quote(self):
        """Dasselbe Verhalten für einfache Anführungszeichen."""
        self.editor.setPlainText("''")
        cursor = self.editor.textCursor()
        cursor.setPosition(1)
        self.editor.setTextCursor(cursor)

        self.editor.keyPressEvent(_key_event("'"))

        text = self.editor.toPlainText()
        self.assertEqual(text, "''",
                         f"Kein neues einfaches Anführungszeichen erwartet, bekommen: {text!r}")
        self.assertEqual(self.editor.textCursor().position(), 2,
                         "Cursor muss hinter das schließende Anführungszeichen gesprungen sein")

    def test_open_bracket_auto_closes_normally(self):
        """Öffnende Klammern müssen weiterhin normal geschlossen werden."""
        self.editor.setPlainText("")
        self.editor.keyPressEvent(_key_event("("))
        text = self.editor.toPlainText()
        self.assertEqual(text, "()", f"Erwartet '()', bekommen: {text!r}")
        self.assertEqual(self.editor.textCursor().position(), 1)


if __name__ == "__main__":
    unittest.main()
