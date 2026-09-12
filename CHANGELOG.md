# Changelog

## 2026-07-27

### Changed
- Documented the actual local CLI contract in `API_STATUS.md` and corrected
  outdated REST/OpenAPI claims in both READMEs. CodeBox currently supports
  startup-file handoff only; no REST, OpenAPI, token, or remote-control
  surface exists.

Alle wesentlichen Änderungen an CodeBox werden hier dokumentiert.

## [0.2.0] - 2026-09-12

### Multi-Root-Workspace Support

- `core/workspace.py`: Neues Kernmodul für Multi-Root-Arbeitsbereiche:
  - Datenklasse `WorkspaceFolder` (`path`, `name`, `to_dict`, `from_dict`) mit portabler relativer Pfadberechnung.
  - `WorkspaceManager` (`QObject`) mit Signalen `foldersChanged`, `activeFolderChanged(object)`, `workspaceLoaded(str)`.
  - Methoden `add_folder`, `remove_folder`, `set_active_folder`, `set_single_folder`, `clear`, `find_folder_for_file`.
  - Datei-Format `.codebox-workspace` (JSON) mit Metadaten, Schema-Version und relativer Pfadauflösung für geräteübergreifende Portabilität (OneDrive/Multi-Device).
  - Methode `collect_all_files` zum schnellen Ordner-übergreifenden Durchsuchen mit Filterregeln.
- `features/project_view.py`:
  - Dynamischer Arbeitsbereich-Umschalter (`workspace_widget` mit `workspace_combo`, `btn_add_root`, `btn_remove_root`), der sich bei mehreren geöffneten Ordnern automatisch einblendet und bei Einzelordnern für ein aufgeräumtes Design unsichtbar bleibt.
  - Nahtloser Wechsel des aktiven Ordners und Aktualisierung von Git-Branch und Dateibaum.
  - Kontextmenü-Aktionen im Dateibaum für Verzeichnisse: "Ordner zum Arbeitsbereich hinzufügen" und "Ordner aus Arbeitsbereich entfernen".
- `ui/main_window.py`:
  - Menü *Datei* erweitert um:
    - *Ordner öffnen...* (`Ctrl+Shift+O`): Öffnet einen Ordner als einzelnen Arbeitsbereich.
    - *Ordner zum Arbeitsbereich hinzufügen...*: Fügt einen weiteren Ordner hinzu.
    - *Arbeitsbereich öffnen...*: Lädt eine `.codebox-workspace` Konfiguration.
    - *Arbeitsbereich speichern unter...*: Speichert den aktuellen Arbeitsbereich inklusive aller Ordner.
    - *Arbeitsbereich schließen*: Schließt alle Ordner des aktuellen Arbeitsbereichs.
  - Intelligente Dateizuordnung (`_on_file_changed`): Erkennt automatisch, welchem Arbeitsbereichs-Ordner eine geöffnete Datei angehört, und wechselt den aktiven Ordner, ohne andere Arbeitsbereichs-Ordner zu verwerfen.
  - Automatische Synchronisation des integrierten Terminals auf den jeweils aktiven Arbeitsbereichs-Ordner.
- `ui/command_palette.py`:
  - Quick-Open (`Ctrl+P`) durchsucht im Multi-Root-Modus alle Projektordner des Arbeitsbereichs gleichzeitig mit prägnanten Ordner-Badges (z. B. `[backend] api/routes.py`).
  - Neue Arbeitsbereichs-Aktionen stehen direkt über die Befehlspalette (`Ctrl+Shift+P`) zur Verfügung.
- `config/__init__.py`:
  - Standardeinstellung `"recent_workspaces": []` hinzugefügt.
- `ui/shortcuts_dialog.py`:
  - Shortcuts-Übersicht um die neuen Arbeitsbereichs-Aktionen und `Ctrl+Shift+O` ergänzt.
