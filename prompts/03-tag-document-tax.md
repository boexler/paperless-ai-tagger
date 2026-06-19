# Paperless Klassifikation + Steuerprüfung

Bearbeite das Paperless-Dokument mit der ID **{{document_id}}** in **einem Durchlauf** in zwei Phasen:

1. **Phase A — Klassifikation:** Korrespondent, Dokumenttyp, Titel, allgemeine Tags, `ai-tag-document`
2. **Phase B — Steuerprüfung:** steuerliche Relevanz, Steuer-Tags, `ai-tag-tax`

Am Ende **ein** `document_update` (Metadaten + alle Tags) und **eine** `document_note_add` (zwei Abschnitte).

Ziel ist nicht maximale Tag-Anzahl, sondern saubere, nachvollziehbare Einordnung mit möglichst bestehenden Werten.

## MCP-Tools

Verwende ausschließlich diese `paperless-ngx-mcp`-Tool-Namen:

| Aktion | Tool |
| --- | --- |
| Tags auflisten | `tag_list` |
| Tag anlegen | `tag_create` |
| Korrespondenten auflisten | `correspondent_list` |
| Korrespondent anlegen | `correspondent_create` |
| Korrespondent aktualisieren | `correspondent_update` |
| Dokumenttypen auflisten | `document_type_list` |
| Dokumenttyp anlegen | `document_type_create` |
| Dokument lesen | `document_get` |
| Dokument aktualisieren | `document_update` |
| Notiz hinzufügen | `document_note_add` |

## Grundprinzipien

* Bestehende Tags haben Vorrang; niemals entfernen.
* Keine Synonyme oder Duplikate anlegen.
* Neue Tags nur anlegen, wenn kein vorhandenes Tag fachlich passt (max. 5 neue Tags pro Dokument).
* Korrespondent und Dokumenttyp vor Titel und Tags festlegen.
* Bei Unsicherheit in Phase A: `ai-review-tag-document`; in Phase B: `ai-review-tag-tax`.
* Jedes bearbeitete Dokument erhält `ai-tag-document` und `ai-tag-tax`.
* Entscheidungen per Notiz nachvollziehbar dokumentieren.
* In Phase A keine Steuer-Tags setzen — das übernimmt Phase B.

## Kontext aus dem Webhook

* Dokument-ID: `{{document_id}}`
* Titel: `{{doc_title}}`
* Korrespondent: `{{correspondent}}`
* Dokumenttyp: `{{document_type}}`
* URL: `{{doc_url}}`

---

## Phase A — Klassifikation

### A.1 Bestehende Tags laden

Lies alle existierenden Tags mit `tag_list` (`page_size=100`, paginieren bis vollständig).

Merke dir: numerische ID, Name, Bedeutung falls ableitbar.

### A.2 Korrespondenten laden

Lies alle Korrespondenten mit `correspondent_list` (`page_size=100`, paginieren).

Merke dir: ID, Name, `match`, `matching_algorithm` (1=Any, 2=All, 3=Exact, 4=Regex, 5=Fuzzy, 6=Auto), `is_insensitive`.

Korrespondenten mit `matching_algorithm=6` oder leerem `match` sind nicht sauber konfiguriert — Modus „Automatisch“ weder belassen noch neu setzen.

### A.3 Dokumenttypen laden

Lies alle Dokumenttypen mit `document_type_list` (`page_size=100`, paginieren). Merke dir ID und Name.

### A.4 Dokument lesen

`document_get` mit `id={{document_id}}`.

Analysiere: Titel, Korrespondent, Dokumenttyp, Tags, OCR-Text/`content`, Datum, Fristen, Zahlungsziele, Handlungsbedarf.

### A.5 Bestehende Dokument-Tags sichern

Bestehende Tags müssen beim finalen `document_update` wieder mitgegeben werden (`tags` ersetzt die komplette Liste). Nur ergänzen, nie entfernen.

### A.6 Inhalt fachlich einordnen

Bestimme aus Titel, Korrespondent, Dokumenttyp und OCR:

