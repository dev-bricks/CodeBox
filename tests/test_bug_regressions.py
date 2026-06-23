# -*- coding: utf-8 -*-
"""Regressionstests Bugfix-Library-Transfer Batch #24 — DEV_CodeBox.

D2: Veraltete Qt-Enums in PySide6 6.4+ dürfen nicht mehr als bare Werte vorkommen.
"""

import py_compile
import unittest
from pathlib import Path

PROJ = Path(__file__).parent.parent


class TestD2DeprecatedQtEnums(unittest.TestCase):
    """D2 — Kein bare Qt-Enum in den Quelldateien."""

    def test_editor_no_bare_align(self):
        src = (PROJ / "core" / "editor.py").read_text(encoding="utf-8")
        self.assertNotIn("Qt.AlignRight", src,
                         "Qt.AlignRight (bare) — muss Qt.AlignmentFlag.AlignRight sein")

    def test_main_window_no_bare_orientation(self):
        src = (PROJ / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertNotIn("Qt.Horizontal", src,
                         "Qt.Horizontal (bare) — muss Qt.Orientation.Horizontal sein")
        self.assertNotIn("Qt.Vertical", src,
                         "Qt.Vertical (bare) — muss Qt.Orientation.Vertical sein")

    def test_syntax_valid(self):
        for rel in ("core/editor.py", "ui/main_window.py"):
            py_compile.compile(str(PROJ / rel), doraise=True)


if __name__ == "__main__":
    unittest.main()
