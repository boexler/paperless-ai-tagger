import re
from typing import Any

from pydantic import BaseModel, Field


DOC_URL_ID_PATTERN = re.compile(r"/documents/(\d+)")


class WebhookPayload(BaseModel):
    doc_url: str | None = None
    doc_title: str | None = None
    correspondent: str | None = None
    document_type: str | None = Field(default=None, alias="document_type")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @classmethod
    def from_body(cls, body: dict[str, Any]) -> "WebhookPayload":
        return cls.model_validate(body)


def extract_document_id(doc_url: str | None) -> int | None:
    if not doc_url:
        return None
    match = DOC_URL_ID_PATTERN.search(doc_url)
    if not match:
        return None
    return int(match.group(1))
