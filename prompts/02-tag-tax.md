# Paperless Steuerrelevanz-Prüfung

Prüfe das bereits klassifizierte Paperless-Dokument mit der ID **{{document_id}}** darauf, ob es potenziell steuerlich relevant ist.

Dieser Prozess ist Stufe 02 und ein nachgelagerter Prüfprozess nach der Klassifikation in Stufe 01 (`01-tag-document.md`). Korrespondent, Dokumenttyp und Titel wurden dort bereits gesetzt. Es geht ausschließlich darum, steuerlich relevante Dokumente zu erkennen und passend zu taggen. Es sollen keine allgemeinen Klassifikationen neu vorgenommen werden.

## Ziel

Prüfe, ob das Dokument potenziell für die Einkommensteuererklärung relevant sein kann, insbesondere als:

* Werbungskosten
* beruflich veranlasste Arbeitsmittel
* Fortbildungskosten
* Fachliteratur
* berufliche Reisekosten
* Bewerbungskosten
* Beiträge zu Berufsverbänden
* Kosten im Zusammenhang mit Homeoffice oder Arbeitszimmer
* sonstige beruflich veranlasste Ausgaben

Die Prüfung bezieht sich primär auf drei berufliche Kontexte:

1. Mechatroniker / Industrieelektroniker / Industriemechaniker in der Industrie
2. Softwareentwickler / Softwareentwicklung / IT- oder EDV-Dienstleistung
3. Grundschullehrerin / Pädagogin, einschließlich aller Unterrichtsfächer wie Deutsch, Mathematik, Sachunterricht, Kunst, Musik, Sport, Religion/Ethik, Englisch, Förderunterricht und Klassenleitung

## MCP-Tools

Verwende ausschließlich diese `paperless-ngx-mcp`-Tool-Namen:

| Aktion                 | Tool                |
| ---------------------- | ------------------- |
| Tags auflisten         | `tag_list`          |
| Tag anlegen            | `tag_create`        |
| Dokument lesen         | `document_get`      |
| Dokument aktualisieren | `document_update`   |
| Notiz hinzufügen       | `document_note_add` |

## Kontext aus dem Webhook

* Dokument-ID: `{{document_id}}`
* Titel: `{{doc_title}}`
* Korrespondent: `{{correspondent}}`
* Dokumenttyp: `{{document_type}}`
* URL: `{{doc_url}}`

## Grundregeln

* Prüfe nur die steuerliche Relevanz.
* Ändere Titel, Korrespondent und Dokumenttyp nicht.
* Entferne keine bestehenden Tags.
* Bestehende Tags am Dokument müssen erhalten bleiben.
* Neue Tags nur anlegen, wenn sie für diesen Prozess zwingend benötigt werden und noch nicht existieren.
* Bei Unsicherheit lieber `ai-review-tag-tax` setzen als falsch positiv oder falsch negativ entscheiden.
* Keine steuerliche Beratung leisten, sondern nur potenzielle steuerliche Relevanz markieren.
* Keine harte Negativentscheidung treffen, wenn der Fall später noch steuerlich geprüft oder geschärft werden könnte.
* Arbeitskleidung nicht automatisch als steuerrelevant taggen.
* Kleidung, Schuhe oder Textilien nur dann markieren, wenn ein klarer beruflicher Sonderfall erkennbar ist; ansonsten `ai-review-tag-tax` setzen.
* Nur das Dokument mit der ID `{{document_id}}` bearbeiten.
* Keine Massenänderungen durchführen.
* Keine Dokumente oder Tags löschen.

## Steuer-Tags

Prüfe, ob folgende Tags existieren. Wenn sie fehlen und benötigt werden, lege sie mit `tag_create` an.

Pflicht-Tags für diesen Prozess:

* `steuerrelevant`
* `ai-review-tag-tax`
* `ai-tag-tax`

Optionale Steuer-Tags, nur wenn passend und vorhanden oder eindeutig sinnvoll:

* `werbungskosten`
* `arbeitsmittel`
* `fortbildung`
* `fachliteratur`
* `homeoffice`
* `arbeitszimmer`
* `reisekosten`
* `fahrtkosten`
* `bewerbung`
* `berufsverband`
* `softwareentwicklung`
* `edv`
* `mechatronik`
* `industrie`
* `schule`
* `pädagogik`
* `unterrichtsmaterial`
* `musik`
* `sport`
* `kunst`
* `sachunterricht`
* `förderunterricht`

