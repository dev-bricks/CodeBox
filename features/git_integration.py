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
from typing import Optional, Dict, List
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
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
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
            filepath = line[3:].strip()
            # Handle renamed files (old -> new)
            if " -> " in filepath:
                filepath = filepath.split(" -> ")[-1]

            status = GitFileStatus(
                path=filepath,
                index_status=x,
                work_status=y,
                is_staged=x in "MADRC",
                is_modified=y == "M" or x == "M",
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
        return self._run_git(*args)

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
