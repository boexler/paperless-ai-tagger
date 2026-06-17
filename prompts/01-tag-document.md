# Paperless Auto-Tagging

Tagge das Paperless-Dokument mit der ID **{{document_id}}**.

Ziel ist nicht, möglichst viele Tags zu setzen, sondern das Dokument sauber, nachvollziehbar und mit möglichst bestehenden Werten einzuordnen. Dazu gehören Korrespondent, Dokumenttyp, Titel und Tags in einem Durchlauf.

## MCP-Tools

Verwende ausschließlich diese `paperless-ngx-mcp`-Tool-Namen:

| Aktion                 | Tool                   |
| ---------------------- | ---------------------- |
| Tags auflisten         | `tag_list`             |
| Tag anlegen            | `tag_create`           |
| Korrespondenten auflisten | `correspondent_list` |
| Korrespondent anlegen  | `correspondent_create` |
| Dokumenttypen auflisten | `document_type_list`  |
| Dokumenttyp anlegen    | `document_type_create` |
| Dokument lesen         | `document_get`         |
| Dokument aktualisieren | `document_update`      |
| Notiz hinzufügen       | `document_note_add`    |

## Grundprinzipien

* Bestehende Tags haben Vorrang.
* Keine Synonyme oder Duplikate anlegen.
* Bestehende Tags am Dokument niemals entfernen.
* Neue Tags nur anlegen, wenn kein vorhandenes Tag fachlich passt.
* Bei Unsicherheit immer `ai-review-tag-document` setzen.
* Jedes automatisch bearbeitete Dokument erhält `ai-tag-document`.
* Die Entscheidung muss per Notiz nachvollziehbar dokumentiert werden.
* Korrespondent und Dokumenttyp vor Titel und Tags festlegen, damit die Einordnung konsistent bleibt.

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

### 2. Korrespondenten laden

Lies alle existierenden Korrespondenten mit `correspondent_list` aus.

Verwende:

* `page_size=100`

Falls mehr als 100 Korrespondenten vorhanden sind und Pagination unterstützt wird, lade weitere Seiten nach, bis die Liste vollständig ist.

Merke dir für jeden Korrespondenten:

* numerische ID
* Name

### 3. Dokumenttypen laden

Lies alle existierenden Dokumenttypen mit `document_type_list` aus.

Verwende:

* `page_size=100`

Falls mehr als 100 Dokumenttypen vorhanden sind und Pagination unterstützt wird, lade weitere Seiten nach, bis die Liste vollständig ist.

Merke dir für jeden Dokumenttyp:

* numerische ID
* Name

### 4. Dokument lesen

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

### 5. Bestehende Dokument-Tags sichern

Prüfe, welche Tags bereits am Dokument gesetzt sind.

Diese bestehenden Tags müssen beim späteren `document_update` wieder mitgegeben werden, da das Feld `tags` die komplette Tag-Liste ersetzt.

Regel:

* Bestehende Tags behalten
* Nur zusätzliche sinnvolle Tags ergänzen
* Keine vorhandenen Tags entfernen

### 6. Inhalt fachlich einordnen

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

### 7. Korrespondent und Dokumenttyp setzen

Bestimme zuerst Korrespondent und Dokumenttyp, bevor du Titel und Tags festlegst.

#### Korrespondent

1. Wenn der vorhandene Korrespondent fachlich plausibel ist, übernimm ihn.
2. Wenn kein Korrespondent gesetzt ist oder der vorhandene wahrscheinlich falsch ist, suche in der geladenen Korrespondenten-Liste nach einem passenden Eintrag.
3. Wähle einen bestehenden Korrespondenten, wenn der Name fachlich passt. Lege keine Duplikate mit leicht abweichender Schreibweise an.
4. Wenn kein passender Korrespondent existiert und du dir sehr sicher bist, lege ihn mit `correspondent_create` an.

Pflichtparameter bei `correspondent_create`:

* `name="..."`

#### Dokumenttyp

1. Wenn der vorhandene Dokumenttyp fachlich plausibel ist, übernimm ihn.
2. Wenn kein Dokumenttyp gesetzt ist oder der vorhandene wahrscheinlich falsch ist, suche in der geladenen Dokumenttyp-Liste nach einem passenden Eintrag.
3. Wähle einen bestehenden Dokumenttyp, wenn der Name fachlich passt. Lege keine Duplikate mit leicht abweichender Schreibweise an.
4. Wenn kein passender Dokumenttyp existiert und du dir sehr sicher bist, lege ihn mit `document_type_create` an.

