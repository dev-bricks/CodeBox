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

---

## Haftung / Liability

Dieses Projekt ist eine **unentgeltliche Open-Source-Schenkung** im Sinne der §§ 516 ff. BGB. Die Haftung des Urhebers ist gemäß **§ 521 BGB** auf **Vorsatz und grobe Fahrlässigkeit** beschränkt. Ergänzend gelten die Haftungsausschlüsse aus GPL-3.0 / MIT / Apache-2.0 §§ 15–16 (je nach gewählter Lizenz).

Nutzung auf eigenes Risiko. Keine Wartungszusage, keine Verfügbarkeitsgarantie, keine Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.

This project is an unpaid open-source donation. Liability is limited to intent and gross negligence (§ 521 German Civil Code). Use at your own risk. No warranty, no maintenance guarantee, no fitness-for-purpose assumed.

