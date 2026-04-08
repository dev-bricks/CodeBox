# CodeBox - Nutzertest-Checkliste

**Version:** 0.1.0
**Stand:** 2026-02-12
**Tester:** _______________

---

## 1. Grundfunktionen

- [ ] Anwendung startet ohne Fehler (`python main.py`)
- [ ] Dark Theme wird korrekt angezeigt
- [ ] Fenster-Groesse und -Position stimmen
- [ ] Menue-Leiste ist vollstaendig (Datei, Bearbeiten, Ausfuehren)
- [ ] Toolbar-Buttons funktionieren

## 2. Datei-Operationen

- [ ] Neue Datei erstellen (Ctrl+N)
- [ ] Datei oeffnen (Ctrl+O)
- [ ] Datei speichern (Ctrl+S)
- [ ] "Speichern unter" bei neuer Datei
- [ ] Ungespeicherte Aenderungen: Warnung beim Schliessen

## 3. Editor-Funktionen

- [ ] Zeilennummern werden angezeigt
- [ ] Aktuelle Zeile wird hervorgehoben
- [ ] Auto-Indent bei Enter
- [ ] Auto-Close Brackets: (), [], {}, "", ''
- [ ] Bracket Matching (passende Klammern hervorgehoben)
- [ ] Undo/Redo funktioniert (Ctrl+Z / Ctrl+Y)

## 4. Syntax-Highlighting

### Python (.py)
- [ ] Keywords (def, class, if, for, ...) blau und fett
- [ ] Strings (einfach/doppelt) orange
- [ ] Kommentare (#) gruen und kursiv
- [ ] Zahlen hellgruen
- [ ] Decorators (@) lila

### JavaScript (.js)
- [ ] Keywords (function, const, let, ...) blau und fett
- [ ] Strings orange
- [ ] Kommentare (//) gruen und kursiv
- [ ] Builtins (console, Array, ...) gelb

### C++ (.cpp)
- [ ] Keywords (class, int, return, ...) blau
- [ ] Preprocessor (#include, #define) lila
- [ ] Strings und Kommentare korrekt

## 5. Auto-Completion

- [ ] Popup erscheint nach 2+ Buchstaben
- [ ] Python-Keywords vorgeschlagen
- [ ] Auswahl mit Enter/Tab funktioniert
- [ ] Snippets werden korrekt eingefuegt

## 6. Tab-System

- [ ] Mehrere Dateien in Tabs oeffnen
- [ ] Tab wechseln per Klick
- [ ] Tab schliessen (X-Button)
- [ ] Modifizierter Tab zeigt *
- [ ] Gleiche Datei wird nicht doppelt geoeffnet

## 7. Ausfuehrung

- [ ] Python-Datei ausfuehren (F5)
- [ ] Output im Output-Panel sichtbar
- [ ] Fehler-Output rot dargestellt
- [ ] Stop-Button beendet laufenden Prozess
- [ ] Clear-Button leert Output

## 8. Suchen

- [ ] Ctrl+F oeffnet Such-Dialog
- [ ] Treffer werden hervorgehoben
- [ ] Anzahl Treffer in Statusbar

## 9. Statusbar

- [ ] Zeile/Spalte wird angezeigt
- [ ] Aktuelle Sprache wird angezeigt
- [ ] Encoding (UTF-8) wird angezeigt

## 10. Sprach-Auswahl

- [ ] Dropdown in Toolbar vorhanden
- [ ] Sprache wechseln aendert Highlighting
- [ ] Auto-Erkennung bei Datei oeffnen

---

## Bekannte Einschraenkungen

- Minimap noch nicht implementiert (aus PythonBox v8)
- Code-Folding noch nicht implementiert
- Linter wird noch nicht automatisch ausgefuehrt
- Rust/Go Provider noch nicht vorhanden

---

## Ergebnis

| Kategorie | Bestanden | Fehlgeschlagen | Kommentar |
|-----------|-----------|----------------|-----------|
| Grundfunktionen | ___ / 5 | | |
| Datei-Operationen | ___ / 5 | | |
| Editor | ___ / 6 | | |
| Highlighting | ___ / 10 | | |
| Completion | ___ / 4 | | |
| Tabs | ___ / 5 | | |
| Ausfuehrung | ___ / 5 | | |
| Suchen | ___ / 3 | | |
| Statusbar | ___ / 3 | | |
| Sprach-Auswahl | ___ / 3 | | |
| **Gesamt** | ___ / 49 | | |

---

*Checkliste erstellt: 2026-02-12 durch ATI Worker 2*
