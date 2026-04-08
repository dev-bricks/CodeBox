# CodeBox - Multi-Language IDE Konzept

> Basierend auf PythonBox v8 - Erweiterung zur universellen Code-Umgebung

---

## 🎯 Vision

**CodeBox** ist eine leichtgewichtige, erweiterbare IDE für mehrere Programmiersprachen.
Sie behält die Einfachheit von PythonBox, bietet aber sprachspezifische Unterstützung
für die gängigsten Sprachen.

### Zielgruppe
- Entwickler die eine schnelle, leichte Alternative zu VS Code/JetBrains suchen
- Lernende die mehrere Sprachen in einer einheitlichen Umgebung nutzen wollen
- Snippet-Sammler für verschiedene Technologien

### Design-Prinzipien
1. **Modular**: Sprachen als austauschbare Plugins
2. **Leichtgewichtig**: Schneller Start, geringer RAM-Verbrauch
3. **Einheitlich**: Gleiche UX für alle Sprachen
4. **Erweiterbar**: Neue Sprachen einfach hinzufügbar

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                        CodeBox Core                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Editor    │  │  Tab System │  │   Output Panel      │  │
│  │  (QPlainT.) │  │             │  │   (Debug/Run)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Language Abstraction Layer                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  LanguageProvider (Abstract Base Class)                 ││
│  │  - get_name() -> str                                    ││
│  │  - get_extensions() -> List[str]                        ││
│  │  - get_highlighter() -> QSyntaxHighlighter              ││
│  │  - get_completer_words() -> List[str]                   ││
│  │  - get_snippets() -> Dict[str, str]                     ││
│  │  - get_run_command(file) -> List[str]                   ││
│  │  - get_debug_command(file) -> List[str]                 ││
│  │  - get_linter() -> Optional[LinterProvider]             ││
│  │  - get_comment_style() -> Tuple[str, str]               ││
│  └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    Language Providers                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Python  │ │JavaScript│ │   C/C++  │ │   Rust   │ ...   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Unterstützte Sprachen (Phase 1)

| Sprache | Extensions | Run Command | Debugger | Linter |
|---------|------------|-------------|----------|--------|
| **Python** | .py, .pyw | `python {file}` | pdb | flake8/pylint |
| **JavaScript** | .js, .mjs | `node {file}` | node --inspect | eslint |
| **TypeScript** | .ts | `ts-node {file}` | ts-node --inspect | tsc |
| **C** | .c, .h | `gcc -o out {file} && ./out` | gdb | gcc -Wall |
| **C++** | .cpp, .hpp | `g++ -o out {file} && ./out` | gdb | g++ -Wall |
| **Rust** | .rs | `rustc {file} && ./out` | rust-gdb | rustc |
| **Go** | .go | `go run {file}` | delve | go vet |
| **Java** | .java | `javac {file} && java {class}` | jdb | javac |

---

## 🧩 Komponenten-Details

### 1. LanguageProvider Basis-Klasse

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional

