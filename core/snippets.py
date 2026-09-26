#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snippet-Manager und Tab-Trigger-Erweiterung für CodeBox.
Verwaltet integrierte und benutzerdefinierte Code-Snippets mit Tab-Stops,
Platzhaltern ($1, ${1:default}, $0) und sprachspezifischer Auflösung.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from PySide6.QtGui import QTextCursor

if TYPE_CHECKING:
    from core.editor import CodeEditor

logger = logging.getLogger("CodeBox.Snippets")

# Standard-Speicherort für benutzerdefinierte Snippets
_DEFAULT_CUSTOM_FILE = Path(__file__).resolve().parent.parent / "config" / "snippets.json"


@dataclass
class SnippetTabStop:
    """Repräsentiert einen Tab-Stop innerhalb eines expandierten Snippets."""
    index: int
    start_offset: int
    length: int
    default_text: str = ""


@dataclass
class Snippet:
    """Definition eines Code-Snippets."""
    trigger: str
    description: str
    body: str
    language: str = "all"
    is_custom: bool = False

    def render_plain(self) -> str:
        """Gibt das Snippet ohne Platzhalter-Syntax zurück."""
        text, _ = parse_snippet(self.body)
        return text


def parse_snippet(template: str) -> Tuple[str, List[SnippetTabStop]]:
    """
    Parst eine Snippet-Vorlage mit Platzhalter-Syntax:
      - $0: Finale Cursor-Position (Exit-Point)
      - $1, $2, ...: Einfache Tab-Stops
      - ${1:default_text}: Tab-Stop mit editierbarem Standardwert
      - \\$: Maskiertes Dollar-Zeichen

    Rückgabe:
      (rendered_text, sorted_tab_stops)
    """
    pattern = re.compile(r'(?<!\\)\$([0-9]+)|(?<!\\)\$\{([0-9]+)(?::([^}]*))?\}')

    rendered_parts: List[str] = []
    tab_stops: List[SnippetTabStop] = []
    current_offset = 0
    last_end = 0

    for match in pattern.finditer(template):
        # Text vor dem Match anhängen
        prefix = template[last_end:match.start()]
        prefix_clean = prefix.replace(r"\$", "$")
        rendered_parts.append(prefix_clean)
        current_offset += len(prefix_clean)

        if match.group(1) is not None:
            # $N
            idx = int(match.group(1))
            default_val = ""
        else:
            # ${N:default}
            idx = int(match.group(2))
            default_val = match.group(3) if match.group(3) is not None else ""

        default_clean = default_val.replace(r"\$", "$")
        rendered_parts.append(default_clean)
        tab_stops.append(SnippetTabStop(
            index=idx,
            start_offset=current_offset,
            length=len(default_clean),
            default_text=default_clean,
        ))
        current_offset += len(default_clean)
        last_end = match.end()

    # Restlichen Text anhängen
    suffix = template[last_end:]
    suffix_clean = suffix.replace(r"\$", "$")
    rendered_parts.append(suffix_clean)

    rendered_text = "".join(rendered_parts)

    # Prüfen, ob $0 definiert wurde
    has_zero = any(ts.index == 0 for ts in tab_stops)
    if not has_zero:
        # Standardmäßiger Exit-Point am Ende des Texts
        tab_stops.append(SnippetTabStop(
            index=0,
            start_offset=len(rendered_text),
            length=0,
            default_text="",
        ))

    # Tab-Stops sortieren: 1, 2, 3, ..., und $0 als allerletztes
    regular_stops = sorted([ts for ts in tab_stops if ts.index > 0], key=lambda ts: ts.index)
    zero_stops = [ts for ts in tab_stops if ts.index == 0]
    sorted_stops = regular_stops + zero_stops

    return rendered_text, sorted_stops


