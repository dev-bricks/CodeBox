# API- und CLI-Status

Stand: 2026-07-27

Dieses Dokument beschreibt ausschließlich die tatsächlich implementierte
Steueroberfläche von CodeBox. Es ersetzt ältere, zu weit gehende Hinweise auf
eine REST-API, OpenAPI-Dokumentation oder Fernsteuerung.

## Vorhandene lokale CLI

CodeBox wird aus dem Quellbaum mit `python main.py` gestartet. Für die
Dateiübergabe unterstützt der Einstiegspunkt genau diese Formen:

```text
python main.py --open <datei>
python main.py <datei>
```

Die CLI öffnet eine Datei beim App-Start. Sie steuert keine bereits laufende
Instanz und bietet keine Befehle zum Ausführen, Schließen oder Auflisten von
Tabs. Ein separat installierbares Kommando `codebox` ist ebenfalls nicht Teil
des aktuellen Projekts.

## Nicht vorhanden

- kein HTTP-Listener und keine REST-Routen;
- keine Authentifizierung oder Token-Konfiguration;
- keine OpenAPI-/Swagger-Spezifikation;
- keine Remote- oder Agentensteuerung.

Damit existiert derzeit keine Netzwerkschnittstelle, über die lokale Dateien
oder Editorzustand fernbedient werden könnten.

## Nächster möglicher Ausbau

Eine REST- oder Agentenschnittstelle wird erst als eigene Aufgabe spezifiziert.
Vor einer Implementierung müssen mindestens Bind-Adresse, Lebenszyklus einer
laufenden Instanz, Berechtigungsmodell, Token-Speicherung, erlaubte
Dateipfade, Fehlerantworten und eine OpenAPI-Spezifikation festgelegt werden.
Bis dahin bleibt die lokale Dateiübergabe die unterstützte Schnittstelle.

## Aufgabenbezug

TW-CB-02 ist mit dieser Bestandsklärung abgeschlossen. Eine spätere
Implementierung wird als neue, separat prüfbare Aufgabe angelegt.
