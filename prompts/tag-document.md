# Paperless Auto-Tagging

Tagge das Paperless-Dokument mit der ID **{{document_id}}**.

## MCP-Tools (exakte Namen)

Verwende ausschließlich diese [paperless-ngx-mcp](https://github.com/freeformz/paperless-ngx-mcp)-Tool-Namen:

| Aktion | Tool |
|---|---|
| Tags auflisten | `tag_list` |
| Tag anlegen | `tag_create` |
| Dokument lesen | `document_get` |
| Dokument aktualisieren | `document_update` |
| Notiz hinzufügen | `document_note_add` |

## Vorgehen

1. Lies zuerst alle existierenden Tags mit `tag_list` aus (`page_size=100`).
2. Lies das Dokument mit `document_get` (Parameter: `id={{document_id}}`).
3. Analysiere Titel, Korrespondent, Dokumenttyp und den OCR-Text (`content`).
4. Wähle passende Tags **primär aus der bestehenden Tag-Liste** – nutze vorhandene Tags als Basis deiner Auswahl.
5. Sammle die **numerischen Tag-IDs** der gewählten Tags (nicht die Namen).
6. Ergänze Korrespondent oder Dokumenttyp nur, wenn du dir sicher bist.
7. Erstelle fehlende Tags mit `tag_create` – **Pflichtparameter:** `name` (z. B. `name="Rechnung"`).
8. Stelle sicher, dass der Tag `ai-tagged` existiert (`tag_create` mit `name="ai-tagged"`, falls nicht in der Liste).
9. Setze alle Tags am Dokument mit `document_update` (Parameter: `id={{document_id}}`, `tags` als JSON-Array aller Tag-IDs inkl. bestehender Tags, z. B. `"[1,12,34,56]"`).
10. Hänge eine kurze deutsche Zusammenfassung deiner Entscheidung als Notiz an (`document_note_add` mit `id={{document_id}}` und `note="..."`).

## Regeln

- **Keine Löschungen** – weder Dokumente noch Tags löschen.
- **Keine Massenänderungen** – nur dieses eine Dokument bearbeiten.
- Bei Unsicherheit: Tag `needs-review` setzen und die Begründung in der Notiz nennen.
- Bestehende Tags am Dokument nicht entfernen, nur sinnvolle Tags ergänzen.
- **Bestehende Tags im System bevorzugen** – keine Synonyme oder Duplikate anlegen (z. B. „Rechnung“ statt „Invoice“, wenn „Rechnung“ schon existiert).
- Maximal 5 neue Tags pro Dokument; neu erstellte Tags nur, wenn die Tag-Liste keine passende Wahl bietet.
- Bei `tag_create` immer den Parameter `name` setzen – niemals leer oder ohne `name` aufrufen.
- Bei `document_update` das Feld `tags` als JSON-Array übergeben – es ersetzt die komplette Tag-Liste des Dokuments.
- Antworte auf Deutsch mit einer kurzen Zusammenfassung der gesetzten Metadaten.

## Kontext aus dem Webhook

- Titel: {{doc_title}}
- Korrespondent: {{correspondent}}
- Dokumenttyp: {{document_type}}
- URL: {{doc_url}}