class LanguageProvider(ABC):
    """Abstrakte Basisklasse für Sprachunterstützung"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Anzeigename der Sprache"""
        pass
    
    @abstractmethod
    def get_extensions(self) -> List[str]:
        """Unterstützte Dateiendungen (ohne Punkt)"""
        pass
    
    @abstractmethod
    def get_highlighter_rules(self) -> List[Tuple[str, QTextCharFormat]]:
        """Regex-Patterns und Formate für Syntax-Highlighting"""
        pass
    
    @abstractmethod
    def get_keywords(self) -> List[str]:
        """Keywords für Auto-Completion"""
        pass
    
    def get_builtins(self) -> List[str]:
        """Built-in Funktionen (optional)"""
        return []
    
    def get_snippets(self) -> Dict[str, str]:
        """Code-Snippets {trigger: expansion}"""
        return {}
    
    @abstractmethod
    def get_run_command(self, file_path: str) -> List[str]:
        """Kommando zum Ausführen"""
        pass
    
    def get_debug_command(self, file_path: str) -> Optional[List[str]]:
        """Kommando zum Debuggen (None = nicht verfügbar)"""
        return None
    
    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        """Linter-Kommando (None = kein Linter)"""
        return None
    
    def parse_linter_output(self, output: str) -> List[Dict]:
        """Parsed Linter-Output zu strukturierten Fehlern"""
        return []
    
    def get_comment_style(self) -> Tuple[str, Optional[str]]:
        """(Einzeilen-Kommentar, Mehrzeilen-Start/Ende oder None)"""
        return ("//", ("/*", "*/"))
    
    def get_bracket_pairs(self) -> Dict[str, str]:
        """Klammer-Paare für Matching"""
        return {'(': ')', '[': ']', '{': '}'}
    
    def get_auto_close_pairs(self) -> Dict[str, str]:
        """Auto-Close Paare"""
        return {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
    
    def get_indent_triggers(self) -> List[str]:
        """Zeichen/Wörter die Einrückung auslösen"""
        return ['{']
    
    def get_dedent_triggers(self) -> List[str]:
        """Zeichen/Wörter die Ausrückung auslösen"""
        return ['}']
```

### 2. Beispiel: Python Provider

```python
class PythonProvider(LanguageProvider):
    def get_name(self) -> str:
        return "Python"
    
    def get_extensions(self) -> List[str]:
        return ["py", "pyw", "pyi"]
    
    def get_keywords(self) -> List[str]:
        return [
            'False', 'None', 'True', 'and', 'as', 'assert', 'async',
            'await', 'break', 'class', 'continue', 'def', 'del', 'elif',
            'else', 'except', 'finally', 'for', 'from', 'global', 'if',
            'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'try', 'while', 'with', 'yield'
        ]
    
    def get_builtins(self) -> List[str]:
        return [
            'abs', 'all', 'any', 'bin', 'bool', 'bytes', 'callable',
            'chr', 'dict', 'dir', 'enumerate', 'eval', 'exec', 'filter',
            'float', 'format', 'getattr', 'globals', 'hasattr', 'hash',
            'hex', 'id', 'input', 'int', 'isinstance', 'issubclass',
            'iter', 'len', 'list', 'locals', 'map', 'max', 'min', 'next',
            'object', 'open', 'ord', 'pow', 'print', 'range', 'repr',
            'reversed', 'round', 'set', 'setattr', 'slice', 'sorted',
            'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip'
        ]
    
    def get_snippets(self) -> Dict[str, str]:
        return {
            'def': 'def ${1:name}(${2:args}):\n    ${3:pass}',
            'class': 'class ${1:Name}:\n    def __init__(self):\n        ${2:pass}',
            'if': 'if ${1:condition}:\n    ${2:pass}',
            'for': 'for ${1:item} in ${2:items}:\n    ${3:pass}',
            'try': 'try:\n    ${1:pass}\nexcept ${2:Exception} as e:\n    ${3:pass}',
            'with': 'with ${1:context} as ${2:var}:\n    ${3:pass}',
            'main': 'if __name__ == "__main__":\n    ${1:main()}',
        }
    
    def get_run_command(self, file_path: str) -> List[str]:
        return ["python", "-u", file_path]
    
    def get_debug_command(self, file_path: str) -> List[str]:
        return ["python", "-m", "pdb", file_path]
    
    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("flake8"):
            return ["flake8", "--format=%(row)d:%(col)d:%(code)s:%(text)s", file_path]
        elif shutil.which("pylint"):
            return ["pylint", "--output-format=text", file_path]
        return None
    
    def get_comment_style(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        return ("#", ('"""', '"""'))
    
    def get_indent_triggers(self) -> List[str]:
        return [':']  # Nach : wird eingerückt
    
    def get_dedent_triggers(self) -> List[str]:
        return ['return', 'break', 'continue', 'pass', 'raise']
```

### 3. Beispiel: JavaScript Provider

```python
class JavaScriptProvider(LanguageProvider):
    def get_name(self) -> str:
        return "JavaScript"
    
    def get_extensions(self) -> List[str]:
        return ["js", "mjs", "cjs"]
    
    def get_keywords(self) -> List[str]:
        return [
            'break', 'case', 'catch', 'class', 'const', 'continue',
            'debugger', 'default', 'delete', 'do', 'else', 'export',
            'extends', 'false', 'finally', 'for', 'function', 'if',
            'import', 'in', 'instanceof', 'let', 'new', 'null', 'return',
            'static', 'super', 'switch', 'this', 'throw', 'true', 'try',
            'typeof', 'var', 'void', 'while', 'with', 'yield', 'async',
            'await', 'of'
        ]
    
    def get_builtins(self) -> List[str]:
        return [
            'Array', 'Boolean', 'Date', 'Error', 'Function', 'JSON',
            'Map', 'Math', 'Number', 'Object', 'Promise', 'Proxy',
            'RegExp', 'Set', 'String', 'Symbol', 'WeakMap', 'WeakSet',
            'console', 'parseInt', 'parseFloat', 'isNaN', 'isFinite',
            'decodeURI', 'encodeURI', 'setTimeout', 'setInterval',
            'clearTimeout', 'clearInterval', 'fetch', 'require', 'module'
        ]
    
    def get_snippets(self) -> Dict[str, str]:
        return {
            'fn': 'function ${1:name}(${2:params}) {\n    ${3}\n}',
            'afn': 'const ${1:name} = (${2:params}) => {\n    ${3}\n};',
            'class': 'class ${1:Name} {\n    constructor(${2:params}) {\n        ${3}\n    }\n}',
            'if': 'if (${1:condition}) {\n    ${2}\n}',
            'for': 'for (let ${1:i} = 0; ${1:i} < ${2:length}; ${1:i}++) {\n    ${3}\n}',
            'foreach': '${1:array}.forEach((${2:item}) => {\n    ${3}\n});',
            'try': 'try {\n    ${1}\n} catch (${2:error}) {\n    ${3}\n}',
            'log': 'console.log(${1});',
            'async': 'async function ${1:name}(${2:params}) {\n    ${3}\n}',
        }
    
    def get_run_command(self, file_path: str) -> List[str]:
        return ["node", file_path]
    
    def get_debug_command(self, file_path: str) -> List[str]:
        return ["node", "--inspect-brk", file_path]
    
    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        if shutil.which("eslint"):
            return ["eslint", "-f", "compact", file_path]
        return None
```

### 4. Beispiel: C/C++ Provider

```python
class CppProvider(LanguageProvider):
    def get_name(self) -> str:
        return "C++"
    
    def get_extensions(self) -> List[str]:
        return ["cpp", "cc", "cxx", "hpp", "h", "c"]
    
    def get_keywords(self) -> List[str]:
        return [
            'alignas', 'alignof', 'and', 'and_eq', 'asm', 'auto',
            'bitand', 'bitor', 'bool', 'break', 'case', 'catch',
            'char', 'class', 'const', 'constexpr', 'continue', 'default',
            'delete', 'do', 'double', 'else', 'enum', 'explicit',
            'export', 'extern', 'false', 'float', 'for', 'friend',
            'goto', 'if', 'inline', 'int', 'long', 'mutable', 'namespace',
            'new', 'noexcept', 'not', 'nullptr', 'operator', 'or',
            'private', 'protected', 'public', 'return', 'short', 'signed',
            'sizeof', 'static', 'struct', 'switch', 'template', 'this',
            'throw', 'true', 'try', 'typedef', 'typeid', 'typename',
            'union', 'unsigned', 'using', 'virtual', 'void', 'volatile',
            'while', 'include', 'define', 'ifdef', 'ifndef', 'endif'
        ]
    
    def get_builtins(self) -> List[str]:
        return [
            'std', 'cout', 'cin', 'endl', 'string', 'vector', 'map',
            'set', 'pair', 'make_pair', 'sort', 'find', 'begin', 'end',
            'push_back', 'pop_back', 'size', 'empty', 'clear', 'printf',
            'scanf', 'malloc', 'free', 'sizeof', 'NULL', 'nullptr'
        ]
    
    def get_snippets(self) -> Dict[str, str]:
        return {
            'main': 'int main(int argc, char* argv[]) {\n    ${1}\n    return 0;\n}',
            'class': 'class ${1:Name} {\npublic:\n    ${1:Name}();\n    ~${1:Name}();\nprivate:\n    ${2}\n};',
            'for': 'for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n    ${3}\n}',
            'foreach': 'for (auto& ${1:item} : ${2:container}) {\n    ${3}\n}',
            'if': 'if (${1:condition}) {\n    ${2}\n}',
            'inc': '#include <${1:iostream}>',
            'guard': '#ifndef ${1:HEADER}_H\n#define ${1:HEADER}_H\n\n${2}\n\n#endif',
        }
    
    def get_run_command(self, file_path: str) -> List[str]:
        output = file_path.rsplit('.', 1)[0]
        if sys.platform == "win32":
            output += ".exe"
        # Kompilieren und ausführen
        return ["g++", "-o", output, file_path, "&&", output]
    
    def get_debug_command(self, file_path: str) -> List[str]:
        output = file_path.rsplit('.', 1)[0]
        return ["gdb", output]
    
    def get_linter_command(self, file_path: str) -> Optional[List[str]]:
        return ["g++", "-Wall", "-Wextra", "-fsyntax-only", file_path]
```

---

## 🔧 Syntax Highlighting System

```python
class UniversalHighlighter(QSyntaxHighlighter):
    """Universeller Syntax-Highlighter basierend auf LanguageProvider"""
    
    def __init__(self, document, provider: LanguageProvider):
        super().__init__(document)
        self.provider = provider
        self.rules = self._build_rules()
    
    def _build_rules(self) -> List[Tuple[QRegExp, QTextCharFormat]]:
        rules = []
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        
        for word in self.provider.get_keywords():
            pattern = QRegExp(f"\\b{word}\\b")
            rules.append((pattern, keyword_format))
        
        # Builtins
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#DCDCAA"))
        
        for word in self.provider.get_builtins():
            pattern = QRegExp(f"\\b{word}\\b")
            rules.append((pattern, builtin_format))
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))
        rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        rules.append((QRegExp(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))
        rules.append((QRegExp(r"\b[0-9]+\.?[0-9]*\b"), number_format))
        
        # Comments (basierend auf Provider)
        comment_style = self.provider.get_comment_style()
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        comment_format.setFontItalic(True)
        
        single_comment = comment_style[0]
        if single_comment:
            escaped = QRegExp.escape(single_comment)
            rules.append((QRegExp(f"{escaped}.*"), comment_format))
        
        return rules
    
    def highlightBlock(self, text: str):
        for pattern, format in self.rules:
            index = pattern.indexIn(text)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, format)
                index = pattern.indexIn(text, index + length)
