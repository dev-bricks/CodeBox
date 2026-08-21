# Changelog

## 2026-07-27

### Changed
- Documented the actual local CLI contract in `API_STATUS.md` and corrected
  outdated REST/OpenAPI claims in both READMEs. CodeBox currently supports
  startup-file handoff only; no REST, OpenAPI, token, or remote-control
  surface exists.

Alle wesentlichen Änderungen an CodeBox werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [0.1.2] - 2026-08-16

### UX, Barrierefreiheit & Accessibility-Härtung (2026-08-21)

- `ui/main_window.py`: StatusTips auf allen Menü- und Toolbar-Aktionen (`Neu`, `Öffnen`, `Speichern`, `Beenden`, `Rückgängig`, `Wiederherstellen`, `Suchen`, `Gehe zu Zeile`, `Plugins`, `Einstellungen`, `Ausführen`, `Stoppen`, `Projektbaum`, `Terminal`, `Tastenkürzel`, `Über`); `setToolTip()`, `setWhatsThis()`, `setAccessibleName()` und `setAccessibleDescription()` für Hauptleiste, Sprach-Auswahl (`lang_combo`), Statusleisten-Widgets (`pos_label`, `lang_label`, `enc_label`) und Reiter im unteren Bedienpanel (`bottom_tabs`).
- `core/tabs.py`: `TabWidget` mit `accessibleName` / `accessibleDescription` versehen und dynamische Tab-Tooltips mit absolutem Dateipfad beim Öffnen, Neuanlegen, Speichern und Drag-and-Drop-Umsortieren implementiert.
- `ui/settings_dialog.py`: Tooltips und `accessibleName` / `accessibleDescription` für alle Einstellungsfelder (`font_combo`, `font_size_spin`, `tab_size_spin`, `theme_combo`, `auto_save_cb`, `minimap_cb`) integriert.
- `ui/shortcuts_dialog.py` & `ui/plugins_dialog.py`: Barrierefreie Beschriftungen, Tooltips und Beschreibungen für Filter-Eingabefelder, Tabellen, Detailboxen und Aktions-Buttons ergänzt.
- `tests/test_ui_ux_accessibility.py`: Neue automatisierte UX- und Accessibility-Vertragstestsuite mit 6 Tests für Toolbar, Tabs, Statusbar, Einstellungen, Shortcuts, Plugins und Panels (109 passed, 1 skipped).

- `core/highlighter.py`: Regex-Mustererstellung in `UniversalHighlighter` (`_keyword_pattern`) gehärtet, sodass Keywords und Builtins mit Satzzeichen/Metazeichen (z.B. Rubys `defined?` oder C++-Symbole) mit `re.escape()` maskiert und mit sicheren Wortgrenzen gematcht werden. Verhindert Fehl-Highlighting von Variablennamen (`define`) und unvollständiges Keyword-Highlighting.
- `languages/declarative.py`: Parsing von `comment_style` in `DeclarativeLanguageProvider.from_dict` erweitert, sodass Einzelstring- (`#`), 1-Element-Listen (`["--"]`), 3-Element-Flachlisten (`["--", "--[[", "--]]"]`) und Dictionary-Formate deterministisch ausgewertet werden.
- `features/plugin_manager.py`: `discover_and_load_all()` bereinigt gelöschte Plugin-Dateien beim Re-Scan; `_load_python_plugin()` registriert Provider aus `PluginInfo`-Rückgaben von `setup()` ab.
- `languages/__init__.py`: Null- und Whitespace-Sicherheit für `get_provider_for_extension`, `get_provider_by_name` und `is_provider_registered`.
- `ui/plugins_dialog.py`: Abbruch-Verhalten bei Vorlagenerstellung korrigiert; Detailanzeige gegen leere Provider-Felder abgesichert.
- `tests/test_plugin_system.py`: 4 neue Testsuiten für Keyword-Escaping, Kommentarstil-Variationen, Provider-Lookups und Plugin-Dateibereinigung (103 passed, 1 skipped).

### Technische Hygiene, Metadaten & Discoverability (2026-08-16)

