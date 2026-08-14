"""Optional, local linters used by CodeBox.

The editor must remain usable without a linter installed.  This module keeps
command discovery and output parsing independent from the Qt UI and runs the
actual command in a short-lived worker thread when used through
``LinterManager``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QThread, QObject, Signal


Diagnostic = Dict[str, object]
Parser = Callable[[str], List[Diagnostic]]


def _diagnostic(
    *,
    line: int,
    col: int = 1,
    message: str = "",
    severity: str = "error",
    code: str = "",
    source: str = "",
    path: Optional[str] = None,
) -> Diagnostic:
    """Create the normalized diagnostic shape shared by all linters."""
    result: Diagnostic = {
        "line": max(1, int(line or 1)),
        "col": max(1, int(col or 1)),
        "message": str(message or "").strip(),
        "severity": severity if severity in {"error", "warning", "info", "hint"} else "error",
        "code": str(code or ""),
        "source": str(source or ""),
    }
    if path:
        result["path"] = str(path)
    return result


def parse_ruff_output(output: str) -> List[Diagnostic]:
    """Parse Ruff's ``--output-format json`` result."""
    try:
        payload = json.loads(output or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []

    diagnostics: List[Diagnostic] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        location = item.get("location") or {}
        code = str(item.get("code") or "")
        diagnostics.append(_diagnostic(
            line=location.get("row", 1),
            col=location.get("column", 1),
            message=item.get("message", ""),
            severity="warning" if code.startswith(("W", "I")) else "error",
            code=code,
            source="ruff",
            path=item.get("filename"),
        ))
    return diagnostics


def parse_eslint_output(output: str) -> List[Diagnostic]:
    """Parse ESLint's JSON formatter result."""
    try:
        payload = json.loads(output or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []

    diagnostics: List[Diagnostic] = []
    for file_result in payload:
        if not isinstance(file_result, dict):
            continue
        path = file_result.get("filePath")
        for item in file_result.get("messages", []):
            if not isinstance(item, dict):
                continue
            severity_value = item.get("severity", 2)
            severity = "warning" if severity_value == 1 else "error"
            diagnostics.append(_diagnostic(
                line=item.get("line", 1),
                col=item.get("column", 1),
                message=item.get("message", ""),
                severity=severity,
                code=item.get("ruleId") or "",
                source="eslint",
                path=path,
            ))
    return diagnostics


_FLAKE8_LINE = re.compile(
    r"^(?P<path>.*?):(?P<line>\d+):(?P<col>\d+):\s*"
    r"(?P<code>[A-Z]\d+)?\s*(?P<message>.*)$"
)


def parse_flake8_output(output: str) -> List[Diagnostic]:
    """Parse the stable ``path:line:column: CODE message`` flake8 format."""
    diagnostics: List[Diagnostic] = []
    for raw_line in (output or "").splitlines():
        match = _FLAKE8_LINE.match(raw_line.strip())
        if not match:
            continue
        groups = match.groupdict()
        code = groups.get("code") or ""
        diagnostics.append(_diagnostic(
            line=groups.get("line", 1),
            col=groups.get("col", 1),
            message=groups.get("message", ""),
            severity="warning" if code.startswith("W") else "error",
            code=code,
            source="flake8",
            path=groups.get("path"),
        ))
    return diagnostics


def resolve_linter(language: str) -> Optional[Tuple[List[str], Parser, str]]:
    """Return ``(command_prefix, parser, source)`` for an installed linter."""
    normalized = (language or "").strip().lower()
    if normalized == "python":
        if shutil.which("ruff"):
            return ["ruff", "check", "--output-format", "json", "--no-cache"], parse_ruff_output, "ruff"
        if shutil.which("flake8"):
            return ["flake8"], parse_flake8_output, "flake8"
    elif normalized in {"javascript", "typescript"} and shutil.which("eslint"):
        return ["eslint", "--format", "json"], parse_eslint_output, "eslint"
    return None


def run_linter(language: str, file_path: Path, timeout: float = 8.0) -> List[Diagnostic]:
    """Run the first available linter for ``file_path``.

    Missing tools, invalid configuration, timeouts and process failures are
    intentionally represented as no diagnostics: an optional linter must not
    make saving a file fail.
    """
    resolved = resolve_linter(language)
    if not resolved or not file_path:
        return []
    command_prefix, parser, source = resolved
    try:
        completed = subprocess.run(
            [*command_prefix, str(file_path)],
            cwd=str(file_path.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    output = completed.stdout
    if not output and source == "flake8":
        output = completed.stderr
    diagnostics = parser(output)
    for item in diagnostics:
        item.setdefault("source", source)
        item.setdefault("path", str(file_path))
    return diagnostics


class _LinterWorker(QThread):
    resultReady = Signal(object, object, int, list)

    def __init__(self, tab, language: str, file_path: Path, token: int, parent=None):
        super().__init__(parent)
        self.tab = tab
        self.language = language
        self.file_path = Path(file_path)
        self.token = token

    def run(self):  # noqa: D401 - Qt thread entry point
        diagnostics = run_linter(self.language, self.file_path)
        self.resultReady.emit(self.tab, self.file_path, self.token, diagnostics)


class LinterManager(QObject):
    """Run optional linters off the UI thread and publish normalized results."""

    lintFinished = Signal(object, object, int, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: Dict[object, _LinterWorker] = {}
        self._tokens: Dict[object, int] = {}

    def lint(self, tab, language: str, file_path: Path) -> int:
        token = self._tokens.get(tab, 0) + 1
        self._tokens[tab] = token
        previous = self._workers.get(tab)
        if previous and previous.isRunning():
            previous.requestInterruption()

        worker = _LinterWorker(tab, language, file_path, token, self)
        self._workers[tab] = worker
        worker.resultReady.connect(self.lintFinished.emit)
        worker.finished.connect(lambda: self._cleanup(tab, worker))
        worker.start()
        return token

    def _cleanup(self, tab, worker):
        if self._workers.get(tab) is worker:
            self._workers.pop(tab, None)
        worker.deleteLater()

    def stop_all(self):
        """Stop/wait for workers during application shutdown."""
        workers = list(self._workers.values())
        for worker in workers:
            worker.requestInterruption()
        for worker in workers:
            worker.wait(9000)
        self._workers.clear()