Pflichtparameter bei `document_type_create`:

* `name="..."`

#### Unsicherheit

Wenn Korrespondent oder Dokumenttyp unklar sind:

* nicht raten
* vorhandenen Wert unverändert lassen, falls kein sicherer Ersatz existiert
* `ai-review-tag-document` setzen
* Unsicherheit in der Notiz nennen

Typische Dokumenttypen:

* Rechnung
* Vertrag
* Bescheid
* Schreiben
* Kontoauszug
* Gehaltsabrechnung
* Mahnung
* Nachweis
* Zertifikat

### 8. Titel prüfen und ggf. verbessern

Prüfe den vorhandenen Titel des Dokuments.

Der Titel soll kurz, verständlich und ohne Öffnen des Dokuments aussagekräftig sein.

Ein guter Titel beschreibt:

* die Art des Dokuments
* den konkreten Inhalt oder Vorgang
* optional einen relevanten Zeitraum, Vertrag, Gegenstand oder Zweck

Bevorzugtes Schema:

`[Dokumenttyp] – [konkreter Inhalt / Kontext]`

Beispiele:

* `Rechnung – Stromabschlag Januar 2026`
* `Vertrag – Mobilfunk Vodafone`
* `Bescheid – Einkommensteuer 2025`
* `Kontoauszug – Girokonto Mai 2026`
* `Schreiben – Beitragserhöhung Hausratversicherung`
* `Nachweis – Zahlung Kfz-Versicherung`
* `Mahnung – Offene Rechnung Internetanschluss`

Verwende keinen schlechten oder technischen Titel wie:

* `scan_2026_06_16.pdf`
* `document.pdf`
* `IMG_1234`
* `Rechnung`
* `Brief`
* `Unbekannt`
* ausschließlich den Korrespondenten, z. B. `Telekom`

Wenn der vorhandene Titel bereits aussagekräftig ist, lasse ihn unverändert.

Wenn der Titel generisch, technisch oder wenig aussagekräftig ist und du aus OCR-Text, Korrespondent und Dokumenttyp sicher einen besseren Titel ableiten kannst, aktualisiere den Titel mit `document_update`.

Beispiele für generische Titel, die verbessert werden sollen:

* `Rechnung` → `Rechnung – Stromabschlag Januar 2026`
* `Scan` → `Bescheid – Einkommensteuer 2025`
* `Telekom` → `Rechnung – Mobilfunk Telekom`
* `Dokument` → `Vertrag – Hausratversicherung`

Ändere den Titel nur, wenn du dir sicher bist.

Wenn kein eindeutiger Titel ableitbar ist:

* vorhandenen Titel nicht spekulativ ändern
* `ai-review-tag-document` setzen
* Begründung in der Notiz nennen

### 9. Passende Tags auswählen

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

### 10. `ai-tag-document` sicherstellen

Prüfe, ob ein Tag mit dem Namen `ai-tag-document` existiert.

* Falls vorhanden: verwende dessen numerische ID.
* Falls nicht vorhanden: erstelle es mit `tag_create`.

Pflichtparameter:

* `name="ai-tag-document"`

Das Tag `ai-tag-document` muss immer am Dokument gesetzt werden.

### 11. `ai-review-tag-document` prüfen

Prüfe, ob das Tag `ai-review-tag-document` existiert.

* Falls vorhanden: verwende dessen numerische ID, wenn Review nötig ist.
* Falls nicht vorhanden und Review nötig ist: erstelle es mit `tag_create`.

Pflichtparameter:

* `name="ai-review-tag-document"`

Setze `ai-review-tag-document`, wenn mindestens einer der folgenden Fälle zutrifft:

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

`ai-review-tag-document` bedeutet:

> Ein Mensch soll die Metadaten, Tags oder den Inhalt nochmals prüfen.

`ai-review-tag-document` bedeutet nicht automatisch, dass eine Aufgabe erledigt werden muss. Für tatsächlichen Handlungsbedarf soll ein vorhandenes passendes Status-Tag verwendet werden, z. B. `todo`, `offen`, `frist`, `bezahlen` oder ähnlich, sofern vorhanden.