* Was ist das Dokument? Von wem? Welcher Lebensbereich/Vorgang?
* Handlungsbedarf? Unsicherheit? Vollständigkeit/Lesbarkeit?

Dokumenttyp = Art (Rechnung, Vertrag, Bescheid …). Tags = Themen, Kontext, Status, Aktionen. Korrespondent ≠ automatisch Tag.

### A.7 Korrespondent und Dokumenttyp setzen

Merke dir, ob der Korrespondent **von Anfang an plausibel** war (Regex-Nachpflege).

#### Korrespondent — Auswahl-Priorität

1. Vorhandener Korrespondent plausibel → übernehmen, keine Regex-Nachpflege.
2. Leer oder wahrscheinlich falsch → in Liste suchen: zuerst Regex-Treffer (`matching_algorithm=4`), dann Name.
3. Bestehenden wählen, keine Duplikate. Nur bei hoher Sicherheit `correspondent_create`.

**`correspondent_create` Pflicht:** `name`, `match` (Regex aus OCR), `matching_algorithm=4`, `is_insensitive=true` (Standard).

**Regex ableiten:** stabile Anker (Firmenname, USt-IdNr., Domain, Briefkopf); eindeutig halten; Varianten per Alternation `Media\s*Markt|MediaMarkt`.

**`correspondent_update` Nachpflege** (wenn Dokument zuvor keinen passenden Korrespondenten hatte und bestehender zugewiesen wird — **vor** finalem `document_update`):

| Situation | Aktion |
| --- | --- |
| `matching_algorithm=6` oder `match` leer | Update mit `matching_algorithm=4` und `match` aus OCR |
| Regex vorhanden, neue Schreibweise | Alternation erweitern (`\|`), solange eindeutig |
| Regex passt | Kein Update |

Nicht nachpflegen, wenn Korrespondent von Anfang an plausibel war.

#### Dokumenttyp

1. Plausibel → übernehmen. 2. Leer/falsch → in Liste suchen. 3. Bestehenden wählen. 4. Nur bei Sicherheit `document_type_create` mit `name`.

Typische Typen: Rechnung, Vertrag, Bescheid, Schreiben, Kontoauszug, Gehaltsabrechnung, Mahnung, Nachweis, Zertifikat.

#### Unsicherheit

Nicht raten; Wert unverändert lassen; `ai-review-tag-document` setzen; in Notiz nennen.

### A.8 Titel prüfen und ggf. verbessern

Schema: `[Dokumenttyp] – [konkreter Inhalt / Kontext]`

Gute Beispiele: `Rechnung – Stromabschlag Januar 2026`, `Vertrag – Mobilfunk Vodafone`, `Bescheid – Einkommensteuer 2025`, `Kontoauszug – Girokonto Mai 2026`, `Schreiben – Beitragserhöhung Hausratversicherung`, `Nachweis – Zahlung Kfz-Versicherung`, `Mahnung – Offene Rechnung Internetanschluss`.

Schlecht: `scan_2026_06_16.pdf`, `document.pdf`, `IMG_1234`, `Rechnung`, `Brief`, `Unbekannt`, ausschließlich Korrespondentenname (`Telekom`).

Verbesserungsbeispiele: `Rechnung` → `Rechnung – Stromabschlag Januar 2026`; `Scan` → `Bescheid – Einkommensteuer 2025`; `Telekom` → `Rechnung – Mobilfunk Telekom`.

Nur bei Sicherheit ändern. Sonst `ai-review-tag-document` und Begründung in Notiz.

### A.9 Allgemeine Tags auswählen (keine Steuer-Tags)

Wähle primär aus `tag_list`. Reihenfolge: exakt passend → allgemeiner passend → keins → nur bei Bedarf neu.

Keine Tags, die nur den Dokumenttyp wiederholen. In Phase A **keine** Steuer-Tags (`steuerrelevant`, `werbungskosten`, `ai-tag-tax` usw.) — Phase B übernimmt.

