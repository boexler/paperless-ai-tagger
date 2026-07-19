from app.config import Settings
from app.providers.base import TaggingResult, exit_code_for_result
from app.providers.factory import create_provider

__all__ = ["DocumentTagger", "TaggingResult", "exit_code_for_result"]


class DocumentTagger:
    """Facade that delegates document tagging to the configured agent provider."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = create_provider(settings)

    def tag_document(
        self,
        document_id: int,
        doc_title: str | None = None,
        correspondent: str | None = None,
        document_type: str | None = None,
        doc_url: str | None = None,
    ) -> TaggingResult:
        """Run tagging for one document via the selected provider."""
        return self.provider.tag_document(
            document_id=document_id,
            doc_title=doc_title,
            correspondent=correspondent,
            document_type=document_type,
            doc_url=doc_url,
        )