```

---

## 📁 Dateistruktur

```
CodeBox/
├── main.py                     # Einstiegspunkt
├── core/
│   ├── __init__.py
│   ├── editor.py               # CodeEditor Komponente
│   ├── tabs.py                 # Tab-System
│   ├── output.py               # Output/Debug Panel
│   ├── highlighter.py          # Universal Highlighter
│   └── completer.py            # Auto-Completion
├── languages/
│   ├── __init__.py
│   ├── base.py                 # LanguageProvider ABC
│   ├── python_lang.py
│   ├── javascript_lang.py
│   ├── typescript_lang.py
│   ├── cpp_lang.py
│   ├── rust_lang.py
│   ├── go_lang.py
│   └── java_lang.py
├── features/
│   ├── __init__.py
│   ├── linter.py               # Linter-Integration
│   ├── debugger.py             # Debug-Integration
│   ├── git.py                  # Git-Integration
│   └── ide_bridge.py           # VS Code/PyCharm Bridge
├── ui/
│   ├── __init__.py
│   ├── main_window.py          # Hauptfenster
│   ├── dialogs.py              # Settings, Goto, etc.
│   ├── minimap.py              # Minimap Widget
│   └── folding.py              # Code Folding
├── resources/
│   ├── themes/
│   │   ├── dark.qss
│   │   ├── light.qss
│   │   └── monokai.qss
│   └── icons/
└── config/
    ├── settings.json           # Benutzereinstellungen
    └── keybindings.json        # Tastenkürzel