Beispiele: Stromrechnung → `Wohnen`, `Strom`, `Finanzen`; Steuerbescheid → `Behörde`, `wichtig` (ohne steuerliche Tag-Namen).

### A.10 `ai-tag-document` und `ai-review-tag-document`

`ai-tag-document` immer setzen (`tag_create` falls nötig, `name="ai-tag-document"`).

`ai-review-tag-document` bei Unsicherheit, wenn mindestens einer der folgenden Fälle zutrifft:

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
* Das Dokument ist rechtlich, finanziell oder vertraglich besonders relevant.
* Es ist unklar, ob ein Original physisch aufbewahrt werden muss.
* Du bist dir bei irgendeiner Einordnung nicht ausreichend sicher.

Steuerliche Relevanz allein ist **kein** Grund für `ai-review-tag-document`.

Für Handlungsbedarf vorhandenes Status-Tag (`todo`, `offen`, `frist`, `bezahlen` …) nutzen, falls vorhanden.

### A.11 Neue Tags restriktiv anlegen

Nur wenn: kein passendes Tag, kein Synonym, wiederverwendbar, nützlich für Suche/Filter.

Nicht anlegen für: Monate, Jahre, Dateiformate, einmalige Produktnamen, reine Korrespondenten-Namen, Synonyme.

Bei Unsicherheit: nicht anlegen, `ai-review-tag-document`, Vorschlag in Notiz.

---

## Phase B — Steuerprüfung

Nutze Ergebnisse aus Phase A (geladene Tags, `document_get`, gesetzte Metadaten). Kein erneutes Laden nötig, außer du brauchst frische Daten.

### B.1 Ziel

Prüfe Einkommensteuer-Relevanz (Werbungskosten, Arbeitsmittel, Fortbildung, Fachliteratur, Reisekosten, Bewerbung, Berufsverband, Homeoffice/Arbeitszimmer, sonstige berufliche Ausgaben).

Berufliche Kontexte:

1. Mechatroniker / Industrieelektroniker / Industriemechaniker
2. Softwareentwickler / IT / EDV-Dienstleistung
3. Grundschullehrerin / Pädagogin (alle Fächer, Klassenleitung)

### B.2 Grundregeln Steuer

* Nur Steuerrelevanz prüfen — **Titel, Korrespondent, Dokumenttyp nicht ändern** (bereits in Phase A).
* Bestehende Tags behalten; Steuer-Tags ergänzen.
* Keine steuerliche Beratung — nur potenzielle Relevanz markieren.
* Keine harte Negativentscheidung, wenn spätere Nachschärfung möglich.
* Kleidung/Textilien nicht automatisch steuerrelevant; im Zweifel `ai-review-tag-tax`.
* Bei Unsicherheit lieber `ai-review-tag-tax` als falsch positiv/negativ.

### B.3 Steuer-Tags

Pflicht (anlegen falls fehlend): `steuerrelevant`, `ai-review-tag-tax`, `ai-tag-tax`.

Optional (nur wenn passend und wiederverwendbar): `werbungskosten`, `arbeitsmittel`, `fortbildung`, `fachliteratur`, `homeoffice`, `arbeitszimmer`, `reisekosten`, `fahrtkosten`, `bewerbung`, `berufsverband`, `softwareentwicklung`, `edv`, `mechatronik`, `industrie`, `schule`, `pädagogik`, `unterrichtsmaterial`, `musik`, `sport`, `kunst`, `sachunterricht`, `förderunterricht`.

Nicht als Standard-Steuer-Tag: `berufskleidung`.

### B.4 Steuerliche Relevanz bewerten

#### A — Steuerlich relevant → `steuerrelevant`

Typische Fälle:

* Rechnung für beruflich genutzte Arbeitsmittel
* Rechnung für Werkzeug, Messgerät, technisches Zubehör oder Fachausstattung
* Rechnung für Computer, Laptop, Monitor, Tastatur, Maus, Drucker, Zubehör
* Rechnung für Software, Lizenzen, Cloud-Dienste, Hosting, Domains oder Entwicklungswerkzeuge
* Rechnung für Fachbücher, Lernmaterial, Unterrichtsmaterial oder pädagogisches Material
* Rechnung für Fortbildung, Kurs, Seminar, Zertifizierung, Prüfung oder Fachkonferenz
* Reisekosten, Hotel, Bahn, Flug, Parken oder Verpflegung bei erkennbarem beruflichem Anlass
* Bewerbungskosten, Bewerbungsfotos, Zeugniskopien, Porto oder Fahrten zu Vorstellungsgesprächen
* Beiträge zu Berufsverbänden, Kammern, Gewerkschaften oder beruflichen Netzwerken
* Kosten für Homeoffice, Arbeitszimmer, Büromaterial oder Büroausstattung
* Nachweise zu beruflicher Nutzung oder Kostenerstattung
* Belege zu Steuerberatung, Lohnsteuerhilfe oder Einkommensteuer

#### B — Möglicherweise relevant → `ai-review-tag-tax`

Typische Fälle:

* Gegenstand kann privat oder beruflich genutzt werden
* Beruflicher Bezug plausibel, aber nicht eindeutig
* Unspezifische Rechnung ohne klare Artikelbeschreibung
* Korrespondent oder Produkt lässt Berufsbezug vermuten, OCR unvollständig
* Fortbildungsbezug möglich, Kursinhalt unklar
* Homeoffice-/Arbeitszimmerbezug möglich, privat mitveranlasst
* Gemischte private und berufliche Positionen
* Rechtliche/steuerliche/finanzielle Themen, konkreter Bezug unklar
* Betrag oder Artikel nicht lesbar; Dokumenttyp passt nicht zum Inhalt
* Kleidung/Schuhe/Textilien möglicherweise beruflich, steuerlich nicht eindeutig
* Kein Steuerbezug erkennbar, Dokumenttyp soll künftig nachgeschärft werden

#### C — Kein klarer Steuerbezug

* `ai-tag-tax` immer setzen
* kein `steuerrelevant`
* `ai-review-tag-tax`, wenn später menschlich nachgeschärft werden soll

Eher privat: Konsum, Lebensmittel, Freizeit, private Kleidung, Haushalt ohne Arbeitszimmer-Bezug, private Unterhaltungselektronik.

### B.5 Berufsfeldbezug

#### Mechatronik / Industrie

Potenziell steuerlich relevante Hinweise:

* **Werkzeug:** Schraubendreher, Zangen, Crimpzange, Abisolierzange, Seitenschneider, Drehmomentschlüssel, Steckschlüsselsatz, Inbusschlüssel, Ratsche, Bohrer, Bits, Gewindeschneider, Feilen
* **Messgeräte:** Messschieber, Bügelmessschraube, Messuhr, Multimeter, Stromzange, Spannungsprüfer, Durchgangsprüfer, Isolationsmessgerät, Prüfgerät
* **Elektro/Zubehör:** Lötstation, Lötkolben, Schrumpfschlauch, Aderendhülsen, Kabelbinder, Klemmen, Steckverbinder, Sensorik, Aktorik, Pneumatik-/Hydraulik-/SPS-Zubehör, Automatisierungstechnik, Maschinenbau-Zubehör, Instandhaltungsbedarf
* **Literatur/Fortbildung:** technische Fachbücher, Tabellenbücher, Normen, VDE-Unterlagen, Meisterschule, Technikerweiterbildung, Staplerschein, Kranschein, Schweißkurs, SPS-/Pneumatik-/Hydraulik-/CAD-Schulung, Arbeitsschutzschulung

**Kleidung/Schutzausrüstung:** nicht automatisch `steuerrelevant`; bei Sicherheitsschuhen, Schutzbrille, Gehörschutz, Helm, Handschuhen → `ai-review-tag-tax`; `steuerrelevant` nur bei eindeutigem Schutz-/Sicherheitsbezug.

Tags: `mechatronik`, `industrie`, `arbeitsmittel`, `fortbildung`, `fachliteratur`, `werbungskosten`.

#### Software / EDV

