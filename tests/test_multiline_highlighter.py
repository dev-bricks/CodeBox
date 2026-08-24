"""Unit tests for UniversalHighlighter multi-line docstring and block comment state machine."""

import pytest
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication

from core.highlighter import UniversalHighlighter
from languages.cpp_lang import CppProvider
from languages.javascript_lang import JavaScriptProvider
from languages.python_lang import PythonProvider


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_python_multiline_triple_double_quotes(qapp):
    """Verifies that triple-double-quoted multi-line docstrings maintain state across blocks."""
    doc = QTextDocument()
    code = '''def greet():
    """First line of docstring
    Second line of docstring
    """
    return True
'''
    doc.setPlainText(code)
    provider = PythonProvider()
    hl = UniversalHighlighter(doc, provider)
    hl.rehighlight()

    # Block 0: def greet(): -> 0
    # Block 1: """First line... -> 1 (open state)
    # Block 2: Second line... -> 1 (continued state)
    # Block 3: """ -> 0 (closed state)
    # Block 4: return True -> 0
    assert doc.findBlockByNumber(0).userState() == 0
    assert doc.findBlockByNumber(1).userState() == 1
    assert doc.findBlockByNumber(2).userState() == 1
    assert doc.findBlockByNumber(3).userState() == 0
    assert doc.findBlockByNumber(4).userState() == 0


def test_python_multiline_triple_single_quotes(qapp):
    """Verifies that triple-single-quoted multi-line docstrings maintain state 2 across blocks."""
    doc = QTextDocument()
    code = """def compute():
    '''Single quote docstring start
    Single quote docstring end'''
    x = 42
"""
    doc.setPlainText(code)
    provider = PythonProvider()
    hl = UniversalHighlighter(doc, provider)
    hl.rehighlight()

    assert doc.findBlockByNumber(0).userState() == 0
    assert doc.findBlockByNumber(1).userState() == 2
    assert doc.findBlockByNumber(2).userState() == 0
    assert doc.findBlockByNumber(3).userState() == 0


def test_single_line_docstring_stays_state_zero(qapp):
    """A docstring opened and closed on the same line must not leak into subsequent blocks."""
    doc = QTextDocument()
    code = '"""Single line docstring"""\nx = 10\n"""Another single line"""\ny = 20\n'
    doc.setPlainText(code)
    provider = PythonProvider()
    hl = UniversalHighlighter(doc, provider)
    hl.rehighlight()

    assert doc.findBlockByNumber(0).userState() == 0
    assert doc.findBlockByNumber(1).userState() == 0
    assert doc.findBlockByNumber(2).userState() == 0
    assert doc.findBlockByNumber(3).userState() == 0


def test_cpp_multiline_block_comments(qapp):
    """Verifies C++ style /* ... */ multi-line block comments."""
    doc = QTextDocument()
    code = """int main() {
    /* Multi-line
       C++ block
       comment */
    return 0;
}"""
    doc.setPlainText(code)
    provider = CppProvider()
    hl = UniversalHighlighter(doc, provider)
    hl.rehighlight()

    assert doc.findBlockByNumber(0).userState() == 0
    assert doc.findBlockByNumber(1).userState() == 1
    assert doc.findBlockByNumber(2).userState() == 1
    assert doc.findBlockByNumber(3).userState() == 0
    assert doc.findBlockByNumber(4).userState() == 0


def test_javascript_multiline_block_comments(qapp):
    """Verifies JavaScript /* ... */ multi-line comments."""
    doc = QTextDocument()
    code = """function add(a, b) {
    /* Add two numbers
       and return the result */
    return a + b;
}"""
    doc.setPlainText(code)
    provider = JavaScriptProvider()
    hl = UniversalHighlighter(doc, provider)
    hl.rehighlight()

    assert doc.findBlockByNumber(0).userState() == 0
    assert doc.findBlockByNumber(1).userState() == 1
    assert doc.findBlockByNumber(2).userState() == 0
    assert doc.findBlockByNumber(3).userState() == 0
