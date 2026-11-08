# CodeBox - Nutzertest-Checkliste

**Version:** 0.3.5
**Stand:** 2026-11-08
**Tester:** _______________

---

## 1. Grundfunktionen

- [ ] Anwendung startet ohne Fehler (`python main.py`)
- [ ] Dark Theme wird korrekt angezeigt
- [ ] Light Theme kann aktiviert werden und bleibt konsistent hell
- [ ] Fenster-Größe und -Position stimmen
- [ ] Menü-Leiste ist vollständig (Datei, Bearbeiten, Ausführen)
- [ ] Toolbar-Buttons funktionieren

## 2. Datei-Operationen

- [ ] Neue Datei erstellen (Ctrl+N)
- [ ] Datei öffnen (Ctrl+O)
- [ ] Datei speichern (Ctrl+S)
- [ ] "Speichern unter" bei neuer Datei
- [ ] Ungespeicherte Änderungen: Warnung beim Schließen

## 3. Editor-Funktionen

- [ ] Zeilennummern werden angezeigt
- [ ] Aktuelle Zeile wird hervorgehoben
- [ ] Auto-Indent bei Enter
- [ ] Auto-Close Brackets: (), [], {}, "", ''
- [ ] Bracket Matching (passende Klammern hervorgehoben)
- [ ] Undo/Redo funktioniert (Ctrl+Z / Ctrl+Y)
- [ ] Minimap wird am rechten Editor-Rand angezeigt und erlaubt Navigation per Klick und Ziehen
- [ ] Code-Folding: Falt-Indikatoren in der Randleiste klappen Code-Blöcke ein und aus (Menü *Ansicht > Code-Faltung*)

## 4. Syntax-Highlighting

### Python (.py)
- [ ] Keywords (def, class, if, for, ...) blau und fett
- [ ] Strings (einfach/doppelt) orange
- [ ] Kommentare (#) grün und kursiv
- [ ] Zahlen hellgrün
- [ ] Decorators (@) lila

### JavaScript (.js)
- [ ] Keywords (function, const, let, ...) blau und fett
- [ ] Strings orange
- [ ] Kommentare (//) grün und kursiv
- [ ] Builtins (console, Array, ...) gelb

### C++ (.cpp)
- [ ] Keywords (class, int, return, ...) blau
- [ ] Preprocessor (#include, #define) lila
- [ ] Strings und Kommentare korrekt

## 5. Auto-Completion

- [ ] Popup erscheint nach 2+ Buchstaben
- [ ] Python-Keywords vorgeschlagen
- [ ] Auswahl mit Enter/Tab funktioniert
- [ ] Snippets werden korrekt eingefügt

## 6. Tab-System

- [ ] Mehrere Dateien in Tabs öffnen
- [ ] Tab wechseln per Klick
- [ ] Tab schließen (X-Button)
- [ ] Modifizierter Tab zeigt *
- [ ] Gleiche Datei wird nicht doppelt geöffnet

## 7. Projektbaum, Terminal, LSP und Linter

- [ ] Projektbaum per Ctrl+B ein-/ausblenden
- [ ] Terminal per Ctrl+` ein-/ausblenden
- [ ] Terminal-Arbeitsverzeichnis folgt der geöffneten Datei
- [ ] Automatisches Linting: Lokaler Linter (Ruff/flake8/ESLint) prüft beim Speichern asynchron und meldet Befunde im Probleme-Panel und Editor
- [ ] Mit installiertem LSP-Server erscheinen Diagnostics im Editor
- [ ] LSP-Completion erscheint nach Eingabe von mindestens zwei Zeichen

## 8. Ausführung

- [ ] Python-Datei ausführen (F5)
- [ ] Output im Output-Panel sichtbar
- [ ] Fehler-Output rot dargestellt
- [ ] Stop-Button beendet laufenden Prozess
- [ ] Clear-Button leert Output

## 9. Suchen

- [ ] Ctrl+F öffnet Such-Dialog
- [ ] Treffer werden hervorgehoben
- [ ] Anzahl Treffer in Statusbar

## 10. Statusbar

- [ ] Zeile/Spalte wird angezeigt
- [ ] Aktuelle Sprache wird angezeigt
- [ ] Encoding (UTF-8) wird angezeigt

## 11. Sprach-Auswahl

- [ ] Dropdown in Toolbar vorhanden
- [ ] Sprache wechseln ändert Highlighting
- [ ] Auto-Erkennung bei Datei öffnen

---

## Bekannte Einschränkungen

- **LSP-Runtime-Integrationstest:** Der optionale End-to-End-LSP-Laufzeittest (`tests/test_lsp_runtime.py`) setzt einen lokal installierten und konfigurierten Sprachserver (z. B. `pylsp` / `pyright` bzw. `python-lsp-server[all]`) sowie die Umgebungsvariable `CODEBOX_LSP_RUNTIME=1` voraus. Ohne externen Sprachserver wird dieser Test im automatisierten CI-/Testlauf regulär und erwartungskonform als `skipped` ausgewiesen (360 passed, 1 skipped).

---

## Ergebnis

| Kategorie | Bestanden | Fehlgeschlagen | Kommentar |
|-----------|-----------|----------------|-----------|
| Grundfunktionen | ___ / 6 | | |
| Datei-Operationen | ___ / 5 | | |
| Editor | ___ / 8 | | |
| Highlighting | ___ / 12 | | |
| Completion | ___ / 4 | | |
| Tabs | ___ / 5 | | |
| Projektbaum/Terminal/LSP/Linter | ___ / 6 | | |
| Ausführung | ___ / 5 | | |
| Suchen | ___ / 3 | | |
| Statusbar | ___ / 3 | | |
| Sprach-Auswahl | ___ / 3 | | |
| **Gesamt** | ___ / 60 | | |

---

*Checkliste erstellt: 2026-02-12 durch ATI Worker 2, aktualisiert 2026-11-08 für Version 0.3.5*
