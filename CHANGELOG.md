# Changelog

Alle wesentlichen Aenderungen an CodeBox werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefuegt
- Headless-Smoke-Test fuer MainWindow-Instanziierung
- `__all__`-Exports in allen Modul-`__init__.py`

### Behoben
- `QApplication` fehlte im Import von `ui/main_window.py` (wurde in Theme-Lambda verwendet)
- Diverse ungenutzte Imports entfernt (core, features, languages, ui)

## [0.1.0] - 2026-04-08

### Hinzugefuegt
- **REST-API und CLI-Steuerbarkeit** (2026-04-04): ATI-Template fuer
  Fernsteuerung durch Claude/LLM-Agenten. CLI: `codebox --open <file>`,
  `--run`, `--close`, `--list-tabs`, `--get-content`.
- **Theme-Manager** (`features/theme_manager.py`) mit Theme-Menue
- **Remote-Editor-Basis** (`features/remote_editor.py`)
- **Git-Integration** (`features/git_integration.py`): Status, Branch,
  Diff ueber subprocess zum git-CLI
- **Tastenkuerzel** fuer Ansicht: `Ctrl+B` (Projektbaum), `` Ctrl+` `` (Terminal)
- **CWD-Sync**: Terminal und ProjectView folgen der aktuell geoeffneten Datei
- **CloseEvent**: raeumt Terminal-Prozesse beim Beenden auf

### Geaendert
- **Migration PyQt5 -> PySide6** (2026-03-15): 8 Dateien, `QRegExp` ->
  `QRegularExpression`, `QAction` -> `QtGui`, scoped Enums fuer
  `QPalette`/`QProcess`/`QTextCursor`. Policy-Konform (LGPL).
- **Terminal und Project-View im MainWindow integriert** (2026-03-08):
  Terminal als Tab im unteren Panel (neben Ausgabe), Project-View als
  linke Sidebar mit horizontalem Splitter.

### Behoben
- **LSP-Client Race Conditions** (2026-03-14): `threading.Lock()` fuer
  `_request_id` und `_pending`-Dict-Zugriffe
- **Terminal `setTextColor()` fehlerhaft**: Farbe ging an Dokument statt
  Cursor-Format. Fix: `QTextCharFormat` + `cursor.setCharFormat()`
- **LSP-Subprocess** wurde bei `read_loop`-Abbruch nicht beendet:
  `self.stop()` nach `break` in `_read_loop`
- **`closeEvent` pruefte nur ersten unsaved Tab**: Sammelt jetzt alle
  ungespeicherten Tabs und zeigt vollstaendige Liste
- **Explorer-Pfad mit Leerzeichen/&**: `f"/select,{path}"` als ein Argument
- **`QCompleter.insert_completion` Edge Case**: Guard `if extra <= 0: return`

## [0.0.1] - 2026-02-12

### Hinzugefuegt
- **Core-Refactoring** aus PythonBox v8 extrahiert:
  `core/editor.py`, `core/tabs.py`, `core/output.py`, `core/highlighter.py`
- **UI-Schicht**: `ui/main_window.py` mit Menue, Toolbar, Statusbar,
  Suchen und Gehe-zu-Zeile
- **LanguageProvider ABC** (`languages/base.py`) mit abstrakten Methoden
  fuer Keywords, Builtins, Snippets, Run-Commands
- **7 Language-Provider**: Python, JavaScript, TypeScript, C++, Rust, Go, Java
- **Auto-Discovery** fuer Extension-zu-Provider-Mapping (`languages/__init__.py`)
- **UniversalHighlighter** (provider-basiert)
- **LSP-Client** (`features/lsp_client.py`): JSON-RPC ueber stdio,
  `LSPClient` + `LSPManager`, Support fuer pylsp, typescript-language-server,
  rust-analyzer, gopls, clangd
- **Integriertes Terminal** (`features/terminal.py`) mit Shell-Auswahl,
  History und farbiger stdout/stderr-Trennung
- **Project-View** (`features/project_view.py`) mit `QFileSystemModel`,
  Filter-Proxy, Textfilter und Kontextmenue
- **Statusbar-Sprachauswahl** mit Dropdown, manueller Auswahl und
  automatischer Erkennung bei Dateieroeffnung
- **Dark-Theme** als Standard (Fusion + eigenes Stylesheet)
