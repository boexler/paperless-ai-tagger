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
* Neue Tags nur anlegen, wenn kein vorhandenes Tag fachlich passt (max. 2 neue Tags pro Dokument).
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

#### Titelbildung

Grundschema:

`[Konkrete Dokumentart] – [Hauptgegenstand] – [optionaler Kontext oder Referenz]`

Die konkrete Dokumentart ist der ausgewählte Paperless-Dokumenttyp oder eine eindeutig erkennbare, fachlich präzisere Unterart dieses Typs.

Eine Unterart nur verwenden, wenn sie eindeutig aus Überschrift, Betreff oder Inhalt hervorgeht. Keine neuen Synonyme oder Dokumentarten erfinden. Ist keine Unterart sicher erkennbar, den Namen des Paperless-Dokumenttyps verwenden.

Maximal drei Bestandteile verwenden und mit ` – ` trennen. Der zweite Bestandteil ist erforderlich. Der dritte ist nur zu ergänzen, wenn er das Dokument sinnvoll unterscheidet.

**Korrespondent nie im Titel.** Der Absender steckt bereits im Metadatum „Korrespondent“ und erscheint im Dateinamen — ihn im Titel zu wiederholen ist redundant (`… – Telekom`, `… – E.ON`, `… – Kirchner GmbH` sind falsch).

Der Korrespondent allein ist kein gültiger Hauptgegenstand. Teil 2 muss der konkrete Inhalt sein (Produkt, Leistung, Zeitraum, Vertragsgegenstand) — nicht eine vage Warengruppe wie „Haushaltsartikel“, wenn Artikel/Marken erkennbar sind. Teil 3 nur für unterscheidende Referenzen (Bestell-/Rechnungsnummer, Monat/Jahr, Verbrauchsstelle), nie für den Korrespondenten.

Schlechte Titel ändern nur bei Sicherheit; sonst `ai-review-tag-document` und Begründung in Notiz.

Gut: `Rechnung – Stromabschlag – Januar 2026`, `Stromrechnung – Jahresabrechnung 2023/24`, `Rechnung – Festool Akku-Dämmstoffsäge ISC 240 EB-Basic`, `Bescheid – Einkommensteuer 2025`, `Kontoauszug – Girokonto – Mai 2026`, `Rechnung – Miniaturkabel Litze LIFY – RE-133101`.

Schlecht: `scan_2026_06_16.pdf`, `Rechnung`, `Brief`, `Telekom`, `Rechnung – Dokument – PDF`, `Rechnung – Telekom`, `Stromrechnung – Abrechnung 2023/24 – E.ON`, `Rechnung – Küchen- und Haushaltsartikel – Bestellung 123`.

Verbesserungsbeispiele: `Rechnung` → `Rechnung – Stromabschlag – Januar 2026`; `Scan` → `Bescheid – Einkommensteuer 2025`; `Telekom` → `Rechnung – Mobilfunk – Januar 2026`; `… – E.ON` → `Stromrechnung – Jahresabrechnung 2023/24`.

### A.8b Datum prüfen und ggf. korrigieren (`created`)

Prüfe das Paperless-Feld `created` (Belegdatum) gegen den OCR-Text.

* **Behalten**, wenn das aktuelle Datum mit dem besten Belegdatum im OCR übereinstimmt oder kein sicheres Belegdatum erkennbar ist.
* **Korrigieren** (`document_update` mit `created` als `YYYY-MM-DD`) nur bei hoher Sicherheit — OCR liefert ein klar besseres Belegdatum als der aktuelle Wert (falsch, fehlend oder unplausibel).
* Bei Unsicherheit: Datum unverändert lassen, `ai-review-tag-document` setzen, in der Notiz nennen. **Kein Datum erfinden**, wenn der OCR keinen Beleg dafür hergibt.

Priorität: Rechnungs-/Briefdatum → Leistungs-/Registrierungsdatum → sonstige explizite Belegdaten. Ignoriere Aktenzeichen/Referenzcodes (z. B. `4.20.01-ABR…`), Telefonnummern und Scan-/Upload-Zeit.

Beispiel: `created=2020-01-04`, OCR zeigt Briefdatum `17.12.2024` → `created=2024-12-17` setzen.

### A.9 Allgemeine Tags auswählen (keine Steuer-Tags)

Wähle primär aus `tag_list`. Reihenfolge: exakt passend → allgemeiner passend → keins → nur bei Bedarf neu.

Keine Tags, die nur den Dokumenttyp wiederholen. In Phase A **keine** Steuer-Tags (`steuerrelevant`, `ai-tag-tax`, `ai-review-tag-tax`) — Phase B übernimmt.

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

Nur wenn: kein passendes Tag, kein Synonym, wiederverwendbar, nützlich für Suche/Filter. Maximal 2 neue Tags pro Dokument.