- `tests/test_metadata.py`: Automatisierte Metadaten-, Manifest- und Plugin-Integritätstestsuite ergänzt (Version-Parität `pyproject.toml`, `version.py`, `CHANGELOG.md`, Required-Fields, Core-Docs, Plugin-JSON-Validierung).
- `version.py`: Version und `__version__` auf `0.1.2` synchronisiert.
- `pyproject.toml`: Version auf `0.1.2` aktualisiert.
- `README.md` & `README_de.md`: Shields.io Badges um `dev-bricks` Ecosystem- und `open-bricks` Umbrella-Zugehörigkeit sowie aktualisierten Teststatus (99 passed, 1 skipped) erweitert.
- `llms.txt`: Last-checked Zeitstempel auf `2026-08-16` und Teststand synchronisiert.

### Plugin-System, Deklarative Sprachen & Shortcuts-Dialog (2026-08-14)

- `features/plugin_manager.py`: Neuer Plugin-Manager für automatische Entdeckung und Verwaltung von benutzerdefinierten und projektweiten Sprach-Plugins (`plugins/`, `~/.codebox/plugins/`).
- `languages/declarative.py`: `DeclarativeLanguageProvider` ermöglicht das Definieren vollständiger Sprachunterstützung (Keywords, Builtins, Snippets, Run-/Debug-Commands, Comment-Styles, Auto-Close-Paare und Indent-Trigger) über schlanke JSON-Dateien ohne Python-Code.
- `languages/__init__.py`: Dynamische Provider-Registrierung (`register_provider`, `unregister_provider`, `reset_providers`) mit Listener-Pattern (`add_provider_listener`, `remove_provider_listener`) für reaktive Toolbar- und Editor-Aktualisierung.
- `ui/plugins_dialog.py`: Neuer interaktiver Plugin- & Sprachverwaltungs-Dialog (`Ctrl+Shift+P` / Menü *Bearbeiten* & *Hilfe*) mit Tabellenansicht, Detailinspektion, Template-Generator und Schnellumschaltung.
- `ui/shortcuts_dialog.py`: Neuer interaktiver Shortcuts-Dialog (`F1` / Menü *Hilfe*) mit Such- und Filterleiste über alle Tastenkombinationen.
- `plugins/lua_plugin.json` & `plugins/ruby_plugin.json`: Beispielhafte deklarative Sprach-Plugins für Lua und Ruby integriert.
- `tests/test_plugin_system.py`: Umfassende Testsuite mit 8 neuen Unit-Tests für Provider-Registrierung, Declarative-Parsing, Plugin-Manager-Laden/Entladen, Dialog-UI und Window-Events.
- Testsuite auf 99 bestandene Tests ausgebaut (100% grün).

### LSP, Linter und Problems-Panel (2026-08-11)

- `tests/test_lsp_runtime.py` verifiziert die optionale Python-LSP-Integration
  mit Diagnostics, Completion und Hover gegen `python-lsp-server[all]`.
- `features/linter.py` erkennt optionale Ruff-/flake8-/ESLint-Installationen,
  normalisiert deren Befunde und führt sie nach dem Speichern außerhalb des
  UI-Threads aus.
- `ui/problems_panel.py` zeigt LSP- und Linter-Befunde gemeinsam an und springt
  per Doppelklick zur betroffenen Datei-/Zeilenposition.

### Build-Verifikation (2026-07-28)

- TASKPLAN-Bündel `deep/easy`, Task #1288: `build_exe.bat` mit
  PyInstaller 6.21.0 erfolgreich ausgeführt (Exit 0). Die erzeugte
  `C:\_Local_DEV\codex_build\codebox\dist\CodeBox.exe` besitzt einen gültigen
  `MZ`-Header, enthält Icon sowie Dark-/Light-Theme und blieb im
  12-Sekunden-Start-Smoke responsiv. Verifikation: 80 Tests bestanden,
  1 optionaler LSP-Runtime-Test ohne Opt-in übersprungen; keine Blocker.

## [0.1.1] - 2026-07-27

### Marketing & Discoverability (2026-07-27)

- `pyproject.toml`: Version auf `0.1.1` angehoben.
- `llms.txt`: Last-checked Datum auf `2026-07-27` aktualisiert und 78/78 bestandene Pytest-Tests verifiziert.
- `README.md` & `README_de.md`: Badges, GFM-Alerts (`> [!NOTE]`), Mermaid-Architektur und Suchbegriffe abgeglichen.
- `MARKETING-LOG.txt`: Empfehlungen für visuellen Screencast / Demo-GIF und GitHub Releases Staging ergänzt.

### Wartung & Hygiene (2026-07-27)

