import json
import time
from pathlib import Path


class ProcessedDocumentStore:
    """Simple file-backed deduplication store."""

    def __init__(self, path: Path, ttl_seconds: int) -> None:
        self.path = path
        self.ttl_seconds = ttl_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, float]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, float]) -> None:
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def _prune(self, data: dict[str, float], now: float) -> dict[str, float]:
        return {
            key: timestamp
            for key, timestamp in data.items()
            if now - timestamp <= self.ttl_seconds
        }

    def was_processed_recently(self, document_id: int) -> bool:
        now = time.time()
        data = self._prune(self._load(), now)
        self._save(data)
        return str(document_id) in data

    def mark_processed(self, document_id: int) -> None:
        now = time.time()
        data = self._prune(self._load(), now)
        data[str(document_id)] = now
        self._save(data)
