#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Code-Folding System für CodeBox

Erkennt faltbare Code-Regionen (Funktionen, Klassen, Blöcke) für verschiedene
Programmiersprachen und steuert die native Block-Sichtbarkeit in QPlainTextEdit.
"""

from dataclasses import dataclass
import re
from typing import List, Optional, Set, Dict, Tuple


@dataclass
class FoldRegion:
    """Repräsentiert einen faltbaren Codebereich."""

    start_line: int  # 0-basierter Block-Index der Kopfzeile
    end_line: int    # 0-basierter Block-Index der letzten Zeile (inklusiv)
    kind: str        # 'function', 'class', 'block'
    name: str = ""   # z. B. 'my_func' oder 'MyClass'
    signature: str = ""  # Eindeutige Signatur zur Wiederherstellung nach Zeilenverschiebungen
    is_folded: bool = False

    @property
    def line_count(self) -> int:
        """Anzahl der Zeilen im Faltungsbereich."""
        return max(1, self.end_line - self.start_line + 1)


class FoldDetector:
    """Erkennt faltbare Regionen für Python und klammerbasierte Sprachen."""

    PYTHON_DEF_CLASS = re.compile(
        r'^[ \t]*(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)'
    )

    @classmethod
    def detect_python(cls, text: str) -> List[FoldRegion]:
        """Erkennt Funktionen und Klassen in Python über Einrückungsstrukturen."""
        lines = text.splitlines()
        regions: List[FoldRegion] = []
        n_lines = len(lines)

        class_scope: List[Tuple[int, str]] = []  # (indent, class_name)

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            indent = len(line) - len(line.lstrip())

            # Scope-Stack anpassen
            while class_scope and class_scope[-1][0] >= indent:
                class_scope.pop()

            m = cls.PYTHON_DEF_CLASS.match(line)
            if not m:
                continue

            name = m.group(1)
            is_class = bool(re.search(r'^[ \t]*class\b', line))
            kind = 'class' if is_class else 'function'

            if class_scope:
                qualified_name = f"{class_scope[-1][1]}.{name}"
            else:
                qualified_name = name

            if is_class:
                class_scope.append((indent, name))

            # Finde die letzte Zeile des Blocks (alle Zeilen mit j_indent > indent)
            last_idx = idx
            for j in range(idx + 1, n_lines):
                j_line = lines[j]
                j_stripped = j_line.strip()
                if not j_stripped:
                    continue
                j_indent = len(j_line) - len(j_line.lstrip())
                if j_indent > indent:
                    last_idx = j
                else:
                    break

            if last_idx > idx:
                sig = f"{kind}:{qualified_name}:{indent}"
                regions.append(FoldRegion(
                    start_line=idx,
                    end_line=last_idx,
                    kind=kind,
                    name=name,
                    signature=sig,
                ))

        # Äußere Blöcke zuerst, danach nach Startzeile
        regions.sort(key=lambda r: (r.start_line, -r.end_line))
        return regions

    @classmethod
    def detect_braces(cls, text: str) -> List[FoldRegion]:
        """Erkennt faltbare Bereiche über geschweifte Klammern { ... }."""
        lines = text.splitlines()
        regions: List[FoldRegion] = []
        stack: List[Tuple[int, str, str, str]] = []  # (start_line, kind, name, sig)

        func_class_re = re.compile(
            r'\b(?:class|function|struct|interface|fn|def|enum)\s+([A-Za-z_][A-Za-z0-9_]*)'
        )

        for idx, line in enumerate(lines):
            m = func_class_re.search(line)
            detected_name = m.group(1) if m else ""
            if m:
                matched_word = m.group(0).split()[0]
                detected_kind = "class" if matched_word in ("class", "struct", "interface") else "function"
            else:
                detected_kind = "block"

            in_string = None
            escaped = False
            i = 0
            while i < len(line):
                c = line[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif c == '\\':
                        escaped = True
                    elif c == in_string:
                        in_string = None
                elif c in ('"', "'", '`'):
                    in_string = c
                elif c == '/' and i + 1 < len(line) and line[i + 1] == '/':
                    # Einzeilen-Kommentar
                    break
                elif c == '{':
                    sig = f"{detected_kind}:{detected_name}:{idx}" if detected_name else f"block:{idx}"
                    stack.append((idx, detected_kind, detected_name, sig))
                elif c == '}':
                    if stack:
                        start_idx, kind, name, sig = stack.pop()
                        if idx > start_idx:
                            regions.append(FoldRegion(
                                start_line=start_idx,
                                end_line=idx,
                                kind=kind,
                                name=name,
                                signature=sig,
                            ))
                i += 1

        regions.sort(key=lambda r: (r.start_line, -r.end_line))
        return regions

    @classmethod
    def detect(cls, text: str, provider=None, filename: str = "") -> List[FoldRegion]:
        """Erkennt Faltungsbereiche basierend auf Provider oder Dateiendung."""
        lang_name = provider.get_name().lower() if provider else ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if lang_name == "python" or ext in ("py", "pyw", "pyi"):
            return cls.detect_python(text)

        brace_langs = {"javascript", "typescript", "c++", "cpp", "c", "rust", "go", "java", "json"}
        brace_exts = {"js", "ts", "jsx", "tsx", "cpp", "c", "h", "hpp", "rs", "go", "java", "json", "css"}

        if lang_name in brace_langs or ext in brace_exts:
            return cls.detect_braces(text)

        # Heuristik: Wenn Python-Muster zutreffen, nutze Python, sonst Braces
        py_res = cls.detect_python(text)
        if py_res:
            return py_res
        return cls.detect_braces(text)


class FoldingManager:
    """Verwaltet Faltungsbereiche und steuert die Sichtbarkeit von Blöcken im Editor."""

    def __init__(self, editor):
        self.editor = editor
        self.regions: List[FoldRegion] = []
        self._folded_signatures: Set[str] = set()
        self._regions_by_start: Dict[int, FoldRegion] = {}

    def update_regions(self, text: str, provider=None, filename: str = ""):
        """Aktualisiert die Faltungsbereiche für den Dokumenttext."""
        detected = FoldDetector.detect(text, provider=provider, filename=filename)
        self.regions = detected
        self._regions_by_start = {r.start_line: r for r in detected}

        # Faltungszustand über Signaturen wiederherstellen
        for r in self.regions:
            r.is_folded = r.signature in self._folded_signatures

        self.apply_visibility()

    def is_line_foldable(self, line: int) -> bool:
        """Gibt True zurück, wenn an dieser Zeile ein faltbarer Block beginnt."""
        return line in self._regions_by_start

    def is_line_folded(self, line: int) -> bool:
        """Gibt True zurück, wenn der Block an dieser Zeile aktuell eingeklappt ist."""
        reg = self._regions_by_start.get(line)
        return bool(reg and reg.is_folded)

    def get_region_at(self, line: int) -> Optional[FoldRegion]:
        """Gibt die Region zurück, die exakt an dieser Zeile beginnt."""
        return self._regions_by_start.get(line)

    def get_enclosing_region(self, line: int) -> Optional[FoldRegion]:
        """Gibt die kleinste Faltungsregion zurück, die diese Zeile enthält."""
        candidates = [
            r for r in self.regions
            if r.start_line <= line <= r.end_line
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda r: r.line_count)

    def toggle_fold(self, line: int) -> bool:
        """Schaltet die Faltung an der Zeile (oder der umfassenden Region) um."""
        reg = self.get_region_at(line)
        if not reg:
            reg = self.get_enclosing_region(line)
        if not reg:
            return False

        if reg.is_folded:
            self._unfold_region(reg)
        else:
            self._fold_region(reg)

        self.apply_visibility()
        return True

    def fold_line(self, line: int) -> bool:
        """Klappt den Block an dieser Zeile gezielt ein."""
        reg = self.get_region_at(line) or self.get_enclosing_region(line)
        if not reg:
            return False
        if not reg.is_folded:
            self._fold_region(reg)
            self.apply_visibility()
        return True

    def unfold_line(self, line: int) -> bool:
        """Klappt den Block an dieser Zeile gezielt aus."""
        reg = self.get_region_at(line) or self.get_enclosing_region(line)
        if not reg:
            return False
        if reg.is_folded:
            self._unfold_region(reg)
            self.apply_visibility()
        return True

    def _fold_region(self, reg: FoldRegion):
        reg.is_folded = True
        self._folded_signatures.add(reg.signature)

    def _unfold_region(self, reg: FoldRegion):
        reg.is_folded = False
        self._folded_signatures.discard(reg.signature)

    def fold_all(self):
        """Klappt alle erkannten Regionen im Dokument ein."""
        for r in self.regions:
            r.is_folded = True
            self._folded_signatures.add(r.signature)
        self.apply_visibility()

    def unfold_all(self):
        """Klappt alle Regionen im Dokument aus."""
        self._folded_signatures.clear()
        for r in self.regions:
            r.is_folded = False
        self.apply_visibility()

    def apply_visibility(self):
        """Wendet den Faltungszustand nativ auf die QTextBlock-Sichtbarkeiten an."""
        doc = self.editor.document()
        total_blocks = doc.blockCount()
        if total_blocks == 0:
            return

        # Bestimme alle ausgeblendeten Zeilenindizes
        hidden_lines: Set[int] = set()
        for r in self.regions:
            if r.is_folded:
                for line_idx in range(r.start_line + 1, min(r.end_line + 1, total_blocks)):
                    hidden_lines.add(line_idx)

        # Cursor vor Verstecken schützen: Wenn Cursor in versteckter Zeile liegt,
        # springt er auf die Kopfzeile des faltenden Blocks
        cursor = self.editor.textCursor()
        cur_line = cursor.blockNumber()
        if cur_line in hidden_lines:
            target_start = 0
            for r in self.regions:
                if r.is_folded and r.start_line < cur_line <= r.end_line:
                    target_start = r.start_line
                    break
            target_block = doc.findBlockByNumber(target_start)
            if target_block.isValid():
                cursor.setPosition(target_block.position())
                self.editor.setTextCursor(cursor)

        # QTextBlock.setVisible anwenden
        needs_dirty = False
        block = doc.firstBlock()
        while block.isValid():
            idx = block.blockNumber()
            should_be_visible = idx not in hidden_lines
            if block.isVisible() != should_be_visible:
                block.setVisible(should_be_visible)
                needs_dirty = True
            block = block.next()

        if needs_dirty:
            doc.markContentsDirty(0, doc.characterCount())
            self.editor.viewport().update()
            if hasattr(self.editor, 'lineNumberArea'):
                self.editor.lineNumberArea.update()
