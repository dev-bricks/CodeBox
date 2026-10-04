#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debugger-Modul für CodeBox — Datenstrukturen und Parser für Stack-Frames und Watch-Expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class StackFrame:
    """Repräsentiert einen einzelnen Frame im Aufruf-Stapel (Call-Stack)."""

    file_path: str
    line_number: int
    function_name: str
    code_line: str = ""
    is_current: bool = False
    frame_index: int = 0

    @property
    def file_name(self) -> str:
        """Liefert den reinen Dateinamen des Stack-Frames."""
        if not self.file_path:
            return ""
        return Path(self.file_path).name

    def display_frame(self) -> str:
        """Formatierte Anzeige für die Baumansicht."""
        prefix = "▶ " if self.is_current else "  "
        func = self.function_name if self.function_name else "<unknown>"
        return f"{prefix}[{self.frame_index}] {func}"

    def location(self) -> str:
        """Kurze Pfadangabe mit Dateiname und Zeilennummer."""
        return f"{self.file_name}:{self.line_number}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialisiert den Frame zu einem Dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "code_line": self.code_line,
            "is_current": self.is_current,
            "frame_index": self.frame_index,
        }


@dataclass
class WatchExpression:
    """Repräsentiert einen benutzerdefinierten Überwachungsausdruck."""

    expression: str
    value: str = "<nicht ausgewertet>"
    type_name: str = ""
    status: str = "pending"  # "ok", "error", "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialisiert die Watch-Expression zu einem Dictionary."""
        return {
            "expression": self.expression,
            "value": self.value,
            "type_name": self.type_name,
            "status": self.status,
            "metadata": dict(self.metadata),
        }


_PDB_FRAME_REGEX = re.compile(
    r"^\s*(?P<current>>)?\s*(?P<path>[a-zA-Z]:[\\/][^():\r\n]+|/[^():\r\n]+|[a-zA-Z0-9_.\-]+(?:\.py|\.pyw)?)\((?P<line>\d+)\)\s*(?P<func>[^\r\n]*)"
)
_PDB_CODE_REGEX = re.compile(r"^\s*->\s*(?P<code>.*)$")


def parse_pdb_stack(text: str) -> List[StackFrame]:
    """Parst die Textausgabe eines PDB 'where'- oder Traceback-Befehls in eine Liste von StackFrames.

    Unterstützt sowohl Windows- als auch POSIX-Pfade, aktuelle Frame-Markierungen ('>')
    und Quelltext-Pfeile ('->').
    """
    if not text:
        return []

    lines = text.splitlines()
    frames: List[StackFrame] = []
    idx = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        match = _PDB_FRAME_REGEX.match(line)
        if match:
            is_current = bool(match.group("current"))
            fpath = match.group("path").strip()
            try:
                fline = int(match.group("line"))
            except ValueError:
                fline = 1

            raw_func = match.group("func").strip()
            # Bereinige Funktionssignaturen wie "foo()" oder "<module>()"
            func_name = raw_func if raw_func else "<module>()"

            code_line = ""
            if i + 1 < len(lines):
                code_match = _PDB_CODE_REGEX.match(lines[i + 1])
                if code_match:
                    code_line = code_match.group("code").strip()
                    i += 1

            frame = StackFrame(
                file_path=fpath,
                line_number=fline,
                function_name=func_name,
                code_line=code_line,
                is_current=is_current,
                frame_index=idx,
            )
            frames.append(frame)
            idx += 1
        i += 1

    return frames


def parse_pdb_eval_response(expression: str, output: str) -> Tuple[str, str, str]:
    """Parst die PDB-Ausgabe nach Ausführung von 'p <expression>' oder 'print(...)'.

    Gibt (value_str, type_str, status) zurück.
    """
    if not output:
        return ("<keine Ausgabe>", "", "pending")

    clean = output.strip()
    # PDB Prompts und führende Echos entfernen
    lines = [
        ln.strip()
        for ln in clean.splitlines()
        if ln.strip() and not ln.strip().startswith("(Pdb)")
    ]
    if not lines:
        return ("None", "NoneType", "ok")

    full_text = "\n".join(lines)

    # Auf Python-Fehlermeldungen prüfen
    if "***" in full_text or "Error:" in full_text:
        # Extrahiere Fehlertyp wenn möglich
        err_match = re.search(r"(\w+Error):\s*(.*)", full_text)
        if err_match:
            err_type = err_match.group(1)
            err_msg = err_match.group(2).strip()
            return (f"<{err_type}: {err_msg}>", err_type, "error")
        return (f"<{full_text}>", "Error", "error")

    # Ergebnis-Typ heuristisch ableiten
    first_val = lines[-1]
    if (first_val.startswith("'") and first_val.endswith("'")) or (
        first_val.startswith('"') and first_val.endswith('"')
    ):
        return (first_val, "str", "ok")
    if first_val in ("True", "False"):
        return (first_val, "bool", "ok")
    if first_val == "None":
        return ("None", "NoneType", "ok")
    if re.match(r"^-?\d+$", first_val):
        return (first_val, "int", "ok")
    if re.match(r"^-?\d+\.\d+$", first_val):
        return (first_val, "float", "ok")
    if first_val.startswith("[") and first_val.endswith("]"):
        return (first_val, "list", "ok")
    if first_val.startswith("{") and first_val.endswith("}"):
        return (first_val, "dict", "ok")
    if first_val.startswith("(") and first_val.endswith(")"):
        return (first_val, "tuple", "ok")

    return (first_val, "object", "ok")


def safe_eval_expression(
    expression: str, context: Optional[Dict[str, Any]] = None
) -> Tuple[str, str, str]:
    """Wertet einen Ausdruck in einem kontrollierten Kontext sicher aus.

    Gibt (value_repr, type_name, status) zurück.
    """
    expr_clean = expression.strip()
    if not expr_clean:
        return ("", "", "pending")

    eval_ctx = dict(context or {})
    # Erlaube grundlegende Builtins zur Auswertung arithmetischer und logischer Ausdrücke
    safe_builtins = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "round": round,
        "repr": repr,
        "type": type,
    }
    globals_dict = {"__builtins__": safe_builtins}

    try:
        result = eval(expr_clean, globals_dict, eval_ctx)
        val_str = repr(result)
        type_str = type(result).__name__
        return (val_str, type_str, "ok")
    except Exception as exc:
        err_type = type(exc).__name__
        return (f"<{err_type}: {exc}>", err_type, "error")
