"""Git integration for CodeBox Project View.

Provides git status information for files in the project tree:
- Modified, staged, untracked, deleted indicators
- Current branch name
- Basic git operations (status, diff)

Uses subprocess to call git CLI (no additional dependencies).
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger("CodeBox.Git")


@dataclass
class GitFileStatus:
    """Status of a single file in the git working tree."""
    path: str
    index_status: str   # X: status in index (staged)
    work_status: str    # Y: status in worktree
    is_staged: bool = False
    is_modified: bool = False
    is_untracked: bool = False
    is_deleted: bool = False
    is_renamed: bool = False

    @property
    def status_icon(self) -> str:
        """Returns a status indicator character for display."""
        if self.is_untracked:
            return "U"
        if self.is_staged and self.is_modified:
            return "SM"
        if self.is_staged:
            return "S"
        if self.is_deleted:
            return "D"
        if self.is_modified:
            return "M"
        if self.is_renamed:
            return "R"
        return ""

    @property
    def color_hint(self) -> str:
        """Returns a color name for the status."""
        if self.is_untracked:
            return "#73c991"  # green
        if self.is_staged:
            return "#c4a000"  # yellow/gold
        if self.is_modified:
            return "#e2c08d"  # orange
        if self.is_deleted:
            return "#c74e39"  # red
        return ""


def parse_porcelain_path(raw_path: str) -> str:
    """Parses a file path from git status --porcelain output, handling renames and C-style quotes.

    Git quotes paths with spaces or special characters in double quotes and C-escapes them.
    Renamed files have the format: "old_path" -> "new_path" or old_path -> new_path.
    """
    raw = raw_path.strip()
    if " -> " in raw:
        raw = raw.split(" -> ")[-1].strip()

    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
        raw = (
            raw.replace(r'\"', '"')
            .replace(r'\\', '\\')
            .replace(r'\t', '\t')
            .replace(r'\n', '\n')
        )
    return raw


class GitRepo:
    """Interface to a git repository via CLI."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    def _run_git(self, *args) -> Optional[str]:
        """Executes a git command and returns stdout, or None on failure."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.rstrip("\r\n")
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug("Git command failed: git %s (%s)", " ".join(args), e)
            return None

    def is_git_repo(self) -> bool:
        """Checks if the path is inside a git repository."""
        return self._run_git("rev-parse", "--is-inside-work-tree") == "true"

    def get_branch(self) -> str:
        """Returns the current branch name."""
        result = self._run_git("branch", "--show-current")
        return result or "(detached)"

    def get_status(self) -> Dict[str, GitFileStatus]:
        """Returns the git status for all changed files.

        Returns:
            Dict mapping relative file path to GitFileStatus.
        """
        output = self._run_git("status", "--porcelain=v1", "-uall")
        if output is None:
            return {}

        statuses = {}
        for line in output.splitlines():
            if len(line) < 4:
                continue
            x = line[0]  # index status
            y = line[1]  # worktree status
            filepath = parse_porcelain_path(line[3:])

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
            statuses[filepath] = status

        return statuses

    def get_diff(self, filepath: str = None, staged: bool = False) -> Optional[str]:
        """Returns the diff for a file or the entire working tree.

        Args:
            filepath: Specific file path, or None for all changes.
            staged: If True, show staged changes (--cached).

        Returns:
            Diff text, or None on failure.
        """
        args = ["diff"]
        if staged:
            args.append("--cached")
        if filepath:
            args.extend(["--", filepath])
        diff = self._run_git(*args)
        if (not diff) and filepath and not staged:
            full_path = self.repo_path / filepath
            if full_path.is_file():
                status = self.get_status().get(filepath.replace("\\", "/"))
                if status and status.is_untracked:
                    try:
                        import difflib
                        content = full_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                        diff_lines = list(difflib.unified_diff(
                            [],
                            content,
                            fromfile=f"a/{filepath}",
                            tofile=f"b/{filepath}",
                        ))
                        if diff_lines:
                            return "".join(diff_lines).strip()
                    except Exception:
                        pass
        return diff

    def get_file_content_at_head(self, filepath: str) -> Optional[str]:
        """Returns the content of a file from HEAD, or None."""
        clean_path = filepath.replace("\\", "/")
        return self._run_git("show", f"HEAD:{clean_path}")

    def get_file_content_in_index(self, filepath: str) -> Optional[str]:
        """Returns the content of a file from the git index (:0:filepath), or None."""
        clean_path = filepath.replace("\\", "/")
        return self._run_git("show", f":0:{clean_path}")

    def get_log(self, limit: int = 20, oneline: bool = True) -> List[str]:
        """Returns recent commit messages.

        Args:
            limit: Number of commits to show.
            oneline: If True, show one line per commit.

        Returns:
            List of commit strings.
        """
        fmt = "--oneline" if oneline else "--format=%h %s (%an, %ar)"
        result = self._run_git("log", fmt, f"-{limit}")
        if result:
            return result.splitlines()
        return []

    def _run_git_result(self, *args) -> Tuple[int, str, str]:
        """Executes a git command and returns (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug("Git command failed: git %s (%s)", " ".join(args), e)
            return -1, "", str(e)

    def stage_file(self, filepath: str) -> bool:
        """Stages a specific file (git add -- <filepath>)."""
        clean_path = filepath.replace("\\", "/")
        code, _, _ = self._run_git_result("add", "--", clean_path)
        return code == 0

    def unstage_file(self, filepath: str) -> bool:
        """Unstages a specific file (git restore --staged -- <filepath>)."""
        clean_path = filepath.replace("\\", "/")
        code, _, _ = self._run_git_result("restore", "--staged", "--", clean_path)
        if code != 0:
            code, _, _ = self._run_git_result("reset", "HEAD", "--", clean_path)
        return code == 0

    def stage_all(self) -> bool:
        """Stages all changes in the repository (git add -A)."""
        code, _, _ = self._run_git_result("add", "-A")
        return code == 0

    def unstage_all(self) -> bool:
        """Unstages all staged changes in the repository (git restore --staged .)."""
        code, _, _ = self._run_git_result("restore", "--staged", ".")
        if code != 0:
            code, _, _ = self._run_git_result("reset", "HEAD")
        return code == 0

    def discard_file_changes(self, filepath: str) -> bool:
        """Discards worktree changes for a file (restore or clean)."""
        clean_path = filepath.replace("\\", "/")
        status_dict = self.get_status()
        status = status_dict.get(clean_path)
        if status and status.is_untracked:
            target = self.repo_path / filepath
            try:
                if target.is_file():
                    target.unlink()
                    return True
            except OSError:
                code, _, _ = self._run_git_result("clean", "-f", "--", clean_path)
                return code == 0
        code, _, _ = self._run_git_result("restore", "--", clean_path)
        if code != 0:
            code, _, _ = self._run_git_result("checkout", "--", clean_path)
        return code == 0

    def commit(self, message: str) -> Tuple[bool, str]:
        """Creates a git commit with the given message.

        Returns:
            (True, output_text) on success, (False, error_message) on failure.
        """
        msg = message.strip()
        if not msg:
            return False, "Commit-Nachricht darf nicht leer sein."
        code, stdout, stderr = self._run_git_result("commit", "-m", msg)
        if code == 0:
            return True, stdout or "Commit erfolgreich erstellt."
        return False, stderr or stdout or "Fehler beim Erstellen des Commits."
