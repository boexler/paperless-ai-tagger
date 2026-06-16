import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.dedup import ProcessedDocumentStore
from app.models import WebhookPayload
from app.tagger import DocumentTagger, TaggingResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaggingJob:
    """One tagging job waiting in the in-memory queue."""

    document_id: int
    payload: WebhookPayload


class TaggingJobQueue:
    """In-memory async queue that limits concurrent tagging jobs."""

    def __init__(self, max_concurrent_jobs: int) -> None:
        if max_concurrent_jobs < 1:
            raise ValueError("max_concurrent_jobs must be at least 1")
        self._max_concurrent_jobs = max_concurrent_jobs
        self._queue: asyncio.Queue[TaggingJob | None] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._pending_ids: set[int] = set()
        self._pending_lock = asyncio.Lock()
        self._tagger: DocumentTagger | None = None
        self._store: ProcessedDocumentStore | None = None
        self._run_job: Callable[
            [DocumentTagger, ProcessedDocumentStore, int, WebhookPayload],
            TaggingResult,
        ] | None = None

    def bind(
        self,
        tagger: DocumentTagger,
        store: ProcessedDocumentStore,
        run_job: Callable[
            [DocumentTagger, ProcessedDocumentStore, int, WebhookPayload],
            TaggingResult,
        ],
    ) -> None:
        """Attach runtime dependencies used by worker coroutines."""
        self._tagger = tagger
        self._store = store
        self._run_job = run_job

    async def start(self) -> None:
        """Start worker coroutines that drain the queue."""
        if self._tagger is None or self._store is None or self._run_job is None:
            raise RuntimeError("TaggingJobQueue must be bound before start()")
        for worker_id in range(self._max_concurrent_jobs):
            self._workers.append(asyncio.create_task(self._worker(worker_id)))

    async def stop(self) -> None:
        """Signal workers to exit and wait for them to finish."""
        for _ in self._workers:
            await self._queue.put(None)
        if self._workers:
            await asyncio.gather(*self._workers)
        self._workers.clear()

    @property
    def pending_count(self) -> int:
        """Number of document IDs currently queued or running."""
        return len(self._pending_ids)

    def queued_count(self) -> int:
        """Approximate number of jobs waiting for a worker."""
        return self._queue.qsize()

    async def submit(self, document_id: int, payload: WebhookPayload) -> bool:
        """Enqueue a job. Returns False when the document is already pending."""
        async with self._pending_lock:
            if document_id in self._pending_ids:
                return False
            self._pending_ids.add(document_id)

        await self._queue.put(TaggingJob(document_id=document_id, payload=payload))
        logger.info(
            "Enqueued tagging job for document %s (pending=%s, queued=%s)",
            document_id,
            self.pending_count,
            self.queued_count(),
        )
        return True

    async def _worker(self, worker_id: int) -> None:
        """Process jobs from the queue using a thread for blocking agent work."""
        assert self._tagger is not None
        assert self._store is not None
        assert self._run_job is not None

        while True:
            job = await self._queue.get()
            try:
                if job is None:
                    return

                logger.info(
                    "Worker %s started tagging job for document %s",
                    worker_id,
                    job.document_id,
                )
                result = await asyncio.to_thread(
                    self._run_job,
                    self._tagger,
                    self._store,
                    job.document_id,
                    job.payload,
                )
                logger.info(
                    "Worker %s finished document %s with status %s",
                    worker_id,
                    job.document_id,
                    result.status,
                )
            finally:
                if job is not None:
                    async with self._pending_lock:
                        self._pending_ids.discard(job.document_id)
                self._queue.task_done()
