# Paperless Auto-Tagging

Tagge das Paperless-Dokument mit der ID **{{document_id}}**.

Ziel ist nicht, möglichst viele Tags zu setzen, sondern das Dokument sauber, nachvollziehbar und mit möglichst bestehenden Werten einzuordnen.

## MCP-Tools

Verwende ausschließlich diese `paperless-ngx-mcp`-Tool-Namen:

| Aktion                 | Tool                |
| ---------------------- | ------------------- |
| Tags auflisten         | `tag_list`          |
| Tag anlegen            | `tag_create`        |
| Dokument lesen         | `document_get`      |
| Dokument aktualisieren | `document_update`   |
| Notiz hinzufügen       | `document_note_add` |

## Grundprinzipien

* Bestehende Tags haben Vorrang.
* Keine Synonyme oder Duplikate anlegen.
* Bestehende Tags am Dokument niemals entfernen.
* Neue Tags nur anlegen, wenn kein vorhandenes Tag fachlich passt.
* Bei Unsicherheit immer `needs-review` setzen.
* Jedes automatisch bearbeitete Dokument erhält `ai-tagged`.
* Die Entscheidung muss per Notiz nachvollziehbar dokumentiert werden.

## Kontext aus dem Webhook

* Dokument-ID: `{{document_id}}`
* Titel: `{{doc_title}}`
* Korrespondent: `{{correspondent}}`
* Dokumenttyp: `{{document_type}}`
* URL: `{{doc_url}}`

## Vorgehen

### 1. Bestehende Tags laden

Lies zuerst alle existierenden Tags mit `tag_list` aus.

Verwende:

* `page_size=100`

Falls mehr als 100 Tags vorhanden sind und Pagination unterstützt wird, lade weitere Seiten nach, bis die Tag-Liste vollständig ist.

Merke dir für jedes Tag:

* numerische ID
* Name
* Bedeutung aus dem Namen, falls eindeutig ableitbar

### 2. Dokument lesen

Lies das Dokument mit `document_get`.

Parameter:

* `id={{document_id}}`

Analysiere insbesondere:

* vorhandener Titel
* vorhandener Korrespondent
* vorhandener Dokumenttyp
* vorhandene Tags
* OCR-Text / `content`
* Dokumentdatum, falls vorhanden
* erkennbare Fristen, Zahlungsziele oder Handlungsbedarfe

### 3. Bestehende Dokument-Tags sichern

Prüfe, welche Tags bereits am Dokument gesetzt sind.

Diese bestehenden Tags müssen beim späteren `document_update` wieder mitgegeben werden, da das Feld `tags` die komplette Tag-Liste ersetzt.

Regel:

* Bestehende Tags behalten
* Nur zusätzliche sinnvolle Tags ergänzen
* Keine vorhandenen Tags entfernen

### 4. Inhalt fachlich einordnen

Bestimme aus Titel, Korrespondent, Dokumenttyp und OCR-Text:

* Was ist das Dokument?
* Von wem stammt es?
* Zu welchem Lebensbereich oder Vorgang gehört es?
* Gibt es einen Handlungsbedarf?
* Gibt es Unsicherheit bei der Klassifikation?
* Ist das Dokument vollständig und plausibel lesbar?

Berücksichtige dabei:

* Der Dokumenttyp beschreibt die Art des Dokuments, z. B. Rechnung, Vertrag, Bescheid, Schreiben.
* Tags beschreiben Themen, Kontexte, Status oder Aktionen.
* Der Korrespondent ist nicht automatisch ein Tag, außer es gibt dafür bereits bewusst ein passendes Tag.

### 5. Passende Tags auswählen

Wähle Tags primär aus der bestehenden Tag-Liste.

Bevorzuge in dieser Reihenfolge:

1. Bereits vorhandenes exakt passendes Tag
2. Bereits vorhandenes allgemeineres, aber fachlich korrektes Tag
3. Kein zusätzliches Tag
4. Nur bei echtem Bedarf ein neues Tag

