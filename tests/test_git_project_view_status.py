"""Tests für status_for_path() in features/project_view.py.

Prüft die Qt-freie Hilfsfunktion, die absoluten Dateipfaden einen
GitFileStatus zuordnet — inkl. Windows-Pfad-Normalisierung.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.project_view import status_for_path
from features.git_integration import GitFileStatus


def _file_status(path: str, *, is_modified=False, is_untracked=False,
                 is_staged=False, is_deleted=False) -> GitFileStatus:
    """Baut ein minimales GitFileStatus für Tests."""
    return GitFileStatus(
        path=path,
        index_status="M" if is_staged else ("D" if is_deleted else "?"),
        work_status="M" if is_modified else ("D" if is_deleted else "?"),
        is_staged=is_staged,
        is_modified=is_modified,
        is_untracked=is_untracked,
        is_deleted=is_deleted,
    )


class TestStatusForPath(unittest.TestCase):

    def test_simple_match_unix(self):
        """Unix-Pfad: einfaches Match gegen Status-Key."""
        sd = {"src/main.py": _file_status("src/main.py", is_modified=True)}
        result = status_for_path("/repo/src/main.py", "/repo", sd)
        self.assertIsNotNone(result)
        self.assertTrue(result.is_modified)

    def test_windows_backslash_normalization(self):
        """Windows-Backslashes werden transparent zu Forward-Slashes normalisiert."""
        sd = {"src/main.py": _file_status("src/main.py", is_modified=True)}
        result = status_for_path(
            r"C:\project\src\main.py", r"C:\project", sd
        )
        self.assertIsNotNone(result, "Windows-Pfad muss nach Normalisierung matchen")
        self.assertTrue(result.is_modified)

    def test_outside_repo_returns_none(self):
        """Pfad außerhalb des Repo-Roots gibt None zurück (keine ValueError-Ausnahme)."""
        sd = {"main.py": _file_status("main.py")}
        result = status_for_path("/other/main.py", "/repo", sd)
        self.assertIsNone(result)

    def test_no_status_entry_returns_none(self):
        """Saubere Datei ohne Status-Eintrag im Dict gibt None zurück."""
        result = status_for_path("/repo/clean.py", "/repo", {})
        self.assertIsNone(result)

    def test_nested_path_untracked(self):
        """Tief verschachtelte Pfade werden korrekt aufgelöst."""
        sd = {"a/b/c/deep.py": _file_status("a/b/c/deep.py", is_untracked=True)}
        result = status_for_path("/repo/a/b/c/deep.py", "/repo", sd)
        self.assertIsNotNone(result)
        self.assertTrue(result.is_untracked)

    def test_staged_file_icon(self):
        """Status-Icon einer rein gestageten Datei ist 'S'."""
        sd = {"staged.py": _file_status("staged.py", is_staged=True)}
        result = status_for_path("/repo/staged.py", "/repo", sd)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_icon, "S")

    def test_deleted_file_icon(self):
        """Status-Icon einer gelöschten Datei ist 'D'."""
        sd = {"gone.py": _file_status("gone.py", is_deleted=True)}
        result = status_for_path("/repo/gone.py", "/repo", sd)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_icon, "D")

    def test_root_itself_returns_none(self):
        """Der Repo-Root selbst taucht nicht im Status-Dict auf → None."""
        result = status_for_path("/repo", "/repo", {})
        self.assertIsNone(result)

    def test_empty_status_dict_returns_none(self):
        """Leeres Status-Dict: immer None."""
        result = status_for_path("/repo/any.py", "/repo", {})
        self.assertIsNone(result)

    def test_windows_nested_backslash(self):
        """Windows-Pfad mit mehreren Ebenen und Backslashes."""
        sd = {"sub/dir/file.py": _file_status("sub/dir/file.py", is_modified=True)}
        result = status_for_path(
            r"C:\myproject\sub\dir\file.py", r"C:\myproject", sd
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.is_modified)


if __name__ == "__main__":
    unittest.main()
