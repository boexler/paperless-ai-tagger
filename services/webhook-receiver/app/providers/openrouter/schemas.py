"""Pydantic schemas for OpenRouter single-shot JSON responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CorrespondentDecision(BaseModel):
    """LLM decision for correspondent assignment."""

    action: Literal["keep", "set_existing", "create", "clear"] = "keep"
    id: int | None = None
    name: str | None = None
    match: str | None = None
    matching_algorithm: int = 4
    update_match: bool = False
    reason: str = ""


class DocumentTypeDecision(BaseModel):
    """LLM decision for document type assignment."""

    action: Literal["keep", "set_existing", "create", "clear"] = "keep"
    id: int | None = None
    name: str | None = None
    reason: str = ""


class TitleDecision(BaseModel):
    """LLM decision for document title."""

    action: Literal["keep", "set"] = "keep"
    value: str | None = None
    reason: str = ""


class ClassificationResult(BaseModel):
    """Metadata classification section."""

    correspondent: CorrespondentDecision = Field(default_factory=CorrespondentDecision)
    document_type: DocumentTypeDecision = Field(default_factory=DocumentTypeDecision)
    title: TitleDecision = Field(default_factory=TitleDecision)
    needs_review: bool = False
    classification_note: str = ""


class TagSelectionResult(BaseModel):
    """General (non-tax) tags section."""

    tags_to_add: list[str] = Field(default_factory=list)
    new_tags: list[str] = Field(default_factory=list)
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    suggested_tags: list[str] = Field(default_factory=list)
    tags_note: str = ""


class TaxReviewResult(BaseModel):
    """Tax relevance section."""

    result: Literal["relevant", "maybe", "none"] = "none"
    tags_to_add: list[str] = Field(default_factory=list)
    new_tags: list[str] = Field(default_factory=list)
    needs_review: bool = False
    professional_context: str = "keine"
    tax_note: str = ""


class DocumentTaggingResult(BaseModel):
    """Single-shot OpenRouter response for classify + tags + tax."""

    classification: ClassificationResult = Field(default_factory=ClassificationResult)
    tags: TagSelectionResult = Field(default_factory=TagSelectionResult)
    tax: TaxReviewResult = Field(default_factory=TaxReviewResult)