Nicht anlegen für: Monate, Jahre, Dateiformate, einmalige Produktnamen, reine Korrespondenten-Namen, Synonyme.

Bei Unsicherheit: nicht anlegen, `ai-review-tag-document`, Vorschlag in Notiz.

---

## Phase B — Steuerprüfung

Nutze Ergebnisse aus Phase A (geladene Tags, `document_get`, gesetzte Metadaten). Kein erneutes Laden nötig, außer du brauchst frische Daten.

### B.1 Ziel

Prüfe, ob das Dokument eine **beruflich absetzbare Ausgabe** belegt (Werbungskosten o. Ä.: Arbeitsmittel, Fortbildung, Fachliteratur, Reisekosten, Bewerbung, Berufsverband, Homeoffice/Arbeitszimmer, sonstige berufliche Ausgaben). Ein Einkommensteuerbescheid allein ist keine absetzbare Ausgabe.

Berufliche Kontexte:

1. Mechatroniker / Industrieelektroniker / Industriemechaniker
2. Softwareentwickler / IT / EDV-Dienstleistung
3. Grundschullehrerin / Pädagogin (alle Fächer, Klassenleitung)

### B.2 Grundregeln Steuer

* Nur Steuerrelevanz prüfen — **Titel, Korrespondent, Dokumenttyp nicht ändern** (bereits in Phase A).
* Bestehende Tags behalten; bei Relevanz `steuerrelevant` ergänzen.
* **Einziges fachliches Steuer-Tag:** `steuerrelevant`. Keine Untertags (`werbungskosten`, `arbeitsmittel`, `fortbildung`, Berufsfeld-Tags usw.) anlegen oder setzen — alles Absetzbare nur mit `steuerrelevant` markieren.
* **`steuerrelevant` bedeutet nur:** Beleg einer potenziell **absetzbaren Ausgabe** (typisch Werbungskosten / berufliche Aufwendungen). Nicht jedes steuerbezogene Dokument.
* **Nicht** `steuerrelevant`: Einkommensteuerbescheid, Festsetzung, Steuererklärung, reine Steuerkorrespondenz/Bescheide ohne Ausgabebeleg, Kontoauszüge ohne absetzbare Position.
* Keine steuerliche Beratung — nur potenzielle Absetzbarkeit markieren.
* Keine harte Negativentscheidung, wenn spätere Nachschärfung möglich.
* Kleidung/Textilien nicht automatisch steuerrelevant; im Zweifel `ai-review-tag-tax`.
* Bei Unsicherheit lieber `ai-review-tag-tax` als falsch positiv/negativ.

### B.3 Steuer-Tags

Nur diese Steuer-/Prozess-Tags (anlegen falls fehlend): `steuerrelevant`, `ai-review-tag-tax`, `ai-tag-tax`.

Keine weiteren Steuer-Untertags anlegen oder setzen.

### B.4 Steuerliche Relevanz bewerten

#### Transport (Lehrkraft)

Gegenstände zum Transport/Organisation von Unterrichtsmaterial oder Dienstgeräten können absetzbar sein. Notebookfach = zusätzlicher Hinweis, keine Voraussetzung. Mode-/Reise-Optik schließt berufliche Nutzung nicht aus. Plausibel → `steuerrelevant`; unsicher → `ai-review-tag-tax`. Nicht ablehnen mit „nur Tasche“/„nur Notebookfach“. Eher privat: reines Reise-/Modeprodukt ohne Schul-/Arbeitsbezug.

#### A — Steuerlich relevant → `steuerrelevant`

Typische Fälle (Ausgabebelege mit erkennbarem beruflichem Nutzen):

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
* Rechnung/Honorar für Steuerberatung oder Lohnsteuerhilfe (Ausgabebeleg) — **nicht** der Steuerbescheid selbst

#### B — Möglicherweise relevant → `ai-review-tag-tax`

Typische Fälle:

* Gegenstand kann privat oder beruflich genutzt werden
* Beruflicher Bezug plausibel, aber nicht eindeutig
* Unspezifische Rechnung ohne klare Artikelbeschreibung
* Korrespondent oder Produkt lässt Berufsbezug vermuten, OCR unvollständig
* Fortbildungsbezug möglich, Kursinhalt unklar
* Homeoffice-/Arbeitszimmerbezug möglich, privat mitveranlasst
* Gemischte private und berufliche Positionen
* Rechtliche/finanzielle Themen, konkreter Absetzungsbezug unklar
* Betrag oder Artikel nicht lesbar; Dokumenttyp passt nicht zum Inhalt
* Kleidung/Schuhe/Textilien möglicherweise beruflich, steuerlich nicht eindeutig
* Transportmittel für Unterrichtsmaterial — beruflicher Zweck plausibel, Beleg unklar
* Kein Steuerbezug erkennbar, Dokumenttyp soll künftig nachgeschärft werden

