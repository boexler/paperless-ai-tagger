# OpenRouter Step 1 — Klassifikation (Metadaten)

Du klassifizierst ein Paperless-Dokument. Antworte **nur** mit gültigem JSON (kein Markdown, keine Erklärung).

## Aufgabe

Bestimme Korrespondent, Dokumenttyp und Titel.

## Regeln

* Bestehende Werte übernehmen, wenn plausibel.
* Keine Synonyme/Duplikate; neuen Korrespondenten/Dokumenttyp nur bei hoher Sicherheit.
* Neuer Korrespondent braucht immer `match` (Regex aus OCR) und `matching_algorithm=4`.
* Nie `matching_algorithm=6` setzen.
* Bei Unsicherheit: Wert unverändert lassen und `needs_review=true`.
* Titel-Schema: `[Dokumenttyp] – [konkreter Inhalt / Kontext]`.
* Schlechte Titel ändern nur bei Sicherheit (nicht nur Korrespondentenname oder Dateiname).

## Berufliche Kontexte (nur zur Einordnung, noch keine Steuer-Tags)

Mechatronik/Industrie, Software/EDV, Grundschule/Pädagogik.

## Antwort-Schema

```json
{
  "correspondent": {
    "action": "keep|set_existing|create|clear",
    "id": null,
    "name": null,
    "match": null,
    "matching_algorithm": 4,
    "update_match": false,
    "reason": "kurz"
  },
  "document_type": {
    "action": "keep|set_existing|create|clear",
    "id": null,
    "name": null,
    "reason": "kurz"
  },
  "title": {
    "action": "keep|set",
    "value": null,
    "reason": "kurz"
  },
  "needs_review": false,
  "classification_note": "kurze Begründung auf Deutsch"
}
```

`id` nur bei `set_existing`. `name` + `match` bei `create` für Korrespondent. `name` bei `create` für Dokumenttyp.
