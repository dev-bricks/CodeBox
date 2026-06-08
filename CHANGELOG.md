# Changelog

Alle wesentlichen Änderungen an CodeBox werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Dokumentation
- `llms.txt` im Root-Verzeichnis hinzugefügt, um Entdeckung und Indexierung durch KI-Crawler zu verbessern.
- `AUFGABEN.txt` und `dist/` Struktur bereinigt (redundante `CodeBox_new.exe` entfernt).

### Build / Release
- EXE aktualisiert 2026-06-01 (OneDrive-Lock aufgelöst nach Beenden alter Prozesse); enthält Startup-/CLI-Bug-Fix (`--open`-Argument + offener Bootstrap-Tab). 13/13 Tests grün, Smoke OK.
- EXE neu gebaut 2026-06-01 (PyInstaller, `CodeBox.spec` → `C:\_Local_DEV\codex_build\codebox`); 11/12 Tests grün (1 skipped), Smoke-Test bestanden. Vorherige EXE: 2026-05-28.

### Hinzugefügt
- macOS-Source-Smoke für offscreen App-Start, Dateiöffnung, Terminalpfad,
  Projektbaum-`open -R` (Finder) und lokale Python-Run-Commands.
  CI-Job `macos-smoke` in `linux-platform-smoke.yml` ergänzt.
- Linux-Source-Smoke für offscreen App-Start, Dateiöffnung, Terminalpfad,
  Projektbaum-`xdg-open` und lokale Python-Run-Commands.
- Regressionstest für Startup-Dateiübergabe per `--open` und positionalem Pfad.
- README-Discoverability für GitHub/Web-Suche geschärft: englischer SEO-Einstieg,
  CodeBox-Namenskollision erklärt, Quickstart und präzisere Suchbegriffe ergänzt.
- Headless-Smoke-Test für MainWindow-Instanziierung
- Optionale LSP-Runtime-Tests für `python-lsp-server[all]`:
  Diagnostics bei Syntaxfehlern und Completion über `pylsp`.
- `__all__`-Exports in allen Modul-`__init__.py`
- LSP-Diagnostics und LSP-Completion sind jetzt im Editor verdrahtet:
  Diagnostics laufen thread-sicher über Qt-Signale, Completion-Anfragen werden
  beim Tippen an den aktiven LSP-Client geschickt.

### Behoben
- `python main.py --open <datei>` und nackte Dateipfade öffnen jetzt die Datei
  direkt beim Start und entfernen den leeren Bootstrap-Tab.
- `QApplication` fehlte im Import von `ui/main_window.py` (wurde in Theme-Lambda verwendet)
- Diverse ungenutzte Imports entfernt (core, features, languages, ui)
- Fenstertitel liest die Version jetzt aus `version.py` statt aus einem Hardcode
- Theme-Wechsel setzt Palette und QSS gemeinsam; Light-Mode bleibt nicht mehr auf Dark-Basis hängen
- Python-LSP-Erkennung startet `pylsp` jetzt auch über `python -m pylsp`,
  wenn das Script nicht auf `PATH` liegt, das Modul aber installiert ist.
- Die Anzeige verfügbarer LSP-Server nutzt jetzt dieselbe Fallback-Prüfung wie
  der Serverstart; installierte `pylsp`-Module werden daher auch ohne `pylsp.exe`
  auf `PATH` korrekt erkannt.
- LSP-Subprocess-Pipes werden beim Stoppen geschlossen; der Runtime-Test läuft
  dadurch ohne ResourceWarnings.
- `close_tab()` bricht jetzt ab, wenn das Speichern eines modifizierten Tabs fehlschlägt,
  statt den Tab trotzdem zu schließen.
- `run_current()` startet kein Programm mehr, wenn das automatische Speichern vor dem
  Ausführen fehlschlägt.
- Tab-Reordering hält die interne Index-Map jetzt synchron; `current_tab()`,
  `close_tab()` und die offenen-Datei-Prüfungen bleiben nach Drag-and-drop korrekt.

### Geändert
- Deutschsprachige Doku sowie Python-Kommentare, Docstrings und naheliegende UI-Texte
  verwenden jetzt echte Umlaute statt `ae/oe/ue`
- Windows-Build nutzt jetzt die vorhandene PyInstaller-Spec mit lokalem
  Arbeitsverzeichnis außerhalb von OneDrive; `start.bat` startet bevorzugt
  `dist\CodeBox.exe` und fällt erst danach auf Release-EXE oder Python zurück.
- README präzisiert die lokale Privacy-Abgrenzung; `.gitignore` schützt
  zusätzliche Credential-, SSH- und SQLite-Artefakte.
- `.gitignore` deckt interne Diagnose-/Skill-Dateien, Test-Caches und lokale
  Windows-Build-Artefakte inklusive PyInstaller-Spec-Dateien ab.
- README beschreibt die optionale `paramiko`-Abhängigkeit für Remote Editing.

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
