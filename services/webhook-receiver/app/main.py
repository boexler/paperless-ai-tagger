import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.config import Settings, settings
from app.dedup import ProcessedDocumentStore
from app.models import WebhookPayload, extract_document_id
from app.tagger import DocumentTagger, TaggingResult

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def create_store(app_settings: Settings) -> ProcessedDocumentStore:
    store_path = Path(app_settings.data_dir) / "processed_documents.json"
    ttl_seconds = app_settings.dedup_ttl_hours * 3600
    return ProcessedDocumentStore(store_path, ttl_seconds=ttl_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = settings
    app.state.store = create_store(settings)
    app.state.tagger = DocumentTagger(settings)
    logger.info("Webhook receiver started")
    yield
    logger.info("Webhook receiver stopped")


app = FastAPI(
    title="Paperless AI Tagger",
    description="Webhook receiver that tags Paperless documents via Cursor SDK + PaperlessMCP",
    version="0.1.0",
    lifespan=lifespan,
)


def verify_secret(request: Request, secret: str | None) -> None:
    expected = request.app.state.settings.webhook_secret
    provided = secret or request.headers.get("X-Webhook-Secret")
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


def run_tagging_job(
    tagger: DocumentTagger,
    store: ProcessedDocumentStore,
    document_id: int,
    payload: WebhookPayload,
) -> TaggingResult:
    result = tagger.tag_document(
        document_id=document_id,
        doc_title=payload.doc_title,
        correspondent=payload.correspondent,
        document_type=payload.document_type,
        doc_url=payload.doc_url,
    )
    if result.status == "finished":
        store.mark_processed(document_id)
    return result


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    secret: str | None = Query(default=None),
) -> JSONResponse:
    verify_secret(request, secret)

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    payload = WebhookPayload.from_body(body)
    document_id = extract_document_id(payload.doc_url)
    if document_id is None:
        raise HTTPException(
            status_code=400,
            detail="Could not extract document ID from doc_url. Ensure PAPERLESS_URL is set in Paperless.",
        )

    store: ProcessedDocumentStore = request.app.state.store
    if store.was_processed_recently(document_id):
        logger.info("Skipping document %s (already processed recently)", document_id)
        return JSONResponse(
            status_code=202,
            content={
                "status": "skipped",
                "document_id": document_id,
                "reason": "already_processed",
            },
        )

    tagger: DocumentTagger = request.app.state.tagger
    background_tasks.add_task(run_tagging_job, tagger, store, document_id, payload)

    logger.info("Queued tagging job for document %s", document_id)
    return JSONResponse(
        status_code=202,
        content={
            "status": "queued",
            "document_id": document_id,
        },
    )


@app.post("/webhook/sync")
async def webhook_sync(
    request: Request,
    secret: str | None = Query(default=None),
) -> JSONResponse:
    """Synchronous endpoint for debugging and smoke tests."""
    verify_secret(request, secret)

    body = await request.json()
    payload = WebhookPayload.from_body(body)
    document_id = extract_document_id(payload.doc_url)
    if document_id is None:
        raise HTTPException(status_code=400, detail="Could not extract document ID from doc_url")

    tagger: DocumentTagger = request.app.state.tagger
    store: ProcessedDocumentStore = request.app.state.store
    result = run_tagging_job(tagger, store, document_id, payload)

    status_code = 200 if result.status == "finished" else 500
    return JSONResponse(
        status_code=status_code,
        content={
            "status": result.status,
            "document_id": result.document_id,
            "run_id": result.run_id,
            "summary": result.summary,
            "error": result.error,
        },
    )