- Testsuite:
  - `tests/test_workspace.py`: 5 Unit-Tests für `WorkspaceManager` und `WorkspaceFolder`.
  - `tests/test_multi_root_workspace.py`: 4 Integrations-Tests für UI, Lifecycle, Dateizuordnung und Quick-Open Suche.
  - 248 Tests bestanden, 1 übersprungen, 100% grün.

## [0.1.9] - 2026-09-11

### Zuschaltbarer Vim-Keybindings Modus

- `core/vim_mode.py`: Neues Kernmodul mit vollständiger Vim-Zustandsmaschine (`VimEngine`, `VimMode`):
  - 4 Betriebsmodi: `NORMAL`, `INSERT`, `VISUAL` (zeichenweise Markierung) und `VISUAL_LINE` (zeilenweise Markierung).
  - Terminal-authentischer Blockcursor im Normal- und Visual-Modus via adaptiver Fontmetrik (`QFontMetrics.horizontalAdvance`).
  - Bewegungstasten: `h`, `j`, `k`, `l`, Wortsprünge `w`, `b`, `e`, Zeilenbegrenzungen `0`, `^`, `$`, Dokumentensprünge `gg`, `G`, `<N>G` sowie Halbseiten-Scrollen `Ctrl+D`, `Ctrl+U`.
  - Ziffernpuffer & Zähler-Multiplikation (`3w`, `5j`, `2dd`).
  - Umfassende Lösch- und Änderungsbefehle: `x`, `X`, `dd`, `dw`, `de`, `d$`/`D`, `d0`, `cw`, `cc`/`S`, `C`, `s`, `r<char>`.
  - Kopieren & Einfügen (Yank/Put): `yy`, `Y`, `yw`, `y$`, `p`, `P` mit nativer Unterscheidung zwischen zeilen- und zeichenbasiertem Einfügen sowie Synchronisation mit dem System-Clipboard.
  - Weitere Aktionen: Fallwechsel (`~`), Zeilen verbinden (`J`), Ein-/Ausrücken (`>>`, `<<`), Undo (`u`), Redo (`Ctrl+R`).
  - Bereichsoperationen im Visual- und Visual-Line-Modus (`d`, `x`, `y`, `c`, `>`, `<`, `~`, `u`, `U`).
- `core/editor.py`:
  - `vim_engine` Instanz in `CodeEditor`.
  - Methoden `set_vim_mode_enabled(bool)` und `is_vim_mode_enabled() -> bool`.
  - Key-Event Routing im Editor fängt Tastenanschläge bei aktivem Vim-Modus modal ab.
- `ui/main_window.py`:
  - Menü *Bearbeiten* -> *Vim-Modus* (`Ctrl+Alt+V`) mit checkbarem Zustand.
  - Statusleisten-Widget (`vim_label`) mit Anzeige von `-- NORMAL --`, `-- INSERT --`, `-- VISUAL --`, `-- VISUAL_LINE --` und aktuellem Befehlspuffer (z. B. `  [3d]`).
  - Propagierung des Vim-Zustands auf alle geöffneten Tabs beider Split-Ansichten.
  - Automatische Registrierung in der Schnellauswahl / Befehlspalette (`Ctrl+Shift+P`).
- `config/__init__.py`:
  - `"vim_mode": False` in `DEFAULT_SETTINGS` aufgenommen.
- `ui/settings_dialog.py`:
  - Checkbox zur globalen Aktivierung/Deaktivierung des Vim-Modus.
- `ui/shortcuts_dialog.py`:
  - Neue Dokumentations-Kategorie *Vim-Modus* mit vollständiger Tabelle aller Tastenbelegungen sowie Ergänzung unter *Bearbeiten*.
- `tests/test_vim_mode.py`:
  - 27 automatisierte Unit Tests für Zustände, Navigation, Operatoren, Visual Mode, Zwischenablage, Editor- und UI-Integration (Gesamt: 239 passed, 1 skipped).

## [0.1.8] - 2026-09-11

### Git-Staging & Commit-Dialog