- `llms.txt`: Timestamp auf 2026-07-27 aktualisiert und Teststatus (78 bestanden, 1 übersprungen) verifiziert.
- `AUFGABEN.txt`: TW-CB-01 (Status- und Dokumentationsquellen synchronisieren) als erledigt dokumentiert.
- `CHECKED-REGISTRY.md` & `CHECKS-LOG.txt`: Projektwartung und Testsuite-Bestätigung eingetragen.

### Marketing & Discoverability (2026-07-26)

- `README.md` & `README_de.md`: Mermaid Systemarchitektur- & Komponenten-Diagramm in Englisch und Deutsch integriert.
- `llms.txt`: Header Timestamp auf 2026-07-26 und Search Phrases erweitert.


### Wartung & Hygiene (2026-07-25)

- `pyproject.toml` mit PEP 621 Metadaten, Pytest-Konfiguration (`pythonpath = "."`) und optionalen Abhängigkeiten (`lsp`, `remote`, `test`) angelegt.
- `llms.txt` Last-checked Timestamp auf 2026-07-25 aktualisiert.
- `README.md` & `README_de.md` um KI-/LLM-Integrationshinweis (`> [!NOTE]`) und erweiterte Badges ergänzt.

### Hinzugefügt

- `features/project_view.py`: Git-Status-Indikatoren (M / S / SM / U / D / R) werden
  jetzt rechts neben dem Dateinamen im Projektbaum angezeigt. Neue Hilfsfunktion
  `status_for_path()` (Qt-frei, direkt testbar) sucht per `Path.as_posix()`-Normalisierung
  auch auf Windows mit Backslash-Pfaden korrekt im Porcelain-Status-Dict. Neuer
  `GitStatusDelegate` (`QStyledItemDelegate`) zeichnet farbige Badges; `_load_git_status()`
  befüllt den Cache bei `set_root()` und `_refresh()`. 10 neue Regressionstests in
  `tests/test_git_project_view_status.py`.

### Behoben

- `core/editor.py`: Behoben: (1) Bracket-Matching am Dokumentende (EOF) filterte Cursortyp bei `pos == len(text)` aus, wodurch schließende Klammern am Dateiende nicht hervorgehoben wurden. (2) `insert_completion()` ersetzte bei case-insensitiver Auto-Completion oder Wort-Ersetzung bisher nur Suffix-Texte statt das Präfix-Wort exakt zu ersetzen. 2 neue Regressionstests in `tests/test_editor_auto_close.py`.
- `features/git_integration.py`: `GitRepo.get_status()` entpackt jetzt von Git zitiere Pfade (z. B. bei Dateinamen mit Leerzeichen oder Sonderzeichen) und umbenannte Pfade (`"old.py" -> "new.py"`) via `parse_porcelain_path()`. Zudem werden C-Style Escape-Sequenzen unescaped und `errors="replace"` bei Subprocess-Output genutzt. Git-Status-Badges in `ProjectView` funktionieren dadurch auch bei Pfaden mit Leerzeichen oder Sonderzeichen. 3 neue Regressionstests in `tests/test_git_status_parsing.py`.
- `features/remote_editor.py`: SSH/SFTP-Verbindungen laden bekannte Hostkeys und
  lehnen unbekannte Hostkeys jetzt ab, statt sie automatisch zu akzeptieren.
- `features/terminal.py` (B-012): `_start_shell()` trennte die Signale
  (`readyReadStandardOutput`, `readyReadStandardError`, `finished`) des alten
  `QProcess`-Objekts nicht, bevor es durch ein neues ersetzt wurde. Beim
  Shell-Neustart konnte der alte Prozess nach `kill()` noch `_on_finished` oder
  `_on_stdout` auslösen und so einen spuriösen „Shell beendet"-Eintrag in den
  neuen Terminal-Output schreiben. Fix: Signale werden jetzt analog zu B-004
  (`core/output.py`) getrennt; `kill()` wird nur noch bei `state() != NotRunning`
  aufgerufen. 3 Regressionstests in `tests/test_terminal_encoding.py` ergänzt.
- `features/project_view.py`: Die kompakte Sidebar im Projektbaum verlässt sich
  für Filterfeld und Dateibaum nicht mehr nur auf Placeholder und Position.
  `Ordner...`, `Aktualisieren`, das Filterfeld und der Dateibaum exponieren
  jetzt sprechende Accessible Names, Descriptions und Tooltips; Regressionstest
  in `tests/test_project_view.py` ergänzt.