#### C — Kein klarer Steuerbezug

* `ai-tag-tax` immer setzen
* kein `steuerrelevant`
* `ai-review-tag-tax`, wenn später menschlich nachgeschärft werden soll

Eher privat / nicht absetzbar hier: Konsum, Lebensmittel, Freizeit, private Kleidung, Haushalt ohne Arbeitszimmer-Bezug, private Unterhaltungselektronik; außerdem **Einkommensteuerbescheid**, Festsetzung, Steuererklärung und reine Steuerkorrespondenz ohne Ausgabebeleg.

### B.5 Berufsfeldbezug

#### Mechatronik / Industrie

Potenziell steuerlich relevante Hinweise:

* **Werkzeug:** Schraubendreher, Zangen, Crimpzange, Abisolierzange, Seitenschneider, Drehmomentschlüssel, Steckschlüsselsatz, Inbusschlüssel, Ratsche, Bohrer, Bits, Gewindeschneider, Feilen
* **Messgeräte:** Messschieber, Bügelmessschraube, Messuhr, Multimeter, Stromzange, Spannungsprüfer, Durchgangsprüfer, Isolationsmessgerät, Prüfgerät
* **Elektro/Zubehör:** Lötstation, Lötkolben, Schrumpfschlauch, Aderendhülsen, Kabelbinder, Klemmen, Steckverbinder, Sensorik, Aktorik, Pneumatik-/Hydraulik-/SPS-Zubehör, Automatisierungstechnik, Maschinenbau-Zubehör, Instandhaltungsbedarf
* **Literatur/Fortbildung:** technische Fachbücher, Tabellenbücher, Normen, VDE-Unterlagen, Meisterschule, Technikerweiterbildung, Staplerschein, Kranschein, Schweißkurs, SPS-/Pneumatik-/Hydraulik-/CAD-Schulung, Arbeitsschutzschulung

**Kleidung/Schutzausrüstung:** nicht automatisch `steuerrelevant`; bei Sicherheitsschuhen, Schutzbrille, Gehörschutz, Helm, Handschuhen → `ai-review-tag-tax`; `steuerrelevant` nur bei eindeutigem Schutz-/Sicherheitsbezug.

Bei Relevanz nur `steuerrelevant` (+ Prozess-Tags) — keine Berufsfeld-/Kostenarten-Tags in Phase B.

#### Software / EDV

Potenziell steuerlich relevante Hinweise:

* **Hardware:** Laptop, Computer, PC-Komponenten, Monitor, Tastatur, Maus, Trackball, Grafiktablet, Headset, Mikrofon, Webcam, Dockingstation, USB-Hub, Router, Switch, NAS, Server, SSD, RAM, Drucker, Scanner
* **Dienste/Lizenzen:** Cloud-Dienste, Hosting, Domains, SSL, E-Mail-Hosting, VPN, Softwarelizenzen, IDE, Git/CI/CD, SaaS, PM-/Dokumentations-/Design-/API-/DB-/Test-/Security-Tools
* **Weiterbildung/Büro:** Fachliteratur, Online-Kurse, Zertifizierungen, Konferenzen, Schreibtisch, Bürostuhl, Monitorarm, Arbeitsplatzbeleuchtung, Homeoffice-Ausstattung, Honorar-Rechnung Steuerberatung bei selbständiger/nebenberuflicher IT-Tätigkeit (nicht der Steuerbescheid), EDV-Projektrechnungen

Bei Relevanz nur `steuerrelevant` (+ Prozess-Tags) — keine Berufsfeld-/Kostenarten-Tags in Phase B.

#### Grundschule / Pädagogik

Potenziell steuerlich relevante Hinweise:

* **Allgemein:** Unterrichtsmaterial, Lehrmittel, Schulbücher, Fachbücher, Arbeitshefte, Lernkarten, Lernspiele, Förder-/Inklusionsmaterial, DaZ-Material, Poster, Stempel, Whiteboard-/Tafelmaterial, Laminiergerät, Toner, Druckerpapier, Ordner, Planer, Lehrerkalender, Stifte, Marker
* **Transport:** Taschen, Rucksäcke, Koffer, Organizer, Transportboxen, Einkaufstrolleys u. Ä. zum Transport/Organisation von Unterrichtsmaterial, Lehrmitteln, Heften, Planern, Korrekturen, Dienst-Laptop/Tablet — auch mit Notebook-/Laptop-/Tablet-Fach.
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

Bei Relevanz nur `steuerrelevant` (+ Prozess-Tags) — keine Berufsfeld-/Kostenarten-Tags in Phase B.

### B.6 Entscheidungslogik

