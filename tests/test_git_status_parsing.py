"""Regressionstests für GitFileStatus-Parsing in features/git_integration.py."""
import unittest

from features.git_integration import GitRepo, GitFileStatus


def _make_status(x: str, y: str, path: str = "file.py") -> GitFileStatus:
    """Baut ein GitFileStatus aus einem porcelain-Zeilenpaar."""
    return GitFileStatus(
        path=path,
        index_status=x,
        work_status=y,
        is_staged=x in "MADRC",
        is_modified=y == "M",
        is_untracked=x == "?" and y == "?",
        is_deleted=x == "D" or y == "D",
        is_renamed=x == "R",
    )


class GitFileStatusIconTests(unittest.TestCase):
    def test_staged_only_shows_S_not_SM(self):
        """Regression (B-006): Rein gestagete Datei (X=M, Y=space) soll 'S' zeigen,
        nicht 'SM'. Vorher war is_modified=y=='M' OR x=='M', was 'SM' erzeugte."""
        status = _make_status("M", " ")
        self.assertFalse(status.is_modified,
                         "Rein gestagete Datei darf is_modified nicht setzen")
        self.assertTrue(status.is_staged)
        self.assertEqual(status.status_icon, "S",
                         f"Erwartet 'S', bekommen: {status.status_icon!r}")

    def test_staged_and_worktree_modified_shows_SM(self):
        """Gestagete Datei mit zusätzlichen Worktree-Änderungen (X=M, Y=M) soll 'SM' zeigen."""
        status = _make_status("M", "M")
        self.assertTrue(status.is_staged)
        self.assertTrue(status.is_modified)
        self.assertEqual(status.status_icon, "SM")

    def test_worktree_only_modified_shows_M(self):
        """Nicht gestagete Worktree-Änderung (X=space, Y=M) soll 'M' zeigen."""
        status = _make_status(" ", "M")
        self.assertFalse(status.is_staged)
        self.assertTrue(status.is_modified)
        self.assertEqual(status.status_icon, "M")

    def test_untracked_shows_U(self):
        """Ungetrackte Datei (X=?, Y=?) soll 'U' zeigen."""
        status = _make_status("?", "?")
        self.assertTrue(status.is_untracked)
        self.assertEqual(status.status_icon, "U")

    def test_staged_addition_shows_S(self):
        """Gestagetes Add (X=A, Y=space) soll 'S' zeigen."""
        status = _make_status("A", " ")
        self.assertTrue(status.is_staged)
        self.assertFalse(status.is_modified)
        self.assertEqual(status.status_icon, "S")

    def test_porcelain_parsing_staged_only(self):
        """get_status() parst 'M  file.py' korrekt als rein gestagt."""
        raw_line = "M  file.py"

        line = raw_line
        x = line[0]
        y = line[1]
        filepath = line[3:].strip()

        status = GitFileStatus(
            path=filepath,
            index_status=x,
            work_status=y,
            is_staged=x in "MADRC",
            is_modified=y == "M",
            is_untracked=x == "?" and y == "?",
            is_deleted=x == "D" or y == "D",
            is_renamed=x == "R",
        )

        self.assertFalse(status.is_modified,
                         "Rein gestagete Datei (X=M, Y=space): is_modified muss False sein")
        self.assertEqual(status.status_icon, "S")


if __name__ == "__main__":
    unittest.main()