Nicht mehr als Standard-Steuer-Tag verwenden:

* `berufskleidung`

Wenn optionale Tags fehlen, lege sie nur an, wenn sie klar wiederverwendbar sind. Andernfalls setze nur `steuerrelevant` und ggf. `ai-review-tag-tax`.

## Vorgehen

### 1. Tags laden

Lies zuerst alle existierenden Tags mit `tag_list`.

Verwende:

* `page_size=100`

Falls mehr als 100 Tags vorhanden sind und Pagination unterstützt wird, lade weitere Seiten nach, bis die Tag-Liste vollständig ist.

Merke dir:

* Tag-ID
* Tag-Name
* ob ein passendes Steuer-Tag bereits existiert

### 2. Dokument lesen

Lies das Dokument mit `document_get`.

Parameter:

* `id={{document_id}}`

Analysiere:

* Titel
* Korrespondent
* Dokumenttyp
* vorhandene Tags
* OCR-Text / `content`
* erkennbare Beträge
* erkennbare Artikel oder Leistungen
* beruflicher Bezug
* Zeitraum oder Datum
* mögliche private Mitveranlassung

### 3. Bestehende Tags sichern

Prüfe, welche Tags bereits am Dokument gesetzt sind.

Diese bestehenden Tag-IDs müssen beim späteren `document_update` vollständig wieder mitgegeben werden, da `tags` die komplette Tag-Liste ersetzt.

Regel:

* vorhandene Tags behalten
* steuerliche Tags ergänzen
* keine Tags entfernen

### 4. Steuerliche Relevanz bewerten

Bewerte das Dokument anhand der folgenden Entscheidung.

#### A. Steuerlich relevant

Setze `steuerrelevant`, wenn das Dokument mit hoher Wahrscheinlichkeit beruflich oder steuerlich nutzbar ist.

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

#### B. Steuerlich möglicherweise relevant

Setze `ai-review-tag-tax`, wenn steuerliche Relevanz möglich, aber nicht sicher ist.

Typische Fälle:

* Gegenstand kann privat oder beruflich genutzt werden
* beruflicher Bezug ist plausibel, aber nicht eindeutig
* Dokument enthält nur eine unspezifische Rechnung ohne klare Artikelbeschreibung
* Korrespondent oder Produkt lässt beruflichen Bezug vermuten, aber OCR ist unvollständig
* Fortbildungsbezug ist möglich, aber Kursinhalt nicht klar
* Homeoffice- oder Arbeitszimmerbezug ist möglich, aber privat mitveranlasst
* Rechnung enthält gemischte private und berufliche Positionen
* Dokument betrifft rechtliche, steuerliche oder finanzielle Themen, aber der konkrete Bezug ist unklar
* Betrag oder Artikel sind nicht lesbar
* Dokumenttyp passt nicht eindeutig zum Inhalt
* Kleidung, Schuhe oder Textilien könnten beruflich begründet sein, sind aber steuerlich nicht automatisch eindeutig
* kein Steuerbezug erkennbar, aber der Prozess soll diesen Dokumenttyp künftig nachschärfen können

#### C. Kein klarer Steuerbezug erkennbar

Triff keine endgültige steuerliche Negativentscheidung.

Wenn kein beruflicher oder steuerlicher Bezug erkennbar ist:

* setze `ai-tag-tax`
* setze kein `steuerrelevant`
* setze `ai-review-tag-tax`, wenn der Fall später menschlich oder regelbasiert nachgeschärft werden soll
* dokumentiere kurz in der Notiz, dass kein klarer Steuerbezug erkannt wurde

Beispiele für eher keinen klaren Steuerbezug:

* private Konsumausgaben ohne erkennbaren beruflichen Bezug
* Lebensmittel, Freizeit, Urlaub
* private Kleidung
* reine Haushaltskosten ohne erkennbaren Arbeitszimmer- oder Homeoffice-Bezug
* private Unterhaltungselektronik ohne erkennbaren Arbeitsbezug
* Rechnungen, die offensichtlich privat wirken