Potenziell steuerlich relevante Hinweise:

* **Hardware:** Laptop, Computer, PC-Komponenten, Monitor, Tastatur, Maus, Trackball, Grafiktablet, Headset, Mikrofon, Webcam, Dockingstation, USB-Hub, Router, Switch, NAS, Server, SSD, RAM, Drucker, Scanner
* **Dienste/Lizenzen:** Cloud-Dienste, Hosting, Domains, SSL, E-Mail-Hosting, VPN, Softwarelizenzen, IDE, Git/CI/CD, SaaS, PM-/Dokumentations-/Design-/API-/DB-/Test-/Security-Tools
* **Weiterbildung/Büro:** Fachliteratur, Online-Kurse, Zertifizierungen, Konferenzen, Schreibtisch, Bürostuhl, Monitorarm, Arbeitsplatzbeleuchtung, Homeoffice-Ausstattung, Steuerberatung bei selbständiger/nebenberuflicher IT-Tätigkeit, EDV-Projektrechnungen

Tags: `softwareentwicklung`, `edv`, `arbeitsmittel`, `fortbildung`, `fachliteratur`, `homeoffice`, `werbungskosten`.

#### Grundschule / Pädagogik

Potenziell steuerlich relevante Hinweise:

* **Allgemein:** Unterrichtsmaterial, Lehrmittel, Schulbücher, Fachbücher, Arbeitshefte, Lernkarten, Lernspiele, Förder-/Inklusionsmaterial, DaZ-Material, Poster, Stempel, Whiteboard-/Tafelmaterial, Laminiergerät, Toner, Druckerpapier, Ordner, Planer, Lehrerkalender, Stifte, Marker
* **Deutsch:** Fibeln, Lesespiele, Silbenmaterial, Anlautkarten, Rechtschreibmaterial, Klassenlektüre
* **Mathematik:** Rechenrahmen, Rechenplättchen, Steckwürfel, Geometriekörper, Zahlenstrahl, Einmaleins-Material, Uhrzeit-/Geld-Material
* **Sachunterricht:** Experimentiermaterial, Mikroskop, Lupen, Magnetismus-Material, Stromkreis-Bausatz, Globus, Wetterstation, Verkehrserziehungsmaterial
* **Kunst/Werken:** Bastelmaterial, Tonpapier, Farben, Pinsel, Modelliermasse, Werkmaterial
* **Musik:** Noten, Liederbücher, Rhythmusinstrumente, Glockenspiel, Metronom, Musiksoftware
* **Sport:** Bälle, Springseile, Leibchen, Koordinationsleiter, Stoppuhr, Gymnastikbänder, kleine Sportgeräte
* **Religion/Ethik/Soziales:** Bildkarten, Erzählkarten, Kamishibai, Gefühlekarten, Klassenrat-Material
* **Englisch:** Flashcards, Wortkarten, Kinderbücher Englisch, Hörmaterial, Sprachlernspiele
* **Digital:** Tablet, Dokumentenkamera, Beamer-Zubehör, Lernsoftware, Unterrichtsapps, Cloud-Abos mit Unterrichtsbezug
* **Fortbildung:** pädagogische Fortbildung, Erste-Hilfe-Kurs, Inklusion, Diagnostik, Classroom Management, Medienbildung, Fachseminare, Lehrerkongresse
* **Reisen:** Klassenfahrt, Exkursion, Schullandheim, Fortbildungsreise, Bahn/Hotel/ÖPNV mit schulischem Anlass

Tags: `schule`, `pädagogik`, `unterrichtsmaterial`, `arbeitsmittel`, `fortbildung`, `fachliteratur`, `homeoffice`, `werbungskosten`, `musik`, `sport`, `kunst`, `sachunterricht`, `förderunterricht`.

### B.6 Entscheidungslogik

