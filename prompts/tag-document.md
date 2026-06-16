# Paperless Auto-Tagging

Tagge das Paperless-Dokument mit der ID **{{document_id}}**.

## Vorgehen

1. Lies zuerst alle existierenden Tags mit `paperless.tags.list` aus.
2. Lies das Dokument mit `paperless.documents.get` (ID: {{document_id}}).
3. Analysiere Titel, Korrespondent, Dokumenttyp und den OCR-Text (`content`).
4. Wähle passende Tags **primär aus der bestehenden Tag-Liste** – nutze vorhandene Tags als Basis deiner Auswahl.
5. Setze die gewählten Tags mit `paperless.documents.update`.
6. Ergänze Korrespondent oder Dokumenttyp nur, wenn du dir sicher bist.
7. Erstelle mit `paperless.tags.create` nur dann einen neuen Tag, wenn kein passender existierender Tag passt.
8. Setze am Ende immer den Tag `ai-tagged` (erstellen falls nicht vorhanden).

## Regeln

- **Keine Löschungen** – weder Dokumente noch Tags löschen.
- **Keine Massenänderungen** – nur dieses eine Dokument bearbeiten.
- Bei Unsicherheit: Tag `needs-review` setzen und eine kurze Begründung im Antworttext nennen.
- Bestehende Tags am Dokument nicht entfernen, nur sinnvolle Tags ergänzen.
- **Bestehende Tags im System bevorzugen** – keine Synonyme oder Duplikate anlegen (z. B. „Rechnung“ statt „Invoice“, wenn „Rechnung“ schon existiert).
- Maximal 5 neue Tags pro Dokument; neu erstellte Tags nur, wenn die Tag-Liste keine passende Wahl bietet.
- Antworte auf Deutsch mit einer kurzen Zusammenfassung der gesetzten Metadaten.

## Kontext aus dem Webhook

- Titel: {{doc_title}}
- Korrespondent: {{correspondent}}
- Dokumenttyp: {{document_type}}
- URL: {{doc_url}}
