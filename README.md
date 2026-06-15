<img src="assets/banner.svg" width="100%" alt="CodeBox Banner">

# CodeBox — local PySide6 desktop code editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()
[![LSP Ready](https://img.shields.io/badge/LSP-ready-purple.svg)]()

> Local-first desktop IDE for Windows — lightweight PySide6 code editor with tabs, project tree, integrated terminal, Git helpers, syntax highlighting and LSP diagnostics.


lightweight PySide6 code editor with tabs, a project tree, an integrated
terminal, Git helpers, syntax highlighting and Language Server Protocol
diagnostics.

Mehrsprachiger Desktop-Codeeditor auf Basis von PySide6. CodeBox ist aus
PythonBox v8 hervorgegangen und bündelt Editor, Projektbaum, Terminal sowie
erste LSP- und API-Grundlagen in einer lokalen IDE.

## Why CodeBox

- Local-first: edit files on your machine without cloud accounts or telemetry.
- PySide6 desktop stack: native Windows app behavior with a small Python codebase.
- Multi-language workflow: Python, JavaScript, TypeScript, C++, Rust, Go and Java.
- LSP-ready: diagnostics and completion can connect to installed language servers.
- Dev-bricks ecosystem: companion to PythonBox and DevCenter for small local tools.

## Screenshot

![CodeBox Screenshot](README/screenshots/main.png)

## Funktionen / Features

- Syntax-Highlighting für Python, JavaScript, TypeScript, C++, Rust, Go und Java
- Integriertes Terminal mit Shell-Auswahl und History
- Projekt-Dateibaum mit Filter und Kontextmenü
- Mehrere Tabs, Suchfunktion und Gehe-zu-Zeile
- Robuste Tab-Verwaltung mit Drag-and-drop-Reordering und Save-Failure-Guards
- Theme-System über `features/theme_manager.py`
- REST-API-/CLI-Grundlage für spätere Fernsteuerung
- LSP-Diagnostics und Completion-Anbindung für installierte Language Server

## Installation

```bash
pip install -r requirements.txt
python main.py
python main.py --open path/to/file.py
```

Alternativ per Doppelklick auf `start.bat`.

### Quick start

1. Clone `https://github.com/dev-bricks/CodeBox`.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run `python main.py`.
4. Optional: install language servers such as `python-lsp-server[all]` or
   `typescript-language-server` for diagnostics and completion.
5. Open a file directly with `python main.py --open path/to/file.py`.

### Voraussetzungen / Requirements

- Python 3.10+
- PySide6 >= 6.5.0

### Optionale LSP-Server

- Python: `pip install "python-lsp-server[all]"` für Completion plus Diagnostics
  (`pip install python-lsp-server` reicht nur für Completion)
- TypeScript: `npm install -g typescript-language-server`
- Rust: `rustup component add rust-analyzer`
- Go: `go install golang.org/x/tools/gopls@latest`
- C++: `clangd` bzw. LLVM

Der Python-LSP wird bevorzugt über `pylsp` auf `PATH` gestartet. Falls das
Script nach der Installation nicht auf `PATH` liegt, nutzt CodeBox den aktuellen
Python-Interpreter als Fallback: `python -m pylsp`.
Die Verfügbarkeitsprüfung in der Oberfläche nutzt dieselbe Fallback-Logik, sodass
installierte `pylsp`-Module auch ohne separates `pylsp.exe` korrekt erkannt werden.

### Optionale Remote-Editing-Abhängigkeit

Die vorbereitete SSH/SFTP-Schicht nutzt `paramiko`, ist aber nicht für den lokalen
Editorstart erforderlich:

```bash
pip install paramiko
```

## Lokaler Windows-Build

```bat
build_exe.bat
```

Das Script nutzt PyInstaller und erstellt lokal eine `CodeBox.exe` mit
`CodeBox.ico`. Die versionierte `CodeBox.spec` bündelt Icon und Theme-Dateien,
während temporäre Build-Daten unter `C:\_Local_DEV\codex_build\codebox` liegen.
Build-Ausgaben in `build/`, `dist/` und `releases/` bleiben lokale Artefakte
und werden nicht versioniert.

`start.bat` startet bevorzugt `dist\CodeBox.exe`, nutzt danach eine vorhandene
Release-EXE und fällt erst zuletzt auf `python main.py` zurück.

## Projektstruktur

```text
main.py            Einstiegspunkt / application entry
core/              Editor-Kern, Tabs, Output, Highlighter
features/          Terminal, Projektbaum, LSP, Git, Themes, Remote
languages/         Sprachprofile und LSP-Konfiguration
ui/                MainWindow und UI-Komposition
config/            Konfigurationsdateien
themes/            QSS-Themes
```

## Discovery keywords

CodeBox is best described as a local PySide6 code editor, Windows desktop IDE,
offline code editor, LSP-enabled Python editor and lightweight multi-language
developer tool. The repository name collides with older projects called
`codebox`, so searches are most precise with `dev-bricks CodeBox`,
`CodeBox PySide6`, `CodeBox LSP editor` or `file-bricks/dev-bricks desktop IDE`.

## Status

Aktueller Stand: `DEV`, Version `0.1.0`

Bereits stabil nutzbar:

- Mehrsprachiger Editor
- Projektbaum und Terminal im MainWindow
- Konsistente Fenstertitel über `version.py`
- Light-/Dark-Theme-Wechsel über den zentralen Theme-Manager
- Speichern-, Schließen- und Ausführen-Flows behalten Tabs offen, wenn ein
  Dateisystemfehler das Speichern verhindert.

Noch offen für die nächste größere Ausbaustufe:

- Runtime-Test mit installiertem LSP-Server
- Linter-/Problems-Panel
- Plugin-System für weitere Sprachen
- Remote Editing (SSH/SFTP)

## Datenschutz / Privacy

CodeBox arbeitet lokal auf Dateien, die der Nutzer öffnet. Es werden keine
Zugangsdaten für den Editor-Grundbetrieb benötigt und keine externen Dienste
kontaktiert, außer Sie starten selbst einen installierten Language Server,
externe Build-/Run-Tools oder optionale Remote-Editing-Funktionen.

Optionale Remote-Verbindungen können zur Laufzeit SSH-Passwörter oder
Schlüsselpfade verwenden. Solche Daten gehören nicht ins Repository und sollten
nur in lokalen, ignorierten Konfigurationsdateien oder im System-Keyring liegen.

Lokale Arbeitsdateien wie `AUFGABEN.txt`, Test-Locks, `.env`-Dateien,
Credentials, SSH-Schlüssel, Logs, Datenbanken und Build-Artefakte sind über `.gitignore`
ausgeschlossen.

## Lizenz / License

[MIT License](LICENSE)

## Haftung / Liability

Dieses Projekt ist eine unentgeltliche Open-Source-Schenkung im Sinne der
§§ 516 ff. BGB. Die Haftung des Urhebers ist gemäß § 521 BGB auf Vorsatz und
grobe Fahrlässigkeit beschränkt. Ergänzend gilt der Haftungsausschluss der
MIT-Lizenz.

Nutzung auf eigenes Risiko. Keine Wartungszusage, keine Verfügbarkeitsgarantie,
keine Gewähr für Fehlerfreiheit oder Eignung für einen bestimmten Zweck.

This project is an unpaid open-source donation. Liability is limited to intent
and gross negligence (§ 521 German Civil Code). Use at your own risk. No
warranty, maintenance guarantee, or fitness-for-purpose is assumed.