class SnippetSession:
    """
    Verwaltet eine aktive Snippet-Navigation im Editor.
    Erlaubt das Vor- und Zurückspringen zwischen Platzhaltern per Tab und Shift+Tab.
    """

    def __init__(self, editor: "CodeEditor", base_pos: int, rendered_text: str, tab_stops: List[SnippetTabStop]):
        self.editor = editor
        self.base_pos = base_pos
        self.rendered_text = rendered_text
        self._is_active = True

        doc = editor.document()
        self._cursor_stops: List[Tuple[int, QTextCursor, str]] = []

        for stop in tab_stops:
            cur = QTextCursor(doc)
            start = base_pos + stop.start_offset
            cur.setPosition(start)
            if stop.length > 0:
                cur.setPosition(start + stop.length, QTextCursor.MoveMode.KeepAnchor)
            self._cursor_stops.append((stop.index, cur, stop.default_text))

        self.regular_stops = [item for item in self._cursor_stops if item[0] > 0]
        self.exit_stops = [item for item in self._cursor_stops if item[0] == 0]
        self.current_idx = -1

    @property
    def is_active(self) -> bool:
        return self._is_active

    def start(self):
        """Startet die Sitzung und markiert den ersten Platzhalter."""
        if self.regular_stops:
            self.current_idx = 0
            self._activate_stop(self.regular_stops[0])
        else:
            self.finish()

    def _activate_stop(self, stop_item: Tuple[int, QTextCursor, str]):
        _, cursor, _ = stop_item
        # Prüfen ob Cursor im gültigen Dokumentbereich liegt
        doc_len = self.editor.document().characterCount()
        start = max(0, min(cursor.selectionStart(), doc_len - 1))
        end = max(0, min(cursor.selectionEnd(), doc_len - 1))

        tc = QTextCursor(self.editor.document())
        tc.setPosition(start)
        if end > start:
            tc.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(tc)

    def next_stop(self) -> bool:
        """Springt zum nächsten Platzhalter oder beendet am $0-Punkt."""
        if not self._is_active:
            return False

        if self.current_idx + 1 < len(self.regular_stops):
            self.current_idx += 1
            self._activate_stop(self.regular_stops[self.current_idx])
            return True
        else:
            self.finish()
            return True

    def prev_stop(self) -> bool:
        """Springt zum vorherigen Platzhalter zurück."""
        if not self._is_active or self.current_idx <= 0:
            return False

        self.current_idx -= 1
        self._activate_stop(self.regular_stops[self.current_idx])
        return True

    def finish(self):
        """Beendet die Snippet-Sitzung und positioniert den Cursor auf $0."""
        self._is_active = False
        if self.exit_stops:
            _, exit_cur, _ = self.exit_stops[0]
            doc_len = self.editor.document().characterCount()
            start = max(0, min(exit_cur.selectionStart(), doc_len - 1))
            end = max(0, min(exit_cur.selectionEnd(), doc_len - 1))
            tc = QTextCursor(self.editor.document())
            tc.setPosition(start)
            if end > start:
                tc.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            self.editor.setTextCursor(tc)

    def cancel(self):
        """Bricht die Sitzung ab, ohne den Cursor zu verändern."""
        self._is_active = False