- `ui/main_window.py` (B-011): ProjectView blieb beim Öffnen einer Datei aus
  einem anderen Ordner auf dem ersten Root hängen. Der Projektbaum folgt jetzt
  auch bei späteren Dateiwechseln dem aktuellen Dateiverzeichnis; neuer
  Regressionstest in `tests/test_project_view.py`.
- `features/lsp_client.py` (B-009): Zweites `process.wait()` nach `kill()` in `try/except` eingebettet — `subprocess.TimeoutExpired` wurde bisher nicht gefangen, sodass `_reader_thread.join()` übersprungen werden konnte. Streams werden jetzt im `finally`-Block zuverlässig geschlossen.
- `core/editor.py` (B-010): Auto-Close wrappte bei aktiver Textmarkierung nicht mehr die Auswahl, sondern verwarf sie. Jetzt wird `selectedText()` mit dem Bracket-/Quote-Paar umschlossen; `U+2029`-Absatztrenner werden vor dem Einfügen zu `\n` normalisiert. 3 Regressionstests hinzugefügt.
- `ui/main_window.py` (B-008): `closeEvent` verwendete veraltete `QMessageBox.Yes/No`-Kurznamen statt `QMessageBox.StandardButton.Yes/No` (PySide6-6.x-Deprecation-Hygiene).

### CI

- `welcome.yml` hinzugefügt: Begrüßungsnachricht bei erstem Issue oder Pull Request.
- `stale.yml` hinzugefügt: Issues und PRs werden nach 30 Tagen als stale markiert und nach 37 Tagen automatisch geschlossen.

### Dokumentation
- `THIRD_PARTY_LICENSES.txt` ergänzt die direkte Runtime-Lizenzinventur für
  `PySide6` und das transitive Qt-for-Python-Wheel-Set; ein Guard-Test schützt
  das Inventar gegen Dependency-Drift.
- `README.md` als klaren englischen Einstieg mit Start-Here-Tabelle,
  Screenshot-Alt-Text und Suchabgrenzung neu strukturiert; `README_de.md` als
  deutsche Einstiegsseite ergänzt. `llms.txt` auf den Marketing-Check vom
  2026-06-25 mit zusätzlichen Suchphrasen und externen Discovery-Notizen
  aktualisiert.
- `.gitignore` schützt interne Lock- und Aufgabenvarianten (`LOCK*.txt`,
  `AUFGABEN.md`, `TODO.txt`, `DONE.txt`, `ERLEDIGT.txt`) vor versehentlichem
  Tracking.
- `llms.txt` im Root-Verzeichnis hinzugefügt, um Entdeckung und Indexierung durch KI-Crawler zu verbessern.
- `AUFGABEN.txt` und `dist/` Struktur bereinigt (redundante `CodeBox_new.exe` entfernt).

### Build / Release
- `build_exe.bat`: `DIST_DIR` zeigt jetzt auf `C:\_Local_DEV\codex_build\codebox\dist` statt auf `%CD%\dist` (OneDrive). Verhindert, dass OneDrive-Sync die EXE beim Rebuild sperrt; konsistent mit dem bereits lokalen `WORK_DIR`. (DEV-Loop Run 46, 2026-06-16)
- `start.bat`: Unterstützt `CODEBOX_LOCAL_DIST`-Umgebungsvariable als erstes EXE-Suchziel vor dem relativen `dist\`-Pfad. Ermöglicht lokales Build-Verzeichnis ohne Hardcode im Skript. (DEV-Loop Run 46, 2026-06-16)
- Nach dem Build: `set CODEBOX_LOCAL_DIST=C:\_Local_DEV\codex_build\codebox\dist` in der Shell setzen (oder dauerhaft in den Systemvariablen), damit `start.bat` die lokal gebaute EXE findet. `build_exe.bat` gibt diesen Hinweis jetzt automatisch nach erfolgreichem Build aus.
- EXE aktualisiert 2026-06-01 (OneDrive-Lock aufgelöst nach Beenden alter Prozesse); enthält Startup-/CLI-Bug-Fix (`--open`-Argument + offener Bootstrap-Tab). 13/13 Tests grün, Smoke OK.
- EXE neu gebaut 2026-06-01 (PyInstaller, `CodeBox.spec` → lokales Build-Verzeichnis); 11/12 Tests grün (1 skipped), Smoke-Test bestanden. Vorherige EXE: 2026-05-28.

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