Wenn du unsicher bist, ob der Beleg wirklich irrelevant ist, setze `ai-review-tag-tax`.

### 5. Berufsfeldbezug prüfen

Prüfe, ob das Dokument zu einem der folgenden beruflichen Kontexte passt.

#### Mechatroniker / Industrieelektroniker / Industriemechaniker

Potenziell steuerlich relevante Hinweise:

* Werkzeug
* Werkzeugkoffer
* Werkzeugwagen
* Schraubendreher
* Zangen
* Crimpzange
* Abisolierzange
* Seitenschneider
* Drehmomentschlüssel
* Steckschlüsselsatz
* Inbusschlüssel
* Maulschlüssel
* Ratsche
* Bohrer
* Bits
* Gewindeschneider
* Feilen
* Messschieber
* Bügelmessschraube
* Messuhr
* Multimeter
* Stromzange
* Spannungsprüfer
* Durchgangsprüfer
* Isolationsmessgerät
* Prüfgerät
* Lötstation
* Lötkolben
* Lötzinn
* Schrumpfschlauch
* Aderendhülsen
* Kabelbinder
* Klemmen
* Steckverbinder
* Sensorik
* Aktorik
* Pneumatik-Zubehör
* Hydraulik-Zubehör
* SPS-Zubehör
* Automatisierungstechnik
* Elektrotechnik-Zubehör
* Maschinenbau-Zubehör
* Instandhaltungsbedarf
* technische Fachbücher
* Tabellenbücher
* Normen
* VDE-Unterlagen
* Prüfungsvorbereitung
* Meisterschule
* Technikerweiterbildung
* Staplerschein
* Kranschein
* Schweißkurs
* Elektrotechnik-Schulung
* SPS-Schulung
* Pneumatik-Schulung
* Hydraulik-Schulung
* CAD/CAM-Schulung
* Arbeitsschutzschulung

Kleidung / Schuhe / Schutzausrüstung:

* nicht automatisch als steuerrelevant taggen
* bei Sicherheitsschuhen, Schutzbrille, Gehörschutz, Helm, Handschuhen oder spezieller Schutzausrüstung `ai-review-tag-tax` setzen
* `steuerrelevant` nur setzen, wenn aus Dokument und Kontext eindeutig ein beruflicher Schutz- oder Sicherheitsbezug hervorgeht

Passende optionale Tags, falls vorhanden:

* `mechatronik`
* `industrie`
* `arbeitsmittel`
* `fortbildung`
* `fachliteratur`
* `werbungskosten`

#### Softwareentwickler / Softwareentwicklung / IT- oder EDV-Dienstleistung

Potenziell steuerlich relevante Hinweise:

* Laptop
* Computer
* PC-Komponenten
* Monitor
* Tastatur
* Maus
* Trackball
* Grafiktablet
* Headset
* Mikrofon
* Webcam
* Dockingstation
* USB-Hub
* Adapter
* Kabel
* Netzwerkzubehör
* Router
* Switch
* Access Point
* NAS
* Server
* SSD
* RAM
* Backup-Medien
* Drucker
* Scanner
* Cloud-Dienste
* Hosting
* Domains
* SSL-Zertifikate
* E-Mail-Hosting
* VPN
* Softwarelizenzen
* IDE
* Entwicklerwerkzeuge
* Git-Dienste
* CI/CD-Dienste
* SaaS-Abos
* Projektmanagement-Tools
* Dokumentationstools
* Design-Tools
* API-Tools
* Datenbanktools
* Testtools
* Security-Tools
* Fachliteratur
* Online-Kurse
* Zertifizierungen
* Konferenzen
* berufliche Weiterbildung
* Büroausstattung
* Schreibtisch
* Bürostuhl
* Monitorarm
* Beleuchtung für Arbeitsplatz
* Homeoffice-Ausstattung
* Steuerberatung für selbständige oder nebenberufliche Tätigkeiten
* Rechnungen im Zusammenhang mit EDV-Dienstleistung oder IT-Projekten

Passende optionale Tags, falls vorhanden:

* `softwareentwicklung`
* `edv`
* `arbeitsmittel`
* `fortbildung`
* `fachliteratur`
* `homeoffice`
* `werbungskosten`

#### Grundschullehrerin / Pädagogin