```

---

## 🚀 Implementierungsplan

### Phase 1: Core Refactoring (2-3 Tage)
- [ ] LanguageProvider ABC erstellen
- [ ] PythonProvider aus PythonBox extrahieren
- [ ] UniversalHighlighter implementieren
- [ ] Datei-Extension → Provider Mapping

### Phase 2: Weitere Sprachen (1-2 Tage pro Sprache)
- [ ] JavaScriptProvider
- [ ] TypeScriptProvider  
- [ ] CppProvider
- [ ] RustProvider

### Phase 3: Features anpassen (2-3 Tage)
- [ ] Linter-System generalisieren
- [ ] Debug-System generalisieren
- [ ] Snippets pro Sprache
- [ ] Projekt-System (multi-file)

### Phase 4: Polish (1-2 Tage)
- [ ] Sprach-Auswahl in Statusbar
- [ ] Automatische Spracherkennung
- [ ] Theme-System erweitern
- [ ] Dokumentation

---

## 🎨 UI-Anpassungen

### Statusbar mit Sprachauswahl

```
┌─────────────────────────────────────────────────────────────────┐
│ Zeile 42, Spalte 15 │ UTF-8 │ LF │ [Python ▼] │ Git: ● Modified │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                      Klick öffnet Dropdown
```

### Neue Toolbar-Elemente

```
[📄 Neu] [📂 Öffnen] [💾 Speichern] │ [↩️ Undo] [↪️ Redo] │ 
[🔍 Suchen] │ [▶️ Run] [🐛 Debug] │ [🐍 Python ▼]
                                          ↑
                                  Sprach-Schnellwahl