Setze nur Tags, die für Suche, Filterung, Status oder spätere Bearbeitung nützlich sind.

Vermeide Tags, die lediglich den Dokumenttyp wiederholen.

Beispiele:

* Wenn Dokumenttyp `Rechnung` ist, nicht zusätzlich ein Tag `Rechnung` setzen, außer dieses Tag existiert bereits als bewusst genutztes Prozess-Tag.
* Bei einer Stromrechnung eher Tags wie `Wohnen`, `Strom`, `Finanzen` verwenden, sofern vorhanden.
* Bei einem Steuerbescheid eher Tags wie `Steuern`, `Behörde`, `wichtig` verwenden, sofern vorhanden.
* Bei einem Vertrag eher Tags wie `Verträge`, `wichtig`, `original-aufbewahren` verwenden, sofern vorhanden.

### 6. `ai-tagged` sicherstellen

Prüfe, ob ein Tag mit dem Namen `ai-tagged` existiert.

* Falls vorhanden: verwende dessen numerische ID.
* Falls nicht vorhanden: erstelle es mit `tag_create`.

Pflichtparameter:

* `name="ai-tagged"`

Das Tag `ai-tagged` muss immer am Dokument gesetzt werden.

### 7. `needs-review` prüfen

Prüfe, ob das Tag `needs-review` existiert.

* Falls vorhanden: verwende dessen numerische ID, wenn Review nötig ist.
* Falls nicht vorhanden und Review nötig ist: erstelle es mit `tag_create`.

Pflichtparameter:

* `name="needs-review"`

Setze `needs-review`, wenn mindestens einer der folgenden Fälle zutrifft:

* Titel wirkt unvollständig, generisch oder nicht aussagekräftig.
* Korrespondent ist leer, unklar oder wahrscheinlich falsch.
* Dokumenttyp ist leer, unklar oder wahrscheinlich falsch.
* Es gibt mehrere plausible Dokumenttypen.
* Es gibt mehrere plausible Tags und keine eindeutige Auswahl.
* Ein sinnvoller Tag fehlt in der vorhandenen Tag-Liste.
* Ein neuer Tag müsste angelegt werden.
* OCR-Text ist schlecht, unvollständig oder widersprüchlich.
* Das Dokument wirkt abgeschnitten, unvollständig oder schlecht lesbar.
* Das Datum ist unklar oder offensichtlich falsch.
* Es besteht Duplikatverdacht.
* Das Dokument enthält eine Frist, Mahnung, Kündigung, Zahlungsaufforderung oder einen möglichen Handlungsbedarf.
* Das Dokument ist rechtlich, steuerlich, finanziell oder vertraglich besonders relevant.
* Es ist unklar, ob ein Original physisch aufbewahrt werden muss.
* Du bist dir bei irgendeiner Einordnung nicht ausreichend sicher.

`needs-review` bedeutet:

> Ein Mensch soll die Metadaten, Tags oder den Inhalt nochmals prüfen.

`needs-review` bedeutet nicht automatisch, dass eine Aufgabe erledigt werden muss. Für tatsächlichen Handlungsbedarf soll ein vorhandenes passendes Status-Tag verwendet werden, z. B. `todo`, `offen`, `frist`, `bezahlen` oder ähnlich, sofern vorhanden.

### 8. Neue Tags nur restriktiv anlegen

Erstelle neue Tags nur, wenn alle folgenden Bedingungen erfüllt sind:

* Kein vorhandenes Tag passt fachlich.
* Das neue Tag ist kein Synonym eines vorhandenen Tags.
* Das neue Tag beschreibt keinen einmaligen Spezialfall.
* Das neue Tag wird voraussichtlich wiederverwendet.
* Das neue Tag ist für Suche, Filterung oder Prozesssteuerung nützlich.

Maximal 5 neue Tags pro Dokument.

Lege keine neuen Tags an für:

* einzelne Monate
* einzelne Jahre
* Dateiformate
* reine Dateiquellen
* einmalige Produktnamen
* reine Korrespondenten-Namen
* Begriffe, die bereits durch Dokumenttyp, Titel oder Korrespondent abgedeckt sind
* Synonyme vorhandener Tags

Wenn ein neuer Tag fachlich sinnvoll wäre, aber du unsicher bist:

* Tag nicht anlegen
* `needs-review` setzen
* Vorschlag in der Notiz dokumentieren

### 9. Korrespondent und Dokumenttyp

Ergänze oder ändere Korrespondent und Dokumenttyp nur, wenn das verwendete MCP-Tool dies eindeutig unterstützt und du dir sehr sicher bist.

Wenn Korrespondent oder Dokumenttyp unklar sind:

* nicht raten
* `needs-review` setzen
* Unsicherheit in der Notiz nennen

Wenn der vorhandene Dokumenttyp fachlich plausibel ist, lasse ihn unverändert.

Wenn der vorhandene Korrespondent fachlich plausibel ist, lasse ihn unverändert.

### 10. Tags am Dokument aktualisieren

Erstelle die finale Tag-Liste aus:

* allen bereits am Dokument vorhandenen Tag-IDs
* allen zusätzlich ausgewählten bestehenden Tag-IDs
* neu erstellten Tag-IDs, falls wirklich erforderlich
* `ai-tagged`
* `needs-review`, falls Review nötig ist

Entferne keine bestehenden Tags.

Rufe anschließend `document_update` auf.

Parameter:

* `id={{document_id}}`
* `tags` als JSON-Array aller numerischen Tag-IDs

Beispiel:

`tags="[1,12,34,56]"`

Wichtig:

* `tags` ersetzt die komplette Tag-Liste des Dokuments.
* Deshalb müssen bestehende Tags zwingend wieder mitgegeben werden.
* Verwende numerische Tag-IDs, nicht Tag-Namen.

### 11. Notiz hinzufügen

Hänge mit `document_note_add` eine kurze deutsche Notiz an.

Parameter:

* `id={{document_id}}`
* `note="..."`

Die Notiz muss enthalten:

* gesetzte oder ergänzte Tags
* kurze Begründung
* ob `needs-review` gesetzt wurde
* falls `needs-review` gesetzt wurde: konkrete Gründe
* falls neue Tags angelegt wurden: Name und Begründung
* falls keine neuen Tags angelegt wurden: Hinweis, dass vorhandene Tags bevorzugt wurden

Beispiel für eine Notiz:

`Automatische Einordnung: Tags ergänzt: Finanzen, Wohnen, Strom, ai-tagged. Begründung: Das Dokument wirkt wie eine Stromrechnung für die Wohnung. needs-review wurde nicht gesetzt, da Titel, Korrespondent, Dokumenttyp und OCR-Inhalt plausibel sind.`

Beispiel bei Unsicherheit:

`Automatische Einordnung: Tags ergänzt: Versicherung, Auto, ai-tagged, needs-review. Begründung: Das Dokument betrifft vermutlich eine KFZ-Versicherung. needs-review wurde gesetzt, weil der Dokumenttyp unklar ist und geprüft werden sollte, ob zusätzlich ein Status-Tag oder ein Aufbewahrungshinweis nötig ist.`

## Entscheidungsregeln

### Dokumenttyp vs. Tag

Der Dokumenttyp beschreibt die Form des Dokuments.

Beispiele:

* Rechnung
* Vertrag
* Bescheid
* Schreiben
* Kontoauszug
* Gehaltsabrechnung
* Mahnung
* Nachweis
* Zertifikat

Tags beschreiben Thema, Kontext, Status oder Aktion.

Beispiele:

* Steuern
* Finanzen
* Wohnen
* Auto
* Gesundheit
* Versicherung
* Arbeit
* wichtig
* todo
* offen
* frist
* original-aufbewahren