Potenziell steuerlich relevante Hinweise:

Allgemeines Unterrichtsmaterial:

* Unterrichtsmaterial
* Lehrmittel
* Schulbücher
* Fachbücher
* pädagogische Literatur
* Arbeitshefte
* Arbeitsblätter
* Kopiervorlagen
* Lernkarten
* Karteikarten
* Lernspiele
* Förderspiele
* Differenzierungsmaterial
* Inklusionsmaterial
* DaZ-Material
* Diagnosematerial
* Fördermaterial
* Klassenlektüre
* Kinderbücher für Unterricht
* Vorlesebücher
* Wörterbücher
* Atlanten
* Poster
* Plakate
* Stempel
* Sticker
* Belohnungssysteme
* Klassenraumorganisation
* Timer
* Magnetmaterial
* Whiteboard-Zubehör
* Tafelmaterial
* Kreide
* Moderationskarten
* Laminiergerät
* Laminierfolien
* Schneidemaschine
* Locher
* Tacker
* Ordner
* Mappen
* Register
* Planer
* Lehrerkalender
* Notizbücher
* Stifte
* Marker
* Druckerpapier
* Toner
* Druckerpatronen
* Kopierkosten

Deutsch / Lesen / Schreiben:

* Erstlesematerial
* Fibeln
* Lesespiele
* Silbenmaterial
* Anlautkarten
* Schreibhefte
* Rechtschreibmaterial
* Grammatikmaterial
* Lesetagebuch
* Klassenlektüre
* Buchstabenkarten

Mathematik:

* Rechenmaterial
* Zahlenstrahl
* Rechenrahmen
* Rechenplättchen
* Steckwürfel
* Geometriekörper
* Lineale
* Zirkel
* Geodreieck
* Mathe-Lernspiele
* Einmaleins-Material
* Uhrzeit-Lernmaterial
* Geld-Rechenmaterial

Sachunterricht:

* Experimentiermaterial
* Naturwissenschaftliches Lernmaterial
* Mikroskop
* Lupen
* Pflanzenzuchtmaterial
* Magnetismus-Material
* Stromkreis-Bausatz
* Kartenmaterial
* Globus
* Wetterstation
* Verkehrserziehungsmaterial
* Erste-Hilfe-Unterrichtsmaterial

Kunst / Werken:

* Bastelmaterial
* Tonpapier
* Pappe
* Scheren
* Kleber
* Farben
* Pinsel
* Wasserfarben
* Acrylfarben
* Filzstifte
* Wachsmalstifte
* Kreide
* Ton
* Modelliermasse
* Wolle
* Stoff
* Perlen
* Werkmaterial
* Aufbewahrungsboxen für Unterrichtsmaterial

Musik:

* Noten
* Liederbücher
* Rhythmusinstrumente
* Klanghölzer
* Triangel
* Trommeln
* Rasseln
* Boomwhackers
* Glockenspiel
* Metronom
* Musikunterrichtsmaterial
* Musiksoftware
* Audiozubehör für Unterricht

Sport:

* Bälle
* Springseile
* Markierungshütchen
* Leibchen
* Koordinationsleiter
* Stoppuhr
* Pfeife
* Gymnastikbänder
* kleine Sportgeräte
* Unterrichtsmaterial für Bewegungsspiele
* Erste-Hilfe-Material für schulischen Sportkontext

Religion / Ethik / Soziales Lernen:

* Bildkarten
* Erzählkarten
* Kamishibai-Material
* Werte- und Sozialkompetenzmaterial
* Gefühlekarten
* Gesprächskarten
* Klassenrat-Material
* Konfliktlösungsmaterial

Englisch / Fremdsprache:

* Bildkarten
* Flashcards
* Wortkarten
* Kinderbücher Englisch
* Lieder
* Hörmaterial
* Sprachlernspiele

Digitale Schule:

* Tablet
* Laptop
* Dokumentenkamera
* Beamer-Zubehör
* Adapter
* Stift für Tablet
* Lernsoftware
* Unterrichtsapps
* digitale Arbeitsblätter
* Cloud- oder Plattform-Abos mit Unterrichtsbezug

Fortbildung / Pädagogik:

* pädagogische Fortbildung
* Erste-Hilfe-Kurs
* Inklusion
* Diagnostik
* Differenzierung
* Classroom Management
* Medienbildung
* Sportfortbildung
* Musikfortbildung
* Kunstfortbildung
* Fachseminare
* Lehrerkongresse

Reisekosten / schulische Anlässe:

* Klassenfahrt
* Exkursion
* Ausflug
* Schullandheim
* Fortbildungsreise
* Bahn
* Hotel
* Parken
* ÖPNV
* Fahrtkosten mit erkennbarem schulischem Anlass

Passende optionale Tags, falls vorhanden:

* `schule`
* `pädagogik`
* `unterrichtsmaterial`
* `arbeitsmittel`
* `fortbildung`
* `fachliteratur`
* `homeoffice`
* `werbungskosten`
* `musik`
* `sport`
* `kunst`
* `sachunterricht`
* `förderunterricht`

### 6. Entscheidungslogik

Verwende diese Logik:

1. Ist ein beruflicher oder steuerlicher Bezug klar erkennbar?

   * Ja: `steuerrelevant` setzen.
   * Zusätzlich passende optionale Tags setzen.

2. Ist ein beruflicher oder steuerlicher Bezug möglich, aber unsicher?

   * Ja: `ai-review-tag-tax` setzen.
   * `steuerrelevant` nur setzen, wenn der berufliche Bezug überwiegend plausibel ist.

3. Ist kein klarer Steuerbezug erkennbar?

   * `ai-tag-tax` setzen.
   * Kein `steuerrelevant` setzen.
   * `ai-review-tag-tax` setzen, wenn der Dokumenttyp, Artikel, Korrespondent oder Kontext künftig menschlich nachgeschärft werden soll.

4. Wurde das Dokument geprüft?

   * Immer `ai-tag-tax` setzen.

5. Gibt es konkrete passende optionale Tags?

   * Nur setzen, wenn sie bereits existieren oder eindeutig sinnvoll und wiederverwendbar sind.

6. Gibt es gemischte private und berufliche Nutzung?

   * `steuerrelevant` setzen, wenn beruflicher Anteil plausibel ist.
   * zusätzlich `ai-review-tag-tax` setzen, weil Aufteilung menschlich geprüft werden sollte.

7. Geht es um Kleidung, Schuhe oder Textilien?

   * Nicht automatisch `steuerrelevant` setzen.
   * Bei eindeutigem beruflichem Schutz-/Sicherheitsbezug höchstens vorsichtig `steuerrelevant` plus `ai-review-tag-tax` setzen.
   * Bei normaler Kleidung kein `steuerrelevant` setzen.
   * Im Zweifel `ai-review-tag-tax` setzen.

8. Gibt es Fristen, Mahnungen oder Zahlungsaufforderungen?

   * Für diesen Prozess nur berücksichtigen, wenn sie steuerlich relevant sein könnten.
   * Keine allgemeinen Aufgaben-Tags setzen, außer sie existieren bereits und sind eindeutig steuerbezogen.

### 7. Tags aktualisieren

Erstelle die finale Tag-Liste aus:

* allen bereits am Dokument vorhandenen Tag-IDs
* `ai-tag-tax`
* `steuerrelevant`, falls steuerlich relevant
* `ai-review-tag-tax`, falls unsicher oder menschliche Prüfung nötig
* passenden optionalen Steuer-Tags

Rufe anschließend `document_update` auf.

Parameter:

* `id={{document_id}}`
* `tags` als JSON-Array aller numerischen Tag-IDs

Beispiel:

`tags="[1,12,34,56]"`

Wichtig:

* `tags` ersetzt die komplette Tag-Liste.
* Bestehende Tags müssen vollständig erhalten bleiben.
* Verwende numerische Tag-IDs, nicht Tag-Namen.
* Ändere keine anderen Metadaten.

### 8. Notiz hinzufügen

Hänge mit `document_note_add` eine kurze deutsche Notiz an.

Parameter:

* `id={{document_id}}`
* `note="..."`

Die Notiz muss enthalten:

* Ergebnis der Steuerprüfung
* gesetzte Steuer-Tags
* erkannter beruflicher Kontext
* kurze Begründung für die Tag-Auswahl
* ob `ai-tag-tax` gesetzt wurde
* ob `ai-review-tag-tax` gesetzt wurde
* falls `ai-review-tag-tax` gesetzt wurde: konkrete Gründe
* Hinweis, dass keine allgemeine Neuklassifikation vorgenommen wurde
* falls steuerliche Relevanz möglich, aber nicht sicher ist: `ai-review-tag-tax` setzen und Grund nennen

Wenn kein Review nötig ist, muss die Notiz klar sagen, warum `ai-review-tag-tax` nicht gesetzt wurde.

Wenn Review nötig ist, muss die Notiz klar sagen, was ein Mensch prüfen soll.

#### Formatregeln

* Übergebe die Notiz **mehrzeilig** mit **echten Zeilenumbrüchen** im `note`-Parameter.
* Kein Fließtext in einer Zeile.
* Schreibe nicht den Literaltext `\n` in die Notiz — verwende echte Zeilenumbrüche.
* Zeile 1: Überschrift `Steuerprüfung:`
* Folgezeilen: je ein Bullet mit `- ` pro Themenblock in dieser Reihenfolge:
  * Ergebnis (steuerlich relevant / möglicherweise steuerlich relevant / kein klarer Steuerbezug erkannt)
  * Tags ergänzt + Begründung
  * Beruflicher Kontext
  * `ai-tag-tax`
  * `ai-review-tag-tax`
  * Hinweis: keine allgemeinen Metadaten geändert

Bevorzugtes Format der Notiz:

```
Steuerprüfung:
- Ergebnis: [steuerlich relevant / möglicherweise steuerlich relevant / kein klarer Steuerbezug erkannt].
- Tags ergänzt: [Tag-Liste]. Begründung: [kurze Begründung].
- Beruflicher Kontext: [Mechatronik / Softwareentwicklung / EDV / Schule-Pädagogik / allgemein / keiner].
- ai-tag-tax wurde gesetzt.
- ai-review-tag-tax wurde [gesetzt/nicht gesetzt]: [Grund].
- Es wurden keine allgemeinen Metadaten geändert.
```

Beispiele:

```
Steuerprüfung:
- Ergebnis: steuerlich relevant.
- Tags ergänzt: steuerrelevant, werbungskosten, arbeitsmittel, softwareentwicklung, ai-tag-tax. Begründung: Rechnung für Monitor und Tastatur mit beruflichem Bezug.
- Beruflicher Kontext: Softwareentwicklung / EDV.
- ai-tag-tax wurde gesetzt.
- ai-review-tag-tax wurde nicht gesetzt: Einordnung plausibel.
- Es wurden keine allgemeinen Metadaten geändert.
```

```
Steuerprüfung:
- Ergebnis: möglicherweise steuerlich relevant.
- Tags ergänzt: steuerrelevant, arbeitsmittel, ai-review-tag-tax, ai-tag-tax. Begründung: Laptop kann beruflich genutzt sein, private Mitnutzung ist möglich.
- Beruflicher Kontext: Softwareentwicklung / EDV.
- ai-tag-tax wurde gesetzt.
- ai-review-tag-tax wurde gesetzt: beruflichen Nutzungsanteil prüfen.
- Es wurden keine allgemeinen Metadaten geändert.
```

```
Steuerprüfung:
- Ergebnis: kein klarer Steuerbezug erkannt.
- Tags ergänzt: ai-review-tag-tax, ai-tag-tax. Begründung: Kein klarer Steuerbezug erkannt, aber Dokumenttyp und Artikelbeschreibung sind unspezifisch.
- Beruflicher Kontext: keiner eindeutig.
- ai-tag-tax wurde gesetzt.
- ai-review-tag-tax wurde gesetzt: spätere Nachschärfung prüfen.
- Es wurden keine allgemeinen Metadaten geändert.
```

## Antwortformat

Antworte kurz auf Deutsch.

Die Antwort soll enthalten:

* Dokument-ID
* Ergebnis der Steuerprüfung
* gesetzte Steuer-Tags
* ob `ai-tag-tax` gesetzt wurde
* ob `ai-review-tag-tax` gesetzt wurde
* falls `ai-review-tag-tax` gesetzt wurde: konkrete Gründe
* kurze Begründung
* Hinweis, dass keine allgemeinen Metadaten geändert wurden
