from dataclasses import dataclass
from typing import Protocol


@dataclass
class TaggingResult:
    """Outcome of a single document tagging run."""

    document_id: int
    status: str
    run_id: str | None = None
    summary: str | None = None
    error: str | None = None


class AgentProvider(Protocol):
    """Runs the tagging agent for one Paperless document."""

    def tag_document(
        self,
        document_id: int,
        doc_title: str | None = None,
        correspondent: str | None = None,
        document_type: str | None = None,
        doc_url: str | None = None,
    ) -> TaggingResult:
        """Execute tagging for the given document."""
        ...


def exit_code_for_result(result: TaggingResult) -> int:
    """Map tagging outcomes to process exit codes for CLI wrappers."""
    if result.status == "finished":
        return 0
    if result.status == "startup_error":
        return 1
    if result.status == "run_error":
        return 2
    return 3