- `features/git_integration.py`: Erweiterung der `GitRepo`-Klasse um vollständige Git-Staging-, Reset-, Verwerfen- und Commit-Funktionen:
  - `_run_git_result()` für detaillierte Subprocess-Ergebnisse mit Rückgabewert, stdout und stderr.
  - `stage_file(filepath)` und `stage_all()` (`git add`).
  - `unstage_file(filepath)` und `unstage_all()` (`git restore --staged` / `git reset HEAD`).
  - `discard_file_changes(filepath)` zum sicheren Verwerfen von Änderungen im Arbeitsbaum oder Löschen ungetrackter Dateien.
  - `commit(message)` zum Erstellen von Commits mit Validierung leerer Nachrichten und Rückgabe von Ausgaben.
- `ui/git_commit_dialog.py`: Neuer nativer Dialog `GitCommitDialog`:
  - Zweispaltige Ansicht für bereitgestellte Änderungen (Staged) und ungestagte Arbeitsbaum-Änderungen.
  - Status-Badges (`[M]`, `[A]`, `[?]`, `[D]`) mit WCAG-konformer Farbcodierung.
  - Direktaktionen: "Stagen", "Alle stagen", "Aus Staging entfernen", "Alle unstagen", "Verwerfen...", "Diff anzeigen".
  - Doppelklick-Unterstützung: Doppelklick auf ein Staged-Element hebt das Staging auf; Doppelklick auf ein Unstaged-Element stellt es bereit.
  - Großzügiges Eingabefeld für Commit-Nachrichten mit Zeichen- und Zeilenzähler sowie Shortcut `Ctrl+Enter` zur sofortigen Ausführung.
  - Vollständig barrierefrei mit `AccessibleName`, `AccessibleDescription` und Tastaturnavigation.
- `features/project_view.py`:
  - Neuer Header-Button "Commit..." (aktiviert, wenn das geöffnete Projekt ein Git-Repository ist).
  - Kontextmenü-Erweiterung um "Datei stagen", "Staging aufheben", "Änderungen verwerfen..." und "Git-Commit Dialog...".
  - Signal `commitRequested(Path)` zur Entkopplung und Status-Synchronisation nach Git-Aktionen.
- `ui/main_window.py`:
  - Menüeintrag *Ansicht* -> *Git-Commit Dialog...* mit Tastenkürzel `Ctrl+Alt+C`.
  - Signalverbindung `project_view.commitRequested.connect(self.show_git_commit)`.
  - Methode `show_git_commit()` zur dialoggestützten Ausführung.
- `ui/shortcuts_dialog.py`:
  - Aufnahme von `Git-Commit Dialog` (`Ctrl+Alt+C`) in die Tastaturkürzel-Referenz.
- `tests/test_git_staging_and_commit.py`:
  - 3 automatisierte Integrations- und GUI-Tests mit vollständiger Testabdeckung auf Basis temporärer Git-Repositories.

## [0.1.7] - 2026-09-10

### Quick-Open Datei-Finder & Befehlspalette (`Ctrl+P` / `Ctrl+Shift+P`)

- `ui/command_palette.py`: Neues Modul für eine zentrierte, tastaturgesteuerte Befehlspalette und Schnellauswahl:
  - **Quick-Open Modus (`Ctrl+P`)**: Schnelles Suchen und Öffnen von Dateien im aktuellen Projekt mit intelligenter Pfad- und Dateinamengewichtung (Scoring), Ignorieren von VCS- und Build-Ordnern (`.git`, `node_modules`, `__pycache__` etc.), Dateityp-Badges und Vorschau.
  - **Befehlspalette (`Ctrl+Shift+P` / führendes `>`)**: Vollständige Übersicht aller registrierten Menü- und Schnellaktionen der IDE mit Kategorie, Shortcuts und Tastaturnavigation.
  - Nahtloser Moduswechsel bei Eingabe oder Löschen des Präfix `>`.
  - Tastaturnavigation (`Pfeil Runter`, `Pfeil Rauf`, `Enter` zur Ausführung/Öffnen, `Esc` zum Abbrechen).
  - Volle Barrierefreiheit mit `AccessibleName` und `AccessibleDescription`.