1. Klarer Berufs-/Steuerbezug → `steuerrelevant` + optionale Tags.
2. Möglich, aber unsicher → `ai-review-tag-tax`; `steuerrelevant` nur wenn überwiegend plausibel.
3. Kein klarer Bezug → `ai-tag-tax`, kein `steuerrelevant`; ggf. `ai-review-tag-tax` für Nachschärfung.
4. **Immer** `ai-tag-tax` setzen.
5. Optionale Tags nur wenn existierend oder eindeutig wiederverwendbar.
6. Gemischte Nutzung → `steuerrelevant` wenn plausibel + `ai-review-tag-tax` für Aufteilung.
7. Kleidung/Textilien → nicht automatisch `steuerrelevant`; Schutzbezug nur vorsichtig + Review.
8. Fristen/Mahnungen nur steuerlich relevant, wenn Steuerbezug möglich.

---

## Finale Aktionen

### F.1 `document_update` (einmal)

Finale Tag-Liste aus:

* allen bisher am Dokument vorhandenen Tag-IDs
* allgemeinen Tags aus Phase A
* `ai-tag-document`, `ai-review-tag-document` (falls nötig)
* `ai-tag-tax` (immer)
* `steuerrelevant`, `ai-review-tag-tax` (falls nötig)
* optionalen Steuer-Tags aus Phase B
* neu erstellten Tag-IDs

Parameter:

* `id={{document_id}}`
* `tags` als JSON-Array numerischer IDs
* optional `title`, `correspondent`, `document_type` (nur Phase-A-Änderungen, numerische IDs)

Beispiel: `tags="[1,12,34,56]", title="Rechnung – Stromabschlag Januar 2026", correspondent=42, document_type=7`

`tags` ersetzt die komplette Liste — bestehende Tags zwingend mitgeben. Numerische IDs, nicht Namen.

### F.2 `document_note_add` (einmal, zwei Abschnitte)

Mehrzeilig mit **echten Zeilenumbrüchen** (kein Literal `\n`).

**Abschnitt 1 — Automatische Einordnung:**

* Korrespondent (geändert/plausibel; ggf. Regex angelegt/aktualisiert)
* Dokumenttyp, Titel
* Tags + Begründung
* `ai-tag-document`, `ai-review-tag-document`
* Neue Tags / keine neuen Tags
* optional Handlungsbedarf/Status-Tag

**Abschnitt 2 — Steuerprüfung:**

* Ergebnis (steuerlich relevant / möglicherweise / kein klarer Bezug)
* Steuer-Tags + Begründung
* Beruflicher Kontext
* `ai-tag-tax`, `ai-review-tag-tax`

Beispiel:

```
Automatische Einordnung:
- Korrespondent nicht geändert, plausibel (Stadtwerke).
- Dokumenttyp nicht geändert, plausibel (Rechnung). Titel plausibel, nicht geändert.
- Tags ergänzt: Finanzen, Wohnen, Strom, ai-tag-document. Begründung: Stromrechnung Wohnung.
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde nicht gesetzt: Metadaten plausibel.
- Keine neuen Tags angelegt.

Steuerprüfung:
- Ergebnis: kein klarer Steuerbezug erkannt.
- Tags ergänzt: ai-tag-tax. Begründung: private Stromrechnung ohne Berufsbezug.
- Beruflicher Kontext: keiner.
- ai-tag-tax wurde gesetzt.
- ai-review-tag-tax wurde nicht gesetzt.
```

Beispiel mit Steuerrelevanz:

```
Automatische Einordnung:
- Korrespondent nicht geändert, plausibel (MediaMarkt).
- Dokumenttyp nicht geändert (Rechnung). Titel geändert zu "Rechnung – Monitor Dell U2723QE".
- Tags ergänzt: EDV, ai-tag-document. Begründung: EDV-Hardware-Rechnung.
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde nicht gesetzt.
- Keine neuen Tags angelegt.

Steuerprüfung:
- Ergebnis: steuerlich relevant.
- Tags ergänzt: steuerrelevant, werbungskosten, arbeitsmittel, softwareentwicklung, ai-tag-tax. Begründung: Monitor mit beruflichem Bezug.
- Beruflicher Kontext: Softwareentwicklung / EDV.
- ai-tag-tax wurde gesetzt.
- ai-review-tag-tax wurde nicht gesetzt: Einordnung plausibel.
```

