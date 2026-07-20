"""Paperless-ngx REST API client for OpenRouter read/write operations."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

PAGE_SIZE = 100


class PaperlessClientError(Exception):
    """Raised when a Paperless REST call fails."""


class PaperlessClient:
    """Thin REST client against the Paperless-ngx API."""

    def __init__(self, base_url: str, api_token: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Token {api_token}"},
            timeout=timeout,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> PaperlessClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Execute an API request and return parsed JSON when present."""
        url = urljoin(self.base_url, path.lstrip("/"))
        try:
            response = self._client.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PaperlessClientError(f"Paperless API {method} {path} failed: {exc}") from exc

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise PaperlessClientError(
                f"Paperless API {method} {path} returned invalid JSON",
            ) from exc

    def _list_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Paginate a Paperless list endpoint until all results are loaded."""
        query = dict(params or {})
        query.setdefault("page_size", PAGE_SIZE)
        query.setdefault("page", 1)
        results: list[dict[str, Any]] = []

        while True:
            payload = self._request("GET", path, params=query)
            if not isinstance(payload, dict):
                raise PaperlessClientError(f"Unexpected list payload for {path}")
            page_results = payload.get("results") or []
            if not isinstance(page_results, list):
                raise PaperlessClientError(f"Unexpected results type for {path}")
            results.extend(item for item in page_results if isinstance(item, dict))
            next_url = payload.get("next")
            if not next_url:
                break
            query["page"] = int(query["page"]) + 1

        return results

    def get_document(self, document_id: int) -> dict[str, Any]:
        """Fetch one document including OCR content and metadata."""
        payload = self._request("GET", f"/api/documents/{document_id}/")
        if not isinstance(payload, dict):
            raise PaperlessClientError(f"Unexpected document payload for id={document_id}")
        return payload

    def list_tags(self) -> list[dict[str, Any]]:
        """Return all tags."""
        return self._list_all("/api/tags/")

    def list_correspondents(self) -> list[dict[str, Any]]:
        """Return all correspondents."""
        return self._list_all("/api/correspondents/")

    def list_document_types(self) -> list[dict[str, Any]]:
        """Return all document types."""
        return self._list_all("/api/document_types/")

    def create_tag(self, name: str) -> dict[str, Any]:
        """Create a tag by name and return the created object."""
        payload = self._request("POST", "/api/tags/", json={"name": name})
        if not isinstance(payload, dict) or "id" not in payload:
            raise PaperlessClientError(f"Failed to create tag {name!r}")
        logger.info("Created Paperless tag id=%s name=%s", payload["id"], name)
        return payload

    def create_correspondent(
        self,
        name: str,
        match: str,
        matching_algorithm: int = 4,
        is_insensitive: bool = True,
    ) -> dict[str, Any]:
        """Create a correspondent with regex matching defaults."""
        payload = self._request(
            "POST",
            "/api/correspondents/",
            json={
                "name": name,
                "match": match,
                "matching_algorithm": matching_algorithm,
                "is_insensitive": is_insensitive,
            },
        )
        if not isinstance(payload, dict) or "id" not in payload:
            raise PaperlessClientError(f"Failed to create correspondent {name!r}")
        logger.info("Created Paperless correspondent id=%s name=%s", payload["id"], name)
        return payload

    def update_correspondent(self, correspondent_id: int, **fields: Any) -> dict[str, Any]:
        """Patch an existing correspondent."""
        payload = self._request(
            "PATCH",
            f"/api/correspondents/{correspondent_id}/",
            json=fields,
        )
        if not isinstance(payload, dict):
            raise PaperlessClientError(
                f"Failed to update correspondent id={correspondent_id}",
            )
        return payload

    def create_document_type(self, name: str) -> dict[str, Any]:
        """Create a document type by name."""
        payload = self._request("POST", "/api/document_types/", json={"name": name})
        if not isinstance(payload, dict) or "id" not in payload:
            raise PaperlessClientError(f"Failed to create document type {name!r}")
        logger.info("Created Paperless document type id=%s name=%s", payload["id"], name)
        return payload

    def update_document(self, document_id: int, **fields: Any) -> dict[str, Any]:
        """Patch document metadata. Caller must pass the full merged tags list."""
        payload = self._request("PATCH", f"/api/documents/{document_id}/", json=fields)
        if not isinstance(payload, dict):
            raise PaperlessClientError(f"Failed to update document id={document_id}")
        return payload

    def add_document_note(self, document_id: int, note: str) -> Any:
        """Append a note to a document."""
        return self._request(
            "POST",
            f"/api/documents/{document_id}/notes/",
            json={"note": note},
        )

    def ensure_tag(self, name: str, tags_by_name: dict[str, int]) -> int:
        """Return an existing tag id or create the tag and update the name map."""
        existing = tags_by_name.get(name.casefold())
        if existing is not None:
            return existing
        created = self.create_tag(name)
        tag_id = int(created["id"])
        tags_by_name[name.casefold()] = tag_id
        return tag_id
