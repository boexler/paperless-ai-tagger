from pathlib import Path

from app.config import Settings


def render_prompt(
    settings: Settings,
    document_id: int,
    doc_title: str | None,
    correspondent: str | None,
    document_type: str | None,
    doc_url: str | None,
) -> str:
    """Load the prompt template and replace webhook placeholders."""
    template_path = Path(settings.prompt_template_path)
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{document_id}}": str(document_id),
        "{{doc_title}}": doc_title or "unbekannt",
        "{{correspondent}}": correspondent or "unbekannt",
        "{{document_type}}": document_type or "unbekannt",
        "{{doc_url}}": doc_url or "unbekannt",
    }
    prompt = template
    for key, value in replacements.items():
        prompt = prompt.replace(key, value)
    return prompt