### 12. Neue Tags nur restriktiv anlegen

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
* `ai-review-tag-document` setzen
* Vorschlag in der Notiz dokumentieren

### 13. Dokument aktualisieren

Erstelle die finale Tag-Liste aus:

* allen bereits am Dokument vorhandenen Tag-IDs
* allen zusätzlich ausgewählten bestehenden Tag-IDs
* neu erstellten Tag-IDs, falls wirklich erforderlich
* `ai-tag-document`
* `ai-review-tag-document`, falls Review nötig ist

Entferne keine bestehenden Tags.

Rufe anschließend `document_update` auf.

Parameter:

* `id={{document_id}}`
* `tags` als JSON-Array aller numerischen Tag-IDs
* optional `title`, wenn der Titel sicher verbessert werden soll
* optional `correspondent`, wenn der Korrespondent sicher gesetzt oder geändert werden soll (numerische ID)
* optional `document_type`, wenn der Dokumenttyp sicher gesetzt oder geändert werden soll (numerische ID)

Beispiel nur mit Tags:

`tags="[1,12,34,56]"`

Beispiel mit Tags und Titel:

`tags="[1,12,34,56]", title="Rechnung – Stromabschlag Januar 2026"`

Beispiel mit Tags, Titel, Korrespondent und Dokumenttyp:

`tags="[1,12,34,56]", title="Rechnung – Stromabschlag Januar 2026", correspondent=42, document_type=7`

Wichtig:

* `tags` ersetzt die komplette Tag-Liste des Dokuments.
* Deshalb müssen bestehende Tags zwingend wieder mitgegeben werden.
* Verwende numerische IDs, nicht Namen.
* Ändere Titel, Korrespondent und Dokumenttyp nur bei hoher Sicherheit.
* Keine Metadatenänderung darf dazu führen, dass vorhandene Tags entfernt werden.

### 14. Notiz hinzufügen

Hänge mit `document_note_add` eine kurze deutsche Notiz an das Dokument an.

Parameter:

* `id={{document_id}}`
* `note="..."`

Die Notiz soll die automatische Entscheidung nachvollziehbar dokumentieren. Sie soll kurz, sachlich und prüfbar sein.

Die Notiz muss enthalten:

* ob der Korrespondent geändert wurde
* falls der Korrespondent geändert wurde: alter und neuer Korrespondent
* falls der Korrespondent nicht geändert wurde: kurze Einschätzung, ob der vorhandene Korrespondent plausibel war
* ob der Dokumenttyp geändert wurde
* falls der Dokumenttyp geändert wurde: alter und neuer Dokumenttyp
* falls der Dokumenttyp nicht geändert wurde: kurze Einschätzung, ob der vorhandene Dokumenttyp plausibel war
* ob der Titel geändert wurde
* falls der Titel geändert wurde: alter und neuer Titel
* falls der Titel nicht geändert wurde: kurze Einschätzung, ob der vorhandene Titel plausibel war
* gesetzte oder ergänzte Tags
* kurze Begründung für die Tag-Auswahl
* ob `ai-tag-document` gesetzt wurde
* ob `ai-review-tag-document` gesetzt wurde
* falls `ai-review-tag-document` gesetzt wurde: konkrete Gründe
* falls neue Tags angelegt wurden: Name und Begründung
* falls keine neuen Tags angelegt wurden: Hinweis, dass vorhandene Tags bevorzugt wurden
* falls ein Handlungsbedarf erkennbar ist: Hinweis auf gesetztes Status- oder Aufgaben-Tag
* falls ein Handlungsbedarf vermutet, aber nicht sicher erkannt wird: `ai-review-tag-document` setzen und Grund nennen

Wenn kein Review nötig ist, muss die Notiz klar sagen, warum `ai-review-tag-document` nicht gesetzt wurde.

Wenn Review nötig ist, muss die Notiz klar sagen, was ein Mensch prüfen soll.

#### Formatregeln

