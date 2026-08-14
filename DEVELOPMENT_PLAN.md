# CodeBox - Entwicklungsplan

> **Ziel:** PythonBox v8 -> CodeBox (Multi-Language IDE)
> **Basis:** PythonBox_v8.py (3,381 Zeilen)
> **Erstellt:** 2026-01-26
> **Aktualisiert:** 2026-08-14

---

## Übersicht

| Phase | Beschreibung | Aufwand | Status |
|-------|--------------|---------|--------|
| 1 | Core Refactoring | ~4h | ERLEDIGT |
| 2 | Python Provider | ~1h | ERLEDIGT |
| 3 | Weitere Sprachen & Registry | ~4h | ERLEDIGT (JS, TS, C++, Rust, Go, Java) |
| 4 | Features, Plugins & Polish | ~4h | ERLEDIGT |
| **Gesamt** | | **~13h** | **100% ABGESCHLOSSEN** |

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

### 3.1 JavaScript & TypeScript - DONE
- [x] `languages/javascript_lang.py`
- [x] `languages/typescript_lang.py`
- [x] Keywords, Builtins, Snippets
- [x] node / ts-node Run-Command

### 3.2 C/C++, Rust, Go & Java - DONE
- [x] `languages/cpp_lang.py`
- [x] `languages/rust_lang.py`
- [x] `languages/go_lang.py`
- [x] `languages/java_lang.py`

### 3.3 Provider-Registry & Dynamic Extensions - DONE (2026-08-14)
- [x] `languages/__init__.py` mit dynamischer Provider-Registrierung (`register_provider`, `unregister_provider`, `reset_providers`)
- [x] Listener-System (`add_provider_listener`, `remove_provider_listener`) für reaktive UI-Aktualisierung
- [x] Declarative JSON Language Provider (`languages/declarative.py`)

---

## Phase 4: Features, Plugins & Polish - ERLEDIGT (2026-08-14)

### 4.1 Statusbar & Toolbar Sprachauswahl - DONE (2026-02-12)
- [x] Dropdown in Toolbar
- [x] Manuelle Sprachauswahl
- [x] Automatische Erkennung bei Dateieröffnung
- [x] Dynamische Aktualisierung bei Plugin-Registrierung

### 4.2 Einstellungs-Dialog - DONE
- [x] `config/__init__.py` mit Settings-System (Font, Size, TabSize, Minimap, Theme)
- [x] `ui/settings_dialog.py` Einstellungs-Dialog
- [x] Theme-Auswahl Dialog & Runtime Theme Switching

### 4.3 Linter- und LSP-Integration - DONE (2026-08-11)
- [x] Error-Markers im Editor (set_linter_errors)
- [x] Generisches Linter-System (automatischer Aufruf beim Speichern)
- [x] Problems-Panel für LSP- und Linter-Diagnosen mit Sprung zur Position

### 4.4 Plugin-System & Erweiterbarkeit - DONE (2026-08-14)
- [x] `features/plugin_manager.py`: Automatische Entdeckung und Laden von Plugins aus Projekt- und Benutzerordnern (`plugins/`, `~/.codebox/plugins/`)
- [x] Deklarative JSON-Plugins (z.B. `plugins/lua_plugin.json`, `plugins/ruby_plugin.json`)
- [x] Python-basierte Plugins (`.py`)
- [x] `ui/plugins_dialog.py`: UI zur Verwaltung, Aktivierung/Deaktivierung und Erstellung von Vorlagen (`Ctrl+Shift+P`)

### 4.5 Dokumentation & Dialoge - DONE (2026-08-14)
- [x] README.md & README_de.md für CodeBox
- [x] Tastenkürzel-Übersicht (`ui/shortcuts_dialog.py`, Shortcut: `F1`)
- [x] Über CodeBox Dialog

### 4.6 Minimap & Editor Polish - DONE
- [x] `core/minimap.py`: Mini-Codeübersicht mit synchronem Scrollen und Sichtbarkeitsumschaltung
- [x] Auto-Close von Klammern und Anführungszeichen
- [x] Drag & Drop Tab-Reordering
- [x] Save-Failure Guards und unsaved changes confirmation

### 4.7 Abschluss & Build
- [x] `requirements.txt` erstellen
- [x] `start.bat` anpassen
- [x] lokales Build-Script (`build_exe.bat`) mit PyInstaller
- [x] Kompilieren und EXE testen (PyInstaller Build verifiziert)

---

## Meilensteine

| Meilenstein | Kriterien | Status |
|-------------|-----------|--------|
| **M1: Lauffähig** | main.py startet, Editor zeigt Code | ERREICHT |
| **M2: Python funktioniert** | Python-Highlighting, Run, Snippets | ERREICHT |
| **M3: Multi-Language** | 3+ Sprachen nutzbar | ERREICHT (Python, JS, TS, C++, Rust, Go, Java, Lua, Ruby) |
| **M4: Release-Ready** | Doku, Tests, Plugin-System, EXE | ERREICHT |

---

## Referenzen

- [CodeBox_Konzept.md](./CodeBox_Konzept.md) - Architektur & Code-Beispiele
- [Feature_Analyse_PythonBox.md](./Feature_Analyse_PythonBox.md) - Basis-Features
- [PythonBox_v8.py](../PythonBox_v8.py) - Quellcode-Basis

---

*Plan erstellt: 2026-01-26 | Vollständig abgeschlossen: 2026-08-14 durch Antigravity Agent*
