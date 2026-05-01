# Changelog

Alle wesentlichen Änderungen an CodeBox werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Hinzugefügt
- Headless-Smoke-Test für MainWindow-Instanziierung
- Optionale LSP-Runtime-Tests für `python-lsp-server[all]`:
  Diagnostics bei Syntaxfehlern und Completion über `pylsp`.
- `__all__`-Exports in allen Modul-`__init__.py`
- LSP-Diagnostics und LSP-Completion sind jetzt im Editor verdrahtet:
  Diagnostics laufen thread-sicher über Qt-Signale, Completion-Anfragen werden
  beim Tippen an den aktiven LSP-Client geschickt.

### Behoben
- `QApplication` fehlte im Import von `ui/main_window.py` (wurde in Theme-Lambda verwendet)
- Diverse ungenutzte Imports entfernt (core, features, languages, ui)
- Fenstertitel liest die Version jetzt aus `version.py` statt aus einem Hardcode
- Theme-Wechsel setzt Palette und QSS gemeinsam; Light-Mode bleibt nicht mehr auf Dark-Basis hängen
- Python-LSP-Erkennung startet `pylsp` jetzt auch über `python -m pylsp`,
  wenn das Script nicht auf `PATH` liegt, das Modul aber installiert ist.
- LSP-Subprocess-Pipes werden beim Stoppen geschlossen; der Runtime-Test läuft
  dadurch ohne ResourceWarnings.

### Geändert
- Deutschsprachige Doku sowie Python-Kommentare, Docstrings und naheliegende UI-Texte
  verwenden jetzt echte Umlaute statt `ae/oe/ue`

## [0.1.0] - 2026-04-08

### Hinzugefügt
- **REST-API und CLI-Steuerbarkeit** (2026-04-04): ATI-Template für
  Fernsteuerung durch Claude/LLM-Agenten. CLI: `codebox --open <file>`,
  `--run`, `--close`, `--list-tabs`, `--get-content`.
- **Theme-Manager** (`features/theme_manager.py`) mit Theme-Menü
- **Remote-Editor-Basis** (`features/remote_editor.py`)
- **Git-Integration** (`features/git_integration.py`): Status, Branch,
  Diff über subprocess zum git-CLI
- **Tastenkürzel** für Ansicht: `Ctrl+B` (Projektbaum), `` Ctrl+` `` (Terminal)
- **CWD-Sync**: Terminal und ProjectView folgen der aktuell geöffneten Datei
- **CloseEvent**: räumt Terminal-Prozesse beim Beenden auf

### Geändert
- **Migration PyQt5 -> PySide6** (2026-03-15): 8 Dateien, `QRegExp` ->
  `QRegularExpression`, `QAction` -> `QtGui`, scoped Enums für
  `QPalette`/`QProcess`/`QTextCursor`. Policy-Konform (LGPL).
- **Terminal und Project-View im MainWindow integriert** (2026-03-08):
  Terminal als Tab im unteren Panel (neben Ausgabe), Project-View als
  linke Sidebar mit horizontalem Splitter.

### Behoben
- **LSP-Client Race Conditions** (2026-03-14): `threading.Lock()` für
  `_request_id` und `_pending`-Dict-Zugriffe
- **Terminal `setTextColor()` fehlerhaft**: Farbe ging an Dokument statt
  Cursor-Format. Fix: `QTextCharFormat` + `cursor.setCharFormat()`
- **LSP-Subprocess** wurde bei `read_loop`-Abbruch nicht beendet:
  `self.stop()` nach `break` in `_read_loop`
- **`closeEvent` prüfte nur ersten unsaved Tab**: Sammelt jetzt alle
  ungespeicherten Tabs und zeigt vollständige Liste
- **Explorer-Pfad mit Leerzeichen/&**: `f"/select,{path}"` als ein Argument
- **`QCompleter.insert_completion` Edge Case**: Guard `if extra <= 0: return`

## [0.0.1] - 2026-02-12

### Hinzugefügt
- **Core-Refactoring** aus PythonBox v8 extrahiert:
  `core/editor.py`, `core/tabs.py`, `core/output.py`, `core/highlighter.py`
- **UI-Schicht**: `ui/main_window.py` mit Menü, Toolbar, Statusbar,
  Suchen und Gehe-zu-Zeile
- **LanguageProvider ABC** (`languages/base.py`) mit abstrakten Methoden
  für Keywords, Builtins, Snippets, Run-Commands
- **7 Language-Provider**: Python, JavaScript, TypeScript, C++, Rust, Go, Java
- **Auto-Discovery** für Extension-zu-Provider-Mapping (`languages/__init__.py`)
- **UniversalHighlighter** (provider-basiert)
- **LSP-Client** (`features/lsp_client.py`): JSON-RPC über stdio,
  `LSPClient` + `LSPManager`, Support für pylsp, typescript-language-server,
  rust-analyzer, gopls, clangd
- **Integriertes Terminal** (`features/terminal.py`) mit Shell-Auswahl,
  History und farbiger stdout/stderr-Trennung
- **Project-View** (`features/project_view.py`) mit `QFileSystemModel`,
  Filter-Proxy, Textfilter und Kontextmenü
- **Statusbar-Sprachauswahl** mit Dropdown, manueller Auswahl und
  automatischer Erkennung bei Dateieröffnung
- **Dark-Theme** als Standard (Fusion + eigenes Stylesheet)
