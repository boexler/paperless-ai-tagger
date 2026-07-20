# OpenRouter Step 2 — Allgemeine Tags

Du wählst allgemeine Tags für ein Paperless-Dokument. Antworte **nur** mit gültigem JSON (kein Markdown, keine Erklärung).

## Aufgabe

Wähle passende **nicht-steuerliche** Tags und setze Prozess-Tags.

## Regeln

* Primär aus der vorhandenen Tag-Liste wählen (Namen exakt übernehmen).
* Bestehende Dokument-Tags bleiben erhalten (nicht entfernen).
* Keine Steuer-Tags (`steuerrelevant`, `werbungskosten`, `ai-tag-tax`, `ai-review-tag-tax`, …).
* Keine Tags, die nur den Dokumenttyp wiederholen.
* Neue Tags nur wenn kein passendes existiert, wiederverwendbar, max. 5 neue Tags.
* Immer `ai-tag-document` setzen (als existierendes Tag oder `new_tags`).
* `ai-review-tag-document` bei Unsicherheit (Titel/Korrespondent/Typ unklar, OCR schlecht, Handlungsbedarf, Duplikatverdacht, …).
* Nicht anlegen: Monate, Jahre, Dateiformate, einmalige Produktnamen, reine Korrespondenten-Namen.

## Antwort-Schema

```json
{
  "tags_to_add": ["Finanzen", "Wohnen"],
  "new_tags": ["ai-tag-document"],
  "needs_review": false,
  "review_reasons": [],
  "suggested_tags": [],
  "tags_note": "kurze Begründung auf Deutsch"
}
```

`tags_to_add` = Namen aus der vorhandenen Liste. `new_tags` = neu anzulegende Namen. `suggested_tags` = Vorschläge ohne Anlegen.
