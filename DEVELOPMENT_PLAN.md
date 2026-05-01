# CodeBox - Entwicklungsplan

> **Ziel:** PythonBox v8 -> CodeBox (Multi-Language IDE)
> **Basis:** PythonBox_v8.py (3,381 Zeilen)
> **Erstellt:** 2026-01-26
> **Aktualisiert:** 2026-05-01

---

## Übersicht

| Phase | Beschreibung | Aufwand | Status |
|-------|--------------|---------|--------|
| 1 | Core Refactoring | ~4h | ERLEDIGT |
| 2 | Python Provider | ~1h | ERLEDIGT |
| 3 | Weitere Sprachen | ~4h | ERLEDIGT (JS, C++) |
| 4 | Features & Polish | laufend | Teilweise |
| **Gesamt** | | **~12h** | |

---

## Phase 1: Core Refactoring - ERLEDIGT (2026-02-12)

### 1.1 Projektstruktur anlegen - DONE (2026-01-26)
- [x] Ordnerstruktur erstellen
- [x] `__init__.py` Dateien anlegen
- [x] Basis-main.py mit Imports

### 1.2 LanguageProvider ABC erstellen - DONE (2026-02-12)
- [x] `languages/base.py` mit abstrakter Basisklasse
- [x] Alle Provider-Methoden definieren
- [x] Type Hints und Docstrings

### 1.3 Core-Komponenten extrahieren - DONE (2026-02-12)
- [x] `core/editor.py` - CodeEditor-Widget (Zeilennummern, Bracket Matching, Auto-Completion)
- [x] `core/tabs.py` - Tab-System
- [x] `core/output.py` - Output/Run Panel mit QProcess
- [x] Auto-Completion in editor.py integriert

### 1.4 UI-Komponenten extrahieren - DONE (2026-02-12)
- [x] `ui/main_window.py` - Hauptfenster mit Menü, Toolbar, Statusbar
- [x] Suchen und Gehe-zu-Zeile implementiert

### 1.5 UniversalHighlighter - DONE (2026-02-12)
- [x] `core/highlighter.py` - Provider-basiertes Highlighting
- [x] Kommentar-Style aus Provider lesen
- [x] Keywords, Builtins, Strings, Numbers, Comments

### 1.6 Integration - DONE (2026-02-12)
- [x] main.py startet mit Dark Theme
- [x] Editor mit Tabs
- [x] Output-Panel integriert

---

## Phase 2: Python Provider - ERLEDIGT (2026-02-12)

### 2.1 PythonProvider erstellen - DONE
- [x] `languages/python_lang.py`
- [x] Keywords, Builtins aus PythonBox übernommen
- [x] Snippets definiert
- [x] Run/Debug Commands

---

## Phase 3: Weitere Sprachen - ERLEDIGT (2026-02-12)

### 3.1 JavaScript - DONE
- [x] `languages/javascript_lang.py`
- [x] Keywords, Builtins, Snippets
- [x] node Run-Command

### 3.2 C/C++ - DONE
- [x] `languages/cpp_lang.py`
- [x] Keywords inkl. Preprocessor
- [x] Snippets, g++ Compile+Run

### 3.5 Provider-Registry - DONE
- [x] `languages/__init__.py` mit Auto-Discovery
- [x] Extension -> Provider Mapping
- [x] Fallback für unbekannte Extensions

---

## Phase 4: Features & Polish - TEILWEISE

### 4.1 Statusbar-Sprachauswahl - DONE (2026-02-12)
- [x] Dropdown in Toolbar
- [x] Manuelle Sprachauswahl
- [x] Automatische Erkennung bei Dateieröffnung

### 4.2 Einstellungs-Dialog
- [x] config/__init__.py mit Settings-System
- [ ] Pro-Sprache Interpreter-Pfad
- [ ] Theme-Auswahl Dialog

### 4.3 Linter-Integration
- [x] Error-Markers im Editor (set_linter_errors)
- [ ] Generisches Linter-System (automatischer Aufruf)
- [ ] Problems-Panel

### 4.4 Dokumentation
- [x] README.md für CodeBox
- [x] GitHub-Community-Dateien aktualisieren
- [ ] Tastenkürzel-Übersicht

### 4.5 Abschluss
- [x] requirements.txt erstellen
- [x] start.bat anpassen
- [x] lokales Build-Script (`build_exe.bat`) ergänzen
- [ ] Kompilieren und EXE testen

---

## Meilensteine

| Meilenstein | Kriterien | Status |
|-------------|-----------|--------|
| **M1: Lauffähig** | main.py startet, Editor zeigt Code | ERREICHT |
| **M2: Python funktioniert** | Python-Highlighting, Run, Snippets | ERREICHT |
| **M3: Multi-Language** | 3+ Sprachen nutzbar | ERREICHT (Python, JS, TS, C++, Rust, Go, Java) |
| **M4: Release-Ready** | Doku, Tests, EXE | Offen |

---

## Nächste Aktionen

- Runtime-Test der LSP-Integration mit installiertem `python-lsp-server`
- Linter automatisch bei Speichern ausführen
- Problems-Panel ergänzen
- Minimap aus PythonBox portieren
- EXE-Build aus `build_exe.bat` prüfen

---

## Referenzen

- [CodeBox_Konzept.md](./CodeBox_Konzept.md) - Architektur & Code-Beispiele
- [Feature_Analyse_PythonBox.md](./Feature_Analyse_PythonBox.md) - Basis-Features
- [PythonBox_v8.py](../PythonBox_v8.py) - Quellcode-Basis

---

*Plan erstellt: 2026-01-26 | Aktualisiert: 2026-05-01 durch Codex Automation*