Beispiel mit Review in Phase A:

```
Automatische Einordnung:
- Korrespondent nicht geändert, plausibel (Allianz).
- Dokumenttyp nicht geändert, unklar. Titel nicht geändert.
- Tags ergänzt: Versicherung, Auto, ai-tag-document, ai-review-tag-document. Begründung: vermutlich KFZ-Versicherung.
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde gesetzt: Mensch soll Dokumenttyp und Titel prüfen.
- Keine neuen Tags angelegt.

Steuerprüfung:
- Ergebnis: möglicherweise steuerlich relevant.
- Tags ergänzt: ai-review-tag-tax, ai-tag-tax. Begründung: Versicherungsbezug unklar, kein eindeutiger Werbungskosten-Beleg.
- Beruflicher Kontext: keiner eindeutig.
- ai-tag-tax wurde gesetzt.
- ai-review-tag-tax wurde gesetzt: steuerlichen Bezug prüfen.
```

---

## Entscheidungsregeln

### Dokumenttyp vs. Tag

Dokumenttyp = Form (Rechnung, Vertrag …). Tags = Thema/Kontext/Status (Finanzen, Wohnen, todo, frist …). Begriff nicht doppelt als Tag, wenn bereits Dokumenttyp.

### Korrespondent vs. Tag

Korrespondent ≠ automatisch Tag (`Telekom` → Korrespondent; `Mobilfunk` → Tag falls vorhanden).

### Review vs. Aufgabe

`ai-review-tag-document` / `ai-review-tag-tax` = menschliche Prüfung nötig. Status-Tags (`todo`, `bezahlen` …) = konkreter Handlungsbedarf.

### Wann keine neuen Tags anlegen?

Lege kein neues Tag an, wenn ein vorhandenes allgemeineres Tag fachlich ausreicht (z. B. `Versicherung` statt neu `Hausratversicherung`).

### Wann neue Tags vorschlagen statt anlegen?

Wenn ein Tag sinnvoll wirken könnte, aber Taxonomie unsicher: nicht anlegen, `ai-review-tag-document` setzen, Vorschlag in Notiz (z. B. `Vorschlag: Neues Tag "Pflegeversicherung" prüfen.`).

### Steuer vs. Klassifikation

Allgemeine Tags in Phase A; Steuer-Tags nur in Phase B. Titel mit „Einkommensteuer“ ist erlaubt; steuerliche Tag-Namen gehören in Phase B.

---

## Sicherheitsregeln

* Nur Dokument `{{document_id}}` bearbeiten.
* Keine Dokumente/Tags löschen, keine Massenänderungen.
* Bestehende Tags nie entfernen; max. 5 neue Tags.
* `tag_create` immer mit `name`; `document_update` mit numerischen Tag-IDs.
* `correspondent_create`: immer `match` + `matching_algorithm=4`; nie `6`.
* Regex-Nachpflege bei zugewiesenem Korrespondenten prüfen, wenn zuvor keiner passte.
* Bei Unsicherheit Review-Tags setzen statt falsch klassifizieren.

## Antwortformat

Kurz auf Deutsch:

* Dokument-ID
* Korrespondent, Dokumenttyp, Titel (gesetzt/geändert/unverändert)
* Allgemeine und Steuer-Tags
* `ai-tag-document`, `ai-review-tag-document`, `ai-tag-tax`, `ai-review-tag-tax`
* Ergebnis Steuerprüfung + kurze Begründung
* Neu angelegte Tags/Korrespondenten/Dokumenttypen; Regex-Nachpflege falls vorhanden

Beispiel:

`Dokument {{document_id}}: Korrespondent Stadtwerke (unverändert), Typ Rechnung, Titel unverändert. Tags: Finanzen, Wohnen, Strom, ai-tag-document, ai-tag-tax. Steuer: kein klarer Bezug. ai-review-tag-document und ai-review-tag-tax nicht gesetzt.`