* Übergebe die Notiz **mehrzeilig** mit **echten Zeilenumbrüchen** im `note`-Parameter.
* Kein Fließtext in einer Zeile.
* Schreibe nicht den Literaltext `\n` in die Notiz — verwende echte Zeilenumbrüche.
* Zeile 1: Überschrift `Automatische Einordnung:`
* Folgezeilen: je ein Bullet mit `- ` pro Themenblock in dieser Reihenfolge:
  * Korrespondent
  * Dokumenttyp
  * Titel
  * Tags + Begründung
  * `ai-tag-document`
  * `ai-review-tag-document`
  * Neue Tags / keine neuen Tags
  * optional: Handlungsbedarf / Status-Tag

Bevorzugtes Format der Notiz:

```
Automatische Einordnung:
- Korrespondent [geändert/nicht geändert, plausibel/unklar, ggf. alter und neuer Wert].
- Dokumenttyp [geändert/nicht geändert, plausibel/unklar, ggf. alter und neuer Wert].
- Titel [geändert/nicht geändert, plausibel/unklar, ggf. alter und neuer Wert].
- Tags ergänzt: [Tag-Liste]. Begründung: [kurze Begründung].
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde [gesetzt/nicht gesetzt]: [Grund].
- [Neue Tags angelegt: … / Keine neuen Tags angelegt.]
- [optional: Handlungsbedarf / Status-Tag]
```

Beispiele:

```
Automatische Einordnung:
- Korrespondent nicht geändert, plausibel (eBay - saturn, Media Markt E-Business GmbH/Saturn).
- Dokumenttyp nicht geändert, plausibel (Rechnung). Titel geändert von "Rechnung zu deiner Bestellung (257396575)" zu "Rechnung – Apple iPad 10.9 128GB (Bestellung 257396575)".
- Tags ergänzt: EDV, ai-tag-document. Begründung: Saturn/eBay-Rechnung für Apple iPad, bereits per Onlinezahlung beglichen (Restbetrag 0,00 EUR).
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde nicht gesetzt: Korrespondent, Dokumenttyp, OCR-Inhalt und Produkt eindeutig erkennbar, kein Handlungsbedarf.
- Keine neuen Tags angelegt.
```

```
Automatische Einordnung:
- Korrespondent nicht geändert, plausibel (Stadtwerke).
- Dokumenttyp nicht geändert, plausibel (Rechnung).
- Titel plausibel, nicht geändert.
- Tags ergänzt: Finanzen, Wohnen, Strom, ai-tag-document. Begründung: Stromrechnung für Wohnung erkennbar.
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde nicht gesetzt: Metadaten und OCR-Inhalt sind plausibel.
- Keine neuen Tags angelegt.
```

```
Automatische Einordnung:
- Korrespondent nicht geändert, plausibel (Allianz).
- Dokumenttyp nicht geändert, unklar.
- Titel nicht geändert, da kein eindeutigerer Titel sicher ableitbar war.
- Tags ergänzt: Versicherung, Auto, ai-tag-document, ai-review-tag-document. Begründung: Vermutlich KFZ-Versicherung.
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde gesetzt: Mensch soll Dokumenttyp und Titel prüfen.
- Keine neuen Tags angelegt.
```

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

`ai-review-tag-document` bedeutet:

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
* `ai-review-tag-document` setzen
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
* Bei Unsicherheit lieber `ai-review-tag-document` setzen als falsch klassifizieren.
* Antworte auf Deutsch mit einer kurzen Zusammenfassung der gesetzten Metadaten.

## Antwortformat

Antworte kurz auf Deutsch.

Die Antwort soll enthalten:

* Dokument-ID
* Korrespondent und Dokumenttyp (gesetzt, geändert oder unverändert)
* gesetzte oder ergänzte Tags
* ob `ai-tag-document` gesetzt wurde
* ob `ai-review-tag-document` gesetzt wurde
* kurze Begründung
* Hinweis auf neu erstellte Tags, Korrespondenten oder Dokumenttypen, falls vorhanden

Beispiel:

`Dokument {{document_id}} wurde geprüft und aktualisiert. Korrespondent: Stadtwerke (unverändert). Dokumenttyp: Rechnung (unverändert). Ergänzte Tags: Finanzen, Wohnen, Strom, ai-tag-document. ai-review-tag-document wurde nicht gesetzt, da Titel, Korrespondent, Dokumenttyp und OCR-Inhalt plausibel zusammenpassen. Es wurden keine neuen Tags angelegt.`