- `ui/main_window.py`:
  - Integration von `act_quick_open` (`Ctrl+P`) im Menü *Datei*.
  - Integration von `act_palette` (`Ctrl+Shift+P`) im Menü *Bearbeiten*.
  - Methoden `show_quick_open()` und `show_command_palette()`.
- `ui/shortcuts_dialog.py`:
  - Tastaturkürzel-Tabelle um `Ctrl+P` und `Ctrl+Shift+P` ergänzt.
- `tests/test_command_palette.py`:
  - 9 automatisierte Tests für Dateisuche, Befehlsindexierung, Moduswechsel, Tastaturnavigation und Ausführung.
- `tests/test_assets_and_icons.py`:
  - 5 automatisierte Vertragstests für das Windows- und Multiplattform-Icon-Asset-Set (`CodeBox.ico`, `DesktopIcon.ico`, `assets/`, `mobile_icons/`, `store_assets/`).
- Versionsangleichung auf 0.1.7 in `pyproject.toml`, `version.py`, `README.md`, `README_de.md` und `CHANGELOG.md`.

## [0.1.6] - 2026-09-09

### Multi-Cursor & Column Selection Modus (2026-09-09)

- `core/multi_cursor.py`: Neues Modul für Multi-Cursor- und Spaltenauswahl-Verwaltung:
  - `MultiCursorManager`: Verwaltet sekundäre Cursoren (`secondary_cursors`), synchrone Eingaben, Cursor-Merging und Selektionen.
  - Methoden `add_cursor_at`, `toggle_cursor_at`, `add_cursor_above` (`Ctrl+Alt+Up`), `add_cursor_below` (`Ctrl+Alt+Down`).
  - `select_all_occurrences` (`Ctrl+Shift+L`): Markiert alle Vorkommen des aktuellen Worts oder der Auswahl mit synchronen Cursorn.
  - `add_next_occurrence` (`Ctrl+Alt+L`): Fügt das nächste Vorkommen sukzessive zur Mehrfachauswahl hinzu.
  - `column_select_between_cursors`: Rechteckige Spaltenauswahl über mehrere Zeilen via `Alt+Shift+Drag`.
  - Synchrone Textmanipulation: `insert_text`, `delete_backspace`, `delete_forward`, `unindent_cursors`, Auto-Pairing & Bracket-Wrapping (`insert_pair_or_wrap`).
  - Multi-Cursor Zwischenablage: `copy_selection`, `cut_selection` und zeilenweises `paste_text`.
  - Atomares Undo/Redo: Alle Änderungen über mehrere Cursoren hinweg werden in einem einzigen `beginEditBlock()`/`endEditBlock()` gekapselt.
  - Visuelles Rendering: `get_extra_selections()` mit `#264f78` und 2px scharfe Vektor-Carets in `paint_extra_carets()`.
- `core/editor.py`:
  - Integration von `MultiCursorManager`.
  - `paintEvent`: Rendert sekundäre Carets im Viewport.
  - `mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent`: `Alt+Klick` zum Setzen/Entfernen von Cursorn und `Alt+Shift+Ziehen` für Spaltenauswahl.
  - `keyPressEvent`: Tastatur-Shortcuts und synchrone Multi-Cursor-Tastendeligation.
  - `highlightCurrentLine`: Dynamische Einbindung sekundärer Selektionen.
- `ui/main_window.py`:
  - Untermenü *Mehrfachauswahl & Multi-Cursor* im Menü *Bearbeiten*.
  - Statusleistenanzeige: Anzeige von ` (X Cursor)` bei aktiven Mehrfachcursorn.
- `ui/shortcuts_dialog.py`: 6 neue Tastenkürzel für Multi-Cursor dokumentiert.
- `tests/test_multi_cursor.py`: 15 automatisierte Tests für Cursor-Erstellung, Spaltenauswahl, parallele Eingabe, Löschen, Navigation, Merging, Copy/Paste, Undo/Redo und UI-Aktionen (195 passed, 1 skipped).