1. Klar absetzbare berufliche Ausgabe (Werbungskosten o. Ä.) → `steuerrelevant`.
2. Möglich, aber unsicher → `ai-review-tag-tax`; `steuerrelevant` nur wenn überwiegend plausibel.
3. Kein klarer Absetzungsbezug → `ai-tag-tax`, kein `steuerrelevant`; ggf. `ai-review-tag-tax` für Nachschärfung.
4. **Immer** `ai-tag-tax` setzen.
5. Keine Steuer-Untertags; Berufskontext nur in der Notiz / `professional_context`.
6. Gemischte Nutzung → `steuerrelevant` wenn plausibel + `ai-review-tag-tax` für Aufteilung.
7. Kleidung/Textilien → nicht automatisch `steuerrelevant`; Schutzbezug nur vorsichtig + Review.
8. Transportmittel (Tasche, Rucksack, Koffer, Organizer …)? → Regel „Transport (Lehrkraft)“; plausibel `steuerrelevant`, sonst mindestens `ai-review-tag-tax`.
9. Einkommensteuerbescheid / Festsetzung / Steuererklärung / reine Steuerkorrespondenz → `none`, **kein** `steuerrelevant` (auch wenn „Steuer“ im Titel steht).
10. Fristen/Mahnungen nur `steuerrelevant`, wenn sie einen absetzbaren Ausgabebeleg betreffen.

---

## Finale Aktionen

### F.1 `document_update` (einmal)

Finale Tag-Liste aus:

* allen bisher am Dokument vorhandenen Tag-IDs
* allgemeinen Tags aus Phase A
* `ai-tag-document`, `ai-review-tag-document` (falls nötig)
* `ai-tag-tax` (immer)
* `steuerrelevant`, `ai-review-tag-tax` (falls nötig)
* neu erstellten Tag-IDs (nur Pflicht-/Prozess-Tags, keine Steuer-Untertags)

Parameter:

* `id={{document_id}}`
* `tags` als JSON-Array numerischer IDs
* optional `title`, `correspondent`, `document_type`, `created` (nur Phase-A-Änderungen; `created` als `YYYY-MM-DD`)

Beispiel: `tags="[1,12,34,56]", title="Rechnung – Stromabschlag Januar 2026", correspondent=42, document_type=7, created="2024-12-17"`

`tags` ersetzt die komplette Liste — bestehende Tags zwingend mitgeben. Numerische IDs, nicht Namen.

### F.2 `document_note_add` (einmal, zwei Abschnitte)

Mehrzeilig mit **echten Zeilenumbrüchen** (kein Literal `\n`).

**Abschnitt 1 — Automatische Einordnung:**

* Korrespondent (geändert/plausibel; ggf. Regex angelegt/aktualisiert)
* Dokumenttyp, Titel, Datum (`created` beibehalten/korrigiert)
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
- Datum unverändert (stimmt mit Rechnungsdatum überein).
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
- Datum geändert zu 2024-12-17 (Briefdatum im OCR; vorheriges Datum unplausibel).
- Tags ergänzt: EDV, ai-tag-document. Begründung: EDV-Hardware-Rechnung.
- ai-tag-document wurde gesetzt.
- ai-review-tag-document wurde nicht gesetzt.
- Keine neuen Tags angelegt.

Steuerprüfung:
- Ergebnis: steuerlich relevant.
- Tags ergänzt: steuerrelevant, ai-tag-tax. Begründung: Monitor mit beruflichem Bezug.
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
- Tags ergänzt: ai-review-tag-tax, ai-tag-tax. Begründung: Versicherungsbezug unklar, kein eindeutiger Berufsausgaben-Beleg.
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
* Bestehende Tags nie entfernen; max. 2 neue Tags.
* `tag_create` immer mit `name`; `document_update` mit numerischen Tag-IDs.
* `correspondent_create`: immer `match` + `matching_algorithm=4`; nie `6`.
* Regex-Nachpflege bei zugewiesenem Korrespondenten prüfen, wenn zuvor keiner passte.
* Bei Unsicherheit Review-Tags setzen statt falsch klassifizieren.

## Antwortformat

Kurz auf Deutsch:

* Dokument-ID
* Korrespondent, Dokumenttyp, Titel, Datum (gesetzt/geändert/unverändert)
* Allgemeine und Steuer-Tags
* `ai-tag-document`, `ai-review-tag-document`, `ai-tag-tax`, `ai-review-tag-tax`
* Ergebnis Steuerprüfung + kurze Begründung
* Neu angelegte Tags/Korrespondenten/Dokumenttypen; Regex-Nachpflege falls vorhanden

Beispiel:

`Dokument {{document_id}}: Korrespondent Stadtwerke (unverändert), Typ Rechnung, Titel unverändert, Datum unverändert. Tags: Finanzen, Wohnen, Strom, ai-tag-document, ai-tag-tax. Steuer: kein klarer Bezug. ai-review-tag-document und ai-review-tag-tax nicht gesetzt.`