class SnippetManager:
    """Zentraler Verwalter aller Snippets in CodeBox."""

    _instance: Optional[SnippetManager] = None

    def __init__(self, custom_file: Optional[Path] = None):
        self.custom_file = custom_file or _DEFAULT_CUSTOM_FILE
        self._builtins: List[Snippet] = []
        self._customs: List[Snippet] = []
        self._init_builtins()
        self.load_custom_snippets()

    @classmethod
    def get_instance(cls) -> SnippetManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, manager: SnippetManager):
        cls._instance = manager

    def _init_builtins(self):
        """Initialisiert die Standard-Snippets für gängige Sprachen."""
        # 1. Python
        py_snippets = [
            Snippet("def", "Funktionsdefinition", "def ${1:name}(${2:args}):\n    ${0:pass}", "python"),
            Snippet("asyncdef", "Asynchrone Funktionsdefinition", "async def ${1:name}(${2:args}):\n    ${0:pass}", "python"),
            Snippet("class", "Klassendefinition mit Konstruktor", 'class ${1:ClassName}:\n    """${2:Docstring}"""\n\n    def __init__(self${3:, args}):\n        ${0:pass}', "python"),
            Snippet("if", "If-Bedingung", "if ${1:condition}:\n    ${0:pass}", "python"),
            Snippet("ifelse", "If-Else-Verzweigung", "if ${1:condition}:\n    ${2:pass}\nelse:\n    ${0:pass}", "python"),
            Snippet("elif", "Elif-Bedingung", "elif ${1:condition}:\n    ${0:pass}", "python"),
            Snippet("for", "For-in-Schleife", "for ${1:item} in ${2:items}:\n    ${0:pass}", "python"),
            Snippet("while", "While-Schleife", "while ${1:condition}:\n    ${0:pass}", "python"),
            Snippet("try", "Try-Except-Block", "try:\n    ${1:pass}\nexcept ${2:Exception} as ${3:e}:\n    ${0:pass}", "python"),
            Snippet("tryfin", "Try-Except-Finally-Block", "try:\n    ${1:pass}\nexcept ${2:Exception} as ${3:e}:\n    ${4:pass}\nfinally:\n    ${0:pass}", "python"),
            Snippet("with", "With-Kontextmanager", "with ${1:context} as ${2:var}:\n    ${0:pass}", "python"),
            Snippet("main", "Main-Guard", 'if __name__ == "__main__":\n    ${0:main()}', "python"),
            Snippet("prop", "Property Getter", "@property\ndef ${1:prop_name}(self):\n    return self._${1:prop_name}", "python"),
            Snippet("init", "__init__ Methode", "def __init__(self${1:, args}):\n    ${0:pass}", "python"),
            Snippet("repr", "__repr__ Repräsentation", 'def __repr__(self):\n    return f"${1:ClassName}({self.${2:attr}!r})"', "python"),
            Snippet("lambda", "Lambda-Ausdruck", "lambda ${1:args}: ${0:expr}", "python"),
            Snippet("print", "Print-Ausgabe", "print(${0:object})", "python"),
            Snippet("doc", "Google-Style Docstring", '"""${1:Kurzbeschreibung}\n\nArgs:\n    ${2:arg}: ${3:Beschreibung}\n\nReturns:\n    ${4:Beschreibung}\n"""', "python"),
        ]

        # 2. JavaScript / TypeScript
        js_snippets = [
            Snippet("fn", "Funktionsdeklaration", "function ${1:name}(${2:params}) {\n    ${0}\n}", "javascript"),
            Snippet("afn", "Pfeilfunktion (Arrow Function)", "const ${1:name} = (${2:params}) => {\n    ${0}\n};", "javascript"),
            Snippet("class", "Klassendefinition mit Konstruktor", "class ${1:ClassName} {\n    constructor(${2:params}) {\n        ${0}\n    }\n}", "javascript"),
            Snippet("if", "If-Bedingung", "if (${1:condition}) {\n    ${0}\n}", "javascript"),
            Snippet("ifelse", "If-Else-Verzweigung", "if (${1:condition}) {\n    ${2}\n} else {\n    ${0}\n}", "javascript"),
            Snippet("for", "Klassische For-Schleife", "for (let ${1:i} = 0; ${1:i} < ${2:length}; ${1:i}++) {\n    ${0}\n}", "javascript"),
            Snippet("forof", "For-of-Schleife", "for (const ${1:item} of ${2:items}) {\n    ${0}\n}", "javascript"),
            Snippet("forin", "For-in-Schleife", "for (const ${1:key} in ${2:object}) {\n    ${0}\n}", "javascript"),
            Snippet("try", "Try-Catch-Block", "try {\n    ${1}\n} catch (${2:error}) {\n    ${0}\n}", "javascript"),
            Snippet("clg", "Konsolenausgabe (console.log)", "console.log(${0:msg});", "javascript"),
            Snippet("cerr", "Konsolenfehler (console.error)", "console.error(${0:msg});", "javascript"),
            Snippet("import", "Modul-Import", "import { ${1:exports} } from '${2:module}';", "javascript"),
            Snippet("prom", "Promise-Instanz", "new Promise((resolve, reject) => {\n    ${0}\n});", "javascript"),
            Snippet("asyncfn", "Asynchrone Funktion", "async function ${1:name}(${2:params}) {\n    ${0}\n}", "javascript"),
        ]

        # 3. TypeScript
        ts_snippets = [
            Snippet("interface", "Interface-Deklaration", "interface ${1:Name} {\n    ${2:property}: ${3:type};\n}", "typescript"),
            Snippet("type", "Typ-Alias", "type ${1:Name} = ${2:type};", "typescript"),
            Snippet("enum", "Enum-Deklaration", "enum ${1:Name} {\n    ${2:Value} = ${3:0},\n}", "typescript"),
        ]

        # 4. C / C++
        cpp_snippets = [
            Snippet("main", "Main-Funktion", "int main(int argc, char* argv[]) {\n    ${0}\n    return 0;\n}", "cpp"),
            Snippet("class", "C++ Klasse", "class ${1:ClassName} {\npublic:\n    ${1:ClassName}();\n    ~${1:ClassName}();\nprivate:\n    ${0}\n};", "cpp"),
            Snippet("for", "For-Schleife", "for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n    ${0}\n}", "cpp"),
            Snippet("cout", "Konsolenausgabe std::cout", "std::cout << ${1:msg} << std::endl;", "cpp"),
            Snippet("include", "Header einbinden", "#include <${1:iostream}>", "cpp"),
        ]

        # 5. Rust
        rust_snippets = [
            Snippet("fn", "Funktionsdefinition", "fn ${1:name}(${2:params}) -> ${3:ReturnType} {\n    ${0}\n}", "rust"),
            Snippet("struct", "Struktur-Definition", "struct ${1:Name} {\n    ${2:field}: ${3:Type},\n}", "rust"),
            Snippet("enum", "Enum-Definition", "enum ${1:Name} {\n    ${2:Variant},\n}", "rust"),
            Snippet("impl", "Implementierungsblock", "impl ${1:Type} {\n    pub fn new(${2:args}) -> Self {\n        ${0:Self {}}\n    }\n}", "rust"),
            Snippet("match", "Match-Mustervergleich", "match ${1:expr} {\n    ${2:pattern} => ${0:expr},\n}", "rust"),
            Snippet("println", "Konsolenausgabe println!", 'println!("${1:format}", ${0:args});', "rust"),
        ]

        # 6. Go
        go_snippets = [
            Snippet("func", "Funktionsdefinition", "func ${1:name}(${2:params}) ${3:error} {\n    ${0}\n}", "go"),
            Snippet("main", "Go Main-Paket", 'package main\n\nimport "fmt"\n\nfunc main() {\n    ${0:fmt.Println("Hello")}\n}', "go"),
            Snippet("struct", "Struct-Definition", "type ${1:Name} struct {\n    ${2:Field} ${3:string}\n}", "go"),
            Snippet("interface", "Interface-Definition", "type ${1:Name} interface {\n    ${2:Method}() ${3:error}\n}", "go"),
            Snippet("iferr", "Error-Check Idiom", "if err != nil {\n    return ${0:err}\n}", "go"),
        ]

        # 7. Java
        java_snippets = [
            Snippet("main", "Main-Methode", "public static void main(String[] args) {\n    ${0}\n}", "java"),
            Snippet("class", "Klassen-Definition", "public class ${1:ClassName} {\n    public ${1:ClassName}() {\n        ${0}\n    }\n}", "java"),
            Snippet("sout", "System.out.println", "System.out.println(${0});", "java"),
            Snippet("for", "For-Schleife", "for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n    ${0}\n}", "java"),
            Snippet("try", "Try-Catch-Block", "try {\n    ${1}\n} catch (${2:Exception} ${3:e}) {\n    ${0:e.printStackTrace();}\n}", "java"),
        ]

        # 8. HTML
        html_snippets = [
            Snippet("html5", "HTML5 Grundgerüst", '<!DOCTYPE html>\n<html lang="de">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>${1:Titel}</title>\n</head>\n<body>\n    ${0}\n</body>\n</html>', "html"),
            Snippet("div", "Div-Container", '<div class="${1:container}">\n    ${0}\n</div>', "html"),
            Snippet("btn", "Schaltfläche (Button)", '<button type="${1:button}" class="${2:btn}">${0:Klick}</button>', "html"),
            Snippet("script", "Script-Tag", '<script src="${1:app.js}"></script>', "html"),
            Snippet("link", "Stylesheet Link-Tag", '<link rel="stylesheet" href="${1:style.css}">', "html"),
        ]

        # 9. Markdown
        md_snippets = [
            Snippet("link", "Markdown Link", "[${1:Text}](${2:url})", "markdown"),
            Snippet("img", "Markdown Bild", "![${1:Alt-Text}](${2:pfad})", "markdown"),
            Snippet("code", "Codeblock mit Syntaxhervorhebung", "```${1:python}\n${0}\n```", "markdown"),
            Snippet("tbl", "Markdown Tabelle", "| ${1:Spalte 1} | ${2:Spalte 2} |\n|---|---|\n| ${3:Wert 1} | ${4:Wert 2} |", "markdown"),
            Snippet("todo", "Aufgaben-Checkbox", "- [ ] ${0:Aufgabe}", "markdown"),
        ]

        # 10. Globale Snippets (Sprachunabhängig)
        global_snippets = [
            Snippet("todo", "TODO-Kommentar", "# TODO: ${0:Aufgabe}", "all"),
            Snippet("fixme", "FIXME-Kommentar", "# FIXME: ${0:Problem}", "all"),
            Snippet("note", "NOTE-Hinweis", "# NOTE: ${0:Hinweis}", "all"),
        ]

        self._builtins = (
            py_snippets + js_snippets + ts_snippets + cpp_snippets +
            rust_snippets + go_snippets + java_snippets + html_snippets +
            md_snippets + global_snippets
        )

    def load_custom_snippets(self):
        """Lädt benutzerdefinierte Snippets aus der JSON-Konfigurationsdatei."""
        self._customs.clear()
        if not self.custom_file.exists():
            return

        try:
            with open(self.custom_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "trigger" in item and "body" in item:
                        snippet = Snippet(
                            trigger=item["trigger"],
                            description=item.get("description", ""),
                            body=item["body"],
                            language=item.get("language", "all").lower(),
                            is_custom=True,
                        )
                        self._customs.append(snippet)
        except Exception as e:
            logger.warning("Fehler beim Laden benutzerdefinierter Snippets aus %s: %s", self.custom_file, e)

    def save_custom_snippets(self) -> bool:
        """Speichert die benutzerdefinierten Snippets in die JSON-Konfigurationsdatei."""
        try:
            self.custom_file.parent.mkdir(parents=True, exist_ok=True)
            data = [
                {
                    "trigger": s.trigger,
                    "description": s.description,
                    "body": s.body,
                    "language": s.language,
                }
                for s in self._customs
            ]
            with open(self.custom_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Fehler beim Speichern benutzerdefinierter Snippets: %s", e)
            return False

    def add_custom_snippet(self, snippet: Snippet) -> bool:
        """Fügt ein benutzerdefiniertes Snippet hinzu oder aktualisiert ein bestehendes."""
        snippet.is_custom = True
        snippet.language = snippet.language.lower()

        # Altes Snippet mit gleichem Trigger und Sprache ersetzen
        self._customs = [
            s for s in self._customs
            if not (s.trigger == snippet.trigger and s.language == snippet.language)
        ]
        self._customs.append(snippet)
        return self.save_custom_snippets()

    def remove_custom_snippet(self, trigger: str, language: str) -> bool:
        """Entfernt ein benutzerdefiniertes Snippet."""
        lang = language.lower()
        before = len(self._customs)
        self._customs = [
            s for s in self._customs
            if not (s.trigger == trigger and s.language == lang)
        ]
        if len(self._customs) != before:
            self.save_custom_snippets()
            return True
        return False

    def get_snippet(self, trigger: str, language: str = "") -> Optional[Snippet]:
        """
        Sucht ein Snippet anhand des Triggers.
        Priorität:
          1. Benutzerdefiniertes Snippet für die spezifische Sprache
          2. Integriertes Snippet für die spezifische Sprache
          3. Benutzerdefiniertes globales Snippet ('all')
          4. Integriertes globales Snippet ('all')
        """
        lang = language.lower()

        # 1. Custom exact match
        for s in self._customs:
            if s.trigger == trigger and (s.language == lang or (lang in ("typescript", "javascript") and s.language in ("typescript", "javascript"))):
                return s

        # 2. Builtin exact match
        for s in self._builtins:
            if s.trigger == trigger and (s.language == lang or (lang in ("typescript", "javascript") and s.language in ("typescript", "javascript"))):
                return s

        # 3. Custom global match
        for s in self._customs:
            if s.trigger == trigger and s.language in ("all", ""):
                return s

        # 4. Builtin global match
        for s in self._builtins:
            if s.trigger == trigger and s.language in ("all", ""):
                return s

        return None

    def get_snippets_for_language(self, language: str = "") -> List[Snippet]:
        """Gibt alle Snippets zurück, die für eine Sprache relevant sind (inklusive 'all')."""
        lang = language.lower()
        results: Dict[str, Snippet] = {}

        # Builtins zuerst
        for s in self._builtins:
            if not lang or s.language in ("all", "") or s.language == lang or (
                lang in ("typescript", "javascript") and s.language in ("typescript", "javascript")
            ):
                key = f"{s.language}:{s.trigger}"
                results[key] = s

        # Customs überschreiben Builtins
        for s in self._customs:
            if not lang or s.language in ("all", "") or s.language == lang or (
                lang in ("typescript", "javascript") and s.language in ("typescript", "javascript")
            ):
                key = f"{s.language}:{s.trigger}"
                results[key] = s

        return list(results.values())

    def all_snippets(self) -> List[Snippet]:
        """Gibt alle registrierten Snippets (Builtins und Customs) zurück."""
        results: Dict[str, Snippet] = {}
        for s in self._builtins:
            results[f"{s.language}:{s.trigger}"] = s
        for s in self._customs:
            results[f"{s.language}:{s.trigger}"] = s
        return list(results.values())