## [0.1.5] - 2026-09-09

### Geteilte Editor-Ansichten (Split Editor Horizontal / Vertikal) (2026-09-09)

- `core/editor.py`:
  - `focusReceived = Signal()`: Emittiert bei Fokuswechsel (`focusInEvent`) für präzises Tracking des aktiven Editors zwischen Split-Panes.
- `core/tabs.py`:
  - `EditorTab`: Unterstützung für geteilte Dokumente (`shared_doc`) und Factory-Methode `create_clone()`.
  - `TabWidget`: Methoden `clone_tab()` und `move_tab_from()` für nahtlose Tab-Übertragung zwischen Split-Bereichen; Signale `tabFocused` und `tabCountChanged`. Sicheres Schließen von Klonen ohne redundante Speicher-Dialoge.
- `ui/main_window.py`:
  - Splitter-Struktur: `editor_splitter` (`QSplitter`) fasst primäres (`tab_widget`) und geteiltes (`split_tab_widget`) TabWidget zusammen.
  - Dynamische Aufteilung: Horizontale (`split_editor_right`, `Ctrl+\`) und vertikale (`split_editor_down`, `Ctrl+Shift+\`) Teilung mit synchroner Echtzeit-Bearbeitung des gemeinsamen `QTextDocument`.
  - Fokus & Navigation: `focus_other_split` (`F6`) und `move_tab_to_other_split` (`Ctrl+Alt+M`).
  - Auto-Unsplit & Safe Unsplit (`unsplit_editor`, `Ctrl+Alt+W`): Automatisches Einklappen beim Schließen des letzten Split-Tabs; sichere Überführung exklusiver Dokumente in den Primärbereich.
  - Statusleiste, Suche (`FindReplaceDialog`), Aktionen (Undo/Redo, Ausführen, LSP/Linter) und Beenden-Prüfung (`closeEvent`) nahtlos an den aktiven Split-Pane gekoppelt.
- `ui/shortcuts_dialog.py`: Neue Tastenkürzel in der Kategorie *Ansicht* dokumentiert.
- `tests/test_split_editor.py`: 9 automatisierte Tests für horizontales/vertikales Teilen, synchrone Dokumentbearbeitung, Fokus-Wechsel, Tab-Verschiebung, Auto-Unsplit und Dialog-Anbindung (180 passed, 1 skipped).

## [0.1.4] - 2026-09-08

### Code-Folding für Funktionen und Klassen (2026-09-08)

- `core/folding.py`: Neues Modul für Faltungserkennung und Block-Sichtbarkeitsverwaltung:
  - `FoldRegion`: Datenklasse für Start-/Endzeile, Typ (Funktion/Klasse/Block), Name und hierarchische Signatur für persistente Faltungszustände über Zeilenverschiebungen hinweg.
  - `FoldDetector`: Präzise Erkennung für Python (Funktionen, `async def`, Klassen über Einrückungs- und Scope-Tracking) und geschweifte Klammern (`{ ... }` für JS, TS, C++, Rust, Go, Java, JSON) unter Ausschluss von String-Literalen und Kommentaren.
  - `FoldingManager`: Verwaltung des aktiven Faltungszustands und native Kopplung an `QTextBlock.setVisible(bool)` mit `QTextDocument.markContentsDirty(0, count)`.
  - Cursorsicherheit: Verhindert unsichtbare Cursors durch automatische Neupositionierung auf die Kopfzeile beim Einklappen.
- `core/editor.py`:
  - `LineNumberArea`: Um Faltungsspalte (`FOLD_AREA_WIDTH = 14`) erweitert; High-DPI Vektor-Rendering für `▼` (ausgeklappt) und `▶` (eingeklappt); Klick zum Umschalten und dynamischer Hover-Cursor (`PointingHandCursor`).
  - Methoden `toggle_fold`, `toggle_fold_at_cursor`, `fold_all`, `unfold_all`, `is_line_foldable`, `is_line_folded`.
  - `_schedule_fold_update`: Entprellte (debounced) Hintergrund-Aktualisierung bei Text- und Provideränderungen.
- `core/tabs.py`: Setzt `file_path` Eigenschaft auf Editor und aktualisiert Faltung beim Laden.
- `ui/main_window.py`: Untermenü *Code-Faltung* im Menü *Ansicht* verankert:
  - *Faltung umschalten* (`Ctrl+Shift+[`)
  - *Alles einklappen* (`Ctrl+Alt+[`)
  - *Alles ausklappen* (`Ctrl+Alt+]`)
- `ui/shortcuts_dialog.py`: Shortcuts in der Kategorie *Ansicht* dokumentiert.
- `tests/test_code_folding.py`: 10 neue automatisierte Tests für Python- und Brace-Erkennung, Gutter-Klick, Visibility, Cursor-Schutz und MainWindow-Aktionen.

## [0.1.3] - 2026-09-07

### Integrierter Git Diff-Viewer & Status-Parser-Härtung (2026-09-07)

- `ui/diff_viewer.py`: Neuer nativer Git Diff-Viewer (`DiffViewerDialog`) für CodeBox:
  - **Unified Diff-Modus**: Einspaltige Ansicht mit WCAG-konformer Syntaxhervorhebung (`DiffHighlighter`) für Einfügungen (`+`), Löschungen (`-`), Hunk-Header (`@@`) und Git-Metadaten.
  - **Side-by-Side Diff-Modus**: Zweispaltige Ansicht mit `QSplitter`, synchronisiertem Scrollen (`valueChanged`-Kopplung) und Linienpräfix-Highlighter (`SideBySideHighlighter`) über zeilenbasierte `compute_side_by_side()`-Ausrichtung.
  - **Dateiauswahl & Status**: Dropdown-Auswahl aller geänderten Dateien oder des Gesamtrepositories mit Git-Status-Badges (`[M]`, `[S]`, `[U]`, `[D]`).
  - **Staging-Umschaltung**: Sofortiges Umschalten zwischen Arbeitsbaum-Änderungen und gestageten Commits (`--cached`).
  - **Chunk-Navigation**: Tastaturnavigation von Chunk zu Chunk via `Alt+Up` und `Alt+Down`.
  - **Editor-Integration**: Direktsprung in den Haupteditor über den Button *Im Editor öffnen* oder Doppelklick.
  - **Vollständige Barrierefreiheit**: WCAG AA/AAA-Farbkontraste, `accessibleName`, `accessibleDescription` und Tastaturfokus-Verwaltung.
- `ui/main_window.py`: Menüaktion *Git-Diff anzeigen...* im Menü *Ansicht* mit Shortcut `Ctrl+Alt+D` verankert und `show_diff()` implementiert; Signalanbindung an `ProjectView.diffRequested`.
- `features/project_view.py`: Kontextmenü um *Git-Diff anzeigen* erweitert; emittiert `diffRequested(Path)`.
- `ui/shortcuts_dialog.py`: Neuer Shortcut `Ctrl+Alt+D` in der Ansicht-Kategorie registriert.
- `features/git_integration.py`:
  - `_run_git()`: Behoben: `result.stdout.strip()` entfernte das führende Leerzeichen von Zeilen im Format ` M <datei>` in `git status --porcelain`, wodurch der erste Buchstabe des Dateinamens abgeschnitten wurde (`rstrip("\r\n")` statt `strip()`).
  - `get_diff()`: Fallback für ungetrackte Dateien via `difflib.unified_diff` integriert.
  - `get_file_content_at_head()` und `get_file_content_in_index()` für präzisen Dateiinhalt-Abgleich hinzugefügt.
- `tests/test_diff_viewer.py`: 13 neue automatisierte Tests für Diff-Highlighting, Side-by-Side-Berechnung, Dialog-Initialisierung, Dateiauswahl, Staging-Toggle, Chunk-Navigation, Barrierefreiheit und Editor-Sprung (161 passed, 1 skipped).

## [0.1.2] - 2026-08-24

### High-End Editor-, Highlighter- & Performance-Härtung (2026-08-24)

- `core/highlighter.py`: Multi-Line Docstrings & Block-Comments über Blockgrenzen hinweg via Qt `QSyntaxHighlighter`-Zustandsautomat (`previousBlockState()`, `setCurrentBlockState()`) implementiert. Vollständige Unterstützung für Python Docstrings (`"""..."""` und `'''...'''`), C/C++/Java/Rust/Go/JavaScript Block-Kommentare (`/* ... */`) und deklarative Plugin-Begrenzer ohne Zustandslecks bei Einzeilern.
- `core/editor.py`:
  - Intelligente Block-Einrückung (`indent_selection`) und -Ausrückung (`unindent_selection`) mit Tastenkürzeln `Tab` und `Shift+Tab` / `Backtab` für Einzelzeilen und mehrzeilige Selektionen.
  - Zeilenkommentar-Umschaltung (`toggle_comment`) mit `Ctrl+/` und `Ctrl+#` (erkennt Provider-spezifische Tokens wie `#` und `//` und kommentiert konsistent ein/aus).
  - Zeilen-Duplizierung (`duplicate_line_or_selection`) via `Ctrl+D` und Zeilenverschiebung nach oben/unten (`move_line_up`, `move_line_down`) via `Alt+Up` / `Alt+Down`.
  - Minimap-Performanceoptimierung: Caching von Dokumentzeilen (`_cached_lines`) und maximaler Zeichenlänge (`_cached_max_chars`) mit ereignisgesteuerter Invalidierung (`contentsChanged`, `textChanged`, `blockCountChanged`). Verhindert redundante Iterationen über zehntausende Textblöcke pro Frame.
- `ui/main_window.py`:
  - `_goto_line`: Fehler behoben, bei dem die Cursorposition immer unkonditioniert an Zeile 1 sprang; navigiert nun präzise zum Zielblock `document().findBlockByNumber(line - 1)`.
  - Aktionen `Zeilenkommentar umschalten` (`Ctrl+/`), `Einrücken` (`Tab`) und `Ausrücken` (`Shift+Tab`) im Menü *Bearbeiten* verankert.
- `ui/shortcuts_dialog.py`: Tastenkürzel-Übersicht um die neuen Editor-Aktionen für Kommentar-Umschaltung, Duplizieren und Zeilenverschiebung erweitert.
- `tests/`: 4 neue Testmodule ergänzt (164 Tests passed in 19.5s, 100% Abdeckung):
  - `tests/test_multiline_highlighter.py`: Multi-Line Docstrings und Block-Kommentare über Blockgrenzen.
  - `tests/test_block_indent_and_comment.py`: Block-Einrückung, Dedentation, Kommentar-Umschaltung und Tastenkürzel.
  - `tests/test_minimap_performance.py`: Minimap-Zeilen-Caching, Invalidierung und Render-Effizienz.
  - `tests/test_goto_line_navigation.py`: Zeilensprung-Navigation und Menü-Delegation.

### Marketing, Discoverability & Diagramm-Architektur (2026-08-24)

- `README.md` & `README_de.md`: Umfassende Überarbeitung des Projektauftritts und der Auffindbarkeit (Pfad B):
  - Zweisprachige interaktive Mermaid-Diagramme (`flowchart TD` für Schichtenarchitektur aus UI, Core/Tabs, ProjectTree, LSP/Diagnostics und Runtime/Plugins sowie `sequenceDiagram` mit autonomer Nummerierung für den End-to-End Workflow-Lebenszyklus von Editor-Öffnung über asynchrones Linting/LSP-Abfrage bis Terminal-Ausführung).
  - Strukturierte zweisprachige Schnellnavigation mit 15 Sprungmarken in beiden README-Dateien.
  - Detaillierte Tabelle der Kernfähigkeiten und Sicherheits-/Datenschutz-Laufzeitinvarianten (100% Offline / Zero-Egress, Non-Elevation User Mode, Universal Highlighting, Declarative Plugins, Non-Blocking LSP & Linters, Speicherverlust-Schutz).
  - Shields.io Badges harmonisiert und erweitert (CI-Status, Tests 120 passed | 100%, Python 3.10-3.13, Plattformen Windows/Linux/macOS, Datenschutz Zero-Egress, zweisprachige Sicherheitsrichtlinie, dev-bricks Ökosystem, open-bricks Dachverband, Version 0.1.2, LSP-Ready, llms.txt).
  - Geschwister-Ökosystem-Matrix mit 9 Partner-Repositories über `dev-bricks`, `ellmos-ai`, `doc-bricks`, `file-bricks` und `open-bricks` verankert.
- `SECURITY.md`: Zweisprachige Sicherheitsrichtlinie (Englisch / Deutsch) mit verbindlichen Garantien für Local-First & Zero-Egress (100% Offline, keine Telemetrie), unprivilegiertem User-Mode (Non-Elevation), Subprozess-Sicherheit, direkten Sicherheitskontaktadressen (`security@ellmos.ai`, `lukas@open-bricks.org`, `support@lukasgeiger.com`), Supported Versions Matrix (`0.1.x`) und vertraulichem GitHub Advisories Melde-Link.
- `.github/workflows/ci.yml`: Neuer Multi-OS GitHub Actions CI-Workflow für `ubuntu-latest`, `windows-latest`, `macos-latest` über die Python-Matrix `['3.10', '3.11', '3.12', '3.13']` mit Concurrency-Steuerung (`cancel-in-progress: true`), `actions/checkout@v4`, `actions/setup-python@v5`, Linting-Gate (`ruff check .`) und vollständiger Pytest-Ausführung.
- `.github/workflows/linux-platform-smoke.yml`: Action-Tags auf kanonisches `@v4` und `@v5` korrigiert und Concurrency-Steuerung ergänzt.
- `pyproject.toml`: PEP 621 Classifiers (Python 3.13, OS Independent, POSIX Linux, MacOS, Microsoft Windows, Desktop Environment, Utilities) und vollständige URLs (`Changelog`, `Security`, `Parent Org`, `Umbrella Ecosystem`) ergänzt.
- `llms.txt`: Last-checked Zeitstempel auf `2026-08-24`, Version `0.1.2`, erweiterte Modulreferenzen, Navigation und Teststand synchronisiert.
- `tests/test_metadata.py`: Metadaten- und Vertragstestsuite um 6 neue Contract-Tests erweitert (Bilingual Parity, Mermaid Syntax, Sibling Ecosystem, Security & Zero-Egress Invariants, CI Workflow Integrity, PEP 621 Classifiers & URLs).

### Terminal- & Prozess-Streaming-Härtung (2026-08-22)

- `features/terminal.py`: Verzeichniswechsel via `set_working_dir()` für PowerShell korrigiert (PowerShell unterstützt keinen `/d`-Schalter von cmd.exe; `cd` führte zuvor zu `PositionalParameterNotFound`-Fehlern und verweigerte das Wechseln des Arbeitsordners). Output-Dekodierung in `_on_stdout` und `_on_stderr` auf dynamisches `_output_encoding()` (cp1252 für cmd unter Windows, sonst utf-8) umgestellt. Signalverwaltung um `errorOccurred` und sauberes Exception-Handling erweitert.
- `core/output.py`: `OutputPanel` mit `errorOccurred`-Signalbehandlung (`_on_error`) gegen hängende Stop-Buttons und unterdrückte Fehlermeldungen bei nicht auffindbaren Compilern/Programmen (`FailedToStart`, `Crashed`) abgesichert. `waitForFinished(1000)` nach `kill()` und `closeEvent` für zuverlässige Prozessbereinigung ergänzt.
- `tests/test_terminal_encoding.py` & `tests/test_output_panel.py`: 6 neue Regressionstests für PowerShell-Verzeichniswechsel, Output-Encoding, Signal-Entkopplung, Fehlerausgabe und Prozessbeendigung ergänzt (115 passed, 1 skipped).

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
