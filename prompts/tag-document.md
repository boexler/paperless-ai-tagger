# Paperless Auto-Tagging

Tagge das Paperless-Dokument mit der ID **{{document_id}}**.

## MCP-Tools (exakte Namen)

Verwende ausschließlich diese PaperlessMCP-Tool-Namen:

| Aktion | Tool |
|---|---|
| Tags auflisten | `paperless_tags_list` |
| Tag anlegen | `paperless_tags_create` |
| Dokument lesen | `paperless_documents_get` |
| Dokument aktualisieren | `paperless_documents_update` |

## Vorgehen

1. Lies zuerst alle existierenden Tags mit `paperless_tags_list` aus.
2. Lies das Dokument mit `paperless_documents_get` (Parameter: `id={{document_id}}`).
3. Analysiere Titel, Korrespondent, Dokumenttyp und den OCR-Text (`content`).
4. Wähle passende Tags **primär aus der bestehenden Tag-Liste** – nutze vorhandene Tags als Basis deiner Auswahl.
5. Sammle die **numerischen Tag-IDs** der gewählten Tags (nicht die Namen).
6. Ergänze Korrespondent oder Dokumenttyp nur, wenn du dir sicher bist.
7. Erstelle fehlende Tags mit `paperless_tags_create` – **Pflichtparameter:** `name` (z. B. `name="Rechnung"`).
8. Stelle sicher, dass der Tag `ai-tagged` existiert (`paperless_tags_create` mit `name="ai-tagged"`, falls nicht in der Liste).
9. Setze alle Tags am Dokument mit `paperless_documents_update` (Parameter: `id={{document_id}}`, `tags="12,34,56"` als kommagetrennte Tag-IDs).

## Regeln

- **Keine Löschungen** – weder Dokumente noch Tags löschen.
- **Keine Massenänderungen** – nur dieses eine Dokument bearbeiten.
- Bei Unsicherheit: Tag `needs-review` setzen und eine kurze Begründung im Antworttext nennen.
- Bestehende Tags am Dokument nicht entfernen, nur sinnvolle Tags ergänzen.
- **Bestehende Tags im System bevorzugen** – keine Synonyme oder Duplikate anlegen (z. B. „Rechnung“ statt „Invoice“, wenn „Rechnung“ schon existiert).
- Maximal 5 neue Tags pro Dokument; neu erstellte Tags nur, wenn die Tag-Liste keine passende Wahl bietet.
- Bei `paperless_tags_create` immer den Parameter `name` setzen – niemals leer oder ohne `name` aufrufen.
- Antworte auf Deutsch mit einer kurzen Zusammenfassung der gesetzten Metadaten.

## Kontext aus dem Webhook

- Titel: {{doc_title}}
- Korrespondent: {{correspondent}}
- Dokumenttyp: {{document_type}}
- URL: {{doc_url}}