Wenn ein Begriff bereits als Dokumenttyp verwendet wird, lege ihn nicht zusätzlich als neues Tag an, außer das Tag existiert bereits und wird bewusst genutzt.

### Korrespondent vs. Tag

Der Korrespondent ist die Organisation oder Person, von der das Dokument stammt oder mit der der Vorgang geführt wird.

Lege Korrespondenten-Namen nicht automatisch als neue Tags an.

Beispiel:

* `Telekom` ist eher Korrespondent.
* `Mobilfunk` oder `Internet` kann ein Tag sein, falls vorhanden.

### Review vs. Aufgabe

`needs-review` bedeutet:

* Die automatische Einordnung soll kontrolliert werden.

Ein Aufgaben- oder Status-Tag bedeutet:

* Es muss inhaltlich etwas erledigt werden.

Wenn ein vorhandenes Aufgaben-Tag wie `todo`, `offen`, `bezahlen`, `frist` oder ähnlich existiert, setze es zusätzlich nur dann, wenn aus dem Dokument tatsächlich ein Handlungsbedarf hervorgeht.

Beispiele für Handlungsbedarf:

* Rechnung muss bezahlt werden.
* Schreiben muss beantwortet werden.
* Frist muss überwacht werden.
* Unterlagen müssen nachgereicht werden.
* Vertrag muss gekündigt oder geprüft werden.
* Bescheid muss fachlich geprüft werden.

### Wann keine neuen Tags anlegen?

Lege kein neues Tag an, wenn ein vorhandenes allgemeineres Tag fachlich ausreicht.

Beispiel:

* Vorhanden: `Versicherung`
* Dokument: Hausratversicherung
* Ergebnis: `Versicherung` verwenden
* Kein neues Tag `Hausratversicherung` anlegen, außer dieser Bereich wird regelmäßig separat gefiltert und es gibt noch kein passendes spezifisches Tag.

### Wann neue Tags vorschlagen statt anlegen?

Wenn ein neues Tag sinnvoll wirken könnte, aber du nicht sicher bist, ob es dauerhaft in die Taxonomie passt:

* nicht anlegen
* `needs-review` setzen
* Vorschlag in der Notiz nennen

Beispiel:

`Vorschlag: Neues Tag "Pflegeversicherung" prüfen. Begründung: Das Dokument passt nur teilweise zu bestehenden Tags und könnte wiederkehrend auftreten.`

## Sicherheitsregeln

* Keine Dokumente löschen.
* Keine Tags löschen.
* Keine Massenänderungen durchführen.
* Nur das Dokument mit der ID `{{document_id}}` bearbeiten.
* Keine vorhandenen Tags entfernen.
* Keine Synonyme oder Duplikate erzeugen.
* Maximal 5 neue Tags pro Dokument.
* Bei `tag_create` immer den Parameter `name` setzen.
* `tag_create` niemals ohne `name` oder mit leerem Namen aufrufen.
* Bei `document_update` das Feld `tags` als JSON-Array numerischer IDs übergeben.
* Bei Unsicherheit lieber `needs-review` setzen als falsch klassifizieren.
* Antworte auf Deutsch mit einer kurzen Zusammenfassung der gesetzten Metadaten.

## Antwortformat

Antworte kurz auf Deutsch.

Die Antwort soll enthalten:

* Dokument-ID
* gesetzte oder ergänzte Tags
* ob `ai-tagged` gesetzt wurde
* ob `needs-review` gesetzt wurde
* kurze Begründung
* Hinweis auf neu erstellte Tags, falls vorhanden

Beispiel:

`Dokument {{document_id}} wurde geprüft und aktualisiert. Ergänzte Tags: Finanzen, Wohnen, Strom, ai-tagged. needs-review wurde nicht gesetzt, da Titel, Korrespondent, Dokumenttyp und OCR-Inhalt plausibel zusammenpassen. Es wurden keine neuen Tags angelegt.`