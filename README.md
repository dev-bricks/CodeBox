# CodeBox

Multi-Language Code Editor auf Basis von PySide6. Leichtgewichtiger
Desktop-Editor mit Syntax-Highlighting, LSP-Integration, integriertem
Terminal und Projekt-Dateibaum.

Abgeleitet von PythonBox v8, ausgebaut zur Multi-Language-IDE.

## Features

- **Multi-Language Syntax-Highlighting** fuer 7 Sprachen: Python, JavaScript,
  TypeScript, C++, Rust, Go, Java
- **LSP-Client** fuer Autovervollstaendigung, Diagnostics und Hover-Info
- **Integriertes Terminal** mit Shell-Auswahl (cmd, PowerShell, bash, zsh)
  und Befehls-History
- **Projekt-Dateibaum** mit Filter, Kontextmenue und Versteckte-Dateien-Support
- **Tab-System** fuer mehrere Dateien gleichzeitig
- **Ausfuehrungs-Panel** pro Sprache (Run/Stop, Output)
- **Such- und Gehe-zu-Zeile** mit Tastenkuerzeln
- **Theme-System** (Dark-Default, weitere per Theme-Menue)
- **Git-Integration** (Basis: Status, Branch, Diff)
- **REST-API/CLI-Steuerbarkeit** (via ATI-Template)

## Installation

```bash
pip install -r requirements.txt
python main.py
```

### Voraussetzungen

- Python 3.10+
- PySide6 >= 6.5.0

### Optionale LSP-Server

- Python: `pip install python-lsp-server`
- TypeScript: `npm install -g typescript-language-server`
- Rust: `rustup component add rust-analyzer`
- Go: `go install golang.org/x/tools/gopls@latest`
- C++: `apt install clangd` / `choco install llvm`

## Projektstruktur

```
main.py            # Einstiegspunkt (QApplication + Dark-Theme)
core/              # Editor, Tabs, Output, Highlighter
features/          # LSP-Client, Terminal, Project-View, Git, Themes, Remote
languages/         # Language Provider (Keywords, Snippets, LSP-Config)
ui/                # MainWindow mit Menues, Toolbar, Splittern
config/            # Konfigurationsdateien
themes/            # Theme-Definitionen
```

## Status

**In aktiver Entwicklung (v0.1.0).**

Funktionsfaehig: Multi-Language-Editor, 7 Language-Provider, LSP-Manager,
Terminal und Project-View sind in das MainWindow integriert (linker Sidebar-
Splitter + unteres Tab-Panel mit Ausgabe/Terminal). Tastenkuerzel:
`Ctrl+B` (Projektbaum), `` Ctrl+` `` (Terminal).

Noch offen fuer v1.0:
- LSP-Diagnostics und -Completion direkt im Editor anzeigen
- Automatischer Linter-Aufruf beim Speichern + Problems-Panel
- Theme-Auswahl-Dialog (aktuell nur ueber Menue)
- Plugin-System fuer weitere Sprachen
- Remote Editing (SSH/SFTP)

## Lizenz

MIT License -- siehe [LICENSE](./LICENSE).
