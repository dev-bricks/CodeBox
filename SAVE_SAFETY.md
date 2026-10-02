# Speichern von Editor-Dateien

`EditorTab.save()` kodiert den vollständigen Text vor dem Öffnen einer Ausgabe
als UTF-8. Die bisherige Umwandlung in native Zeilenenden bleibt erhalten.
Qt `QSaveFile` schreibt einen privaten Zwischenstand und übernimmt ihn erst,
wenn Schreiben und `commit()` erfolgreich waren. Der direkte Schreib-Fallback
ist ausdrücklich deaktiviert; bei eingeschränkten Verzeichnisrechten kann das
Speichern deshalb fehlschlagen, obwohl direktes Überschreiben möglich wäre.

Fehler beim Öffnen, Teilwrites, Schreibfehler, ungültiges UTF-8 und ein
fehlgeschlagenes Commit melden einen Fehler und lassen den bisherigen
Dateiinhalt bestehen. Das Dokument bleibt geändert; Schließen und Ausführen
nutzen weiterhin den bestehenden Erfolgsstatus. Geteilte Ansichten werden
erst nach erfolgreichem Speichern gemeinsam als unverändert markiert.
Auch ein bewusst leeres Dokument darf erfolgreich gespeichert werden.

Diese Änderung betrifft lokale Editor-Dateien. Sie ist keine Abnahme von
SFTP-Uploads, Workspace-/Snippet-/Einstellungsspeichern, Datei-Lade-Encoding,
parallelen externen Änderungen, einer In-place-Erhaltung von Hardlinks oder
mehrteiligen Transaktionen. Ein neuer
EXE-Build und Geräte-/Office-/Store-Prüfungen sind nicht Teil der Quelländerung.

API-Verhalten: [Qt-QSaveFile-Dokumentation](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSaveFile.html).