```

---

## 💡 Erweiterungsideen (Future)

| Feature | Beschreibung | Priorität |
|---------|--------------|-----------|
| **LSP Support** | Language Server Protocol Integration | Hoch |
| **Plugin System** | Sprachen als Plugins laden | Mittel |
| **Terminal** | Integriertes Terminal | Mittel |
| **Project View** | Dateibaum-Explorer | Mittel |
| **Remote Editing** | SSH/SFTP Dateien | Niedrig |
| **Collaborative** | Shared Editing | Niedrig |

---

## 📊 Vergleich: PythonBox vs CodeBox

| Aspekt | PythonBox v8 | CodeBox |
|--------|--------------|---------|
| Sprachen | 1 (Python) | 6+ |
| Architektur | Monolithisch | Modular |
| Zeilen Code | ~3,400 | ~4,500 (geschätzt) |
| Erweiterbarkeit | Schwer | Einfach |
| Lernkurve | Flach | Flach |
| Performance | Schnell | Schnell |

---

## ✅ Fazit

CodeBox baut auf dem soliden Fundament von PythonBox auf und macht es durch
eine saubere Abstraktion möglich, beliebige Programmiersprachen zu unterstützen.
Der Hauptaufwand liegt im Refactoring der bestehenden Codebasis und dem
Erstellen der sprachspezifischen Provider.

**Geschätzter Gesamtaufwand: 10-14 Tage**

---

*Konzept erstellt: Januar 2026*
*Basierend auf: PythonBox v8 (3,381 Zeilen)*
