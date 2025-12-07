"""API route definitions."""

import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from slowapi import Limiter

from .dependencies import get_orchestrator
from ..pipeline.models import BatchProgress, BatchStatus, PipelineStage

logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting.

    Currently uses IP address. When authentication is added,
    replace this with user ID or API key.
    """
    # TODO: When authentication is added, use this instead:
    # if hasattr(request.state, "user") and request.state.user:
    #     return f"user:{request.state.user.id}"
    # return "anonymous"

    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_user_identifier)


# ==================== Response Models ====================


class BatchResponse(BaseModel):
    """Response for batch operations."""

    batch_id: str
    status: str
    message: str


class ProgressResponse(BaseModel):
    """Response for progress queries."""

    batch_id: str
    status: str
    stage: str
    progress: float
    total_files: int
    processed_files: int
    failed_files: int
    message: Optional[str] = None
    error_message: Optional[str] = None


class FileResponse(BaseModel):
    """Response for file information."""

    id: str
    filename: str
    status: str
    error_message: Optional[str] = None


class GuideResponse(BaseModel):
    """Response for guide information."""

    id: str
    title: str
    description: str
    slug: str
    status: str
    batch_id: str


class GuidesListResponse(BaseModel):
    """Response for guides list."""

    guides: list[GuideResponse]
    total: int


# ==================== Health Check ====================


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/debug/trelent")
async def debug_trelent():
    """Debug endpoint to test Trelent API connectivity."""
    from ..clients.trelent import TrelentClient

    try:
        async with TrelentClient() as client:
            is_healthy = await client.health_check()
            return {
                "trelent_api_accessible": is_healthy,
                "trelent_url": client.api_url,
                "has_token": bool(client.api_token),
            }
    except Exception as e:
        return {
            "error": str(e),
            "trelent_api_accessible": False,
        }


# ==================== Upload ====================


@router.post("/upload", response_model=BatchResponse)
@limiter.limit("10/minute")
async def upload_files(request: Request, files: list[UploadFile] = File(...)):
    """
    Upload files and start processing.

    Accepts multiple files (PDF, DOCX, DOC, TXT, etc.) and starts
    the pipeline to convert them to HTML guides.

    Rate limit: 10 requests per minute per IP to prevent API overload.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    orchestrator = get_orchestrator()

    # Read file contents
    file_data = []
    for upload_file in files:
        if not upload_file.filename:
            continue
        content = await upload_file.read()
        file_data.append((upload_file.filename, content))

    if not file_data:
        raise HTTPException(status_code=400, detail="No valid files provided")

    # Start batch processing
    batch_id = await orchestrator.start_batch(file_data, run_async=True)

    return BatchResponse(
        batch_id=batch_id,
        status="processing",
        message=f"Started processing {len(file_data)} files",
    )


# ==================== Batch Operations ====================


@router.get("/batches")
async def list_batches(limit: int = 50):
    """List all batches."""
    orchestrator = get_orchestrator()
    batches = await orchestrator.list_batches(limit)

    return {
        "batches": [
            {
                "id": b["id"],
                "status": b["status"],
                "progress": b["progress"],
                "total_files": b["total_files"],
                "processed_files": b["processed_files"],
                "failed_files": b["failed_files"],
                "created_at": b["created_at"],
            }
            for b in batches
        ],
        "total": len(batches),
    }


@router.get("/batches/{batch_id}", response_model=ProgressResponse)
async def get_batch_progress(batch_id: str):
    """Get progress for a specific batch."""
    orchestrator = get_orchestrator()
    progress = await orchestrator.get_progress(batch_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Batch not found")

    return ProgressResponse(
        batch_id=progress.batch_id,
        status=progress.status.value,
        stage=progress.stage.value,
        progress=progress.progress,
        total_files=progress.total_files,
        processed_files=progress.processed_files,
        failed_files=progress.failed_files,
        message=progress.message,
        error_message=progress.error_message,
    )


@router.get("/batches/{batch_id}/files")
async def get_batch_files(batch_id: str):
    """Get all files in a batch."""
    orchestrator = get_orchestrator()
    files = await orchestrator.get_batch_files(batch_id)

    return {
        "files": [
            FileResponse(
                id=f["id"],
                filename=f["filename"],
                status=f["status"],
                error_message=f.get("error_message"),
            )
            for f in files
        ],
        "total": len(files),
    }


@router.get("/batches/{batch_id}/failed")
async def get_failed_files(batch_id: str):
    """Get failed files in a batch."""
    orchestrator = get_orchestrator()
    failed = await orchestrator.get_failed_files(batch_id)

    return {
        "files": [
            FileResponse(
                id=f["id"],
                filename=f["filename"],
                status=f["status"],
                error_message=f.get("error_message"),
            )
            for f in failed
        ],
        "total": len(failed),
    }


@router.post("/batches/{batch_id}/retry", response_model=BatchResponse)
async def retry_failed_files(batch_id: str):
    """Retry failed files in a batch."""
    orchestrator = get_orchestrator()
    success = await orchestrator.retry_failed(batch_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="No failed files to retry or files not found",
        )

    return BatchResponse(
        batch_id=batch_id,
        status="retrying",
        message="Retry started for failed files",
    )


# ==================== Guide Operations ====================


@router.get("/guides", response_model=GuidesListResponse)
async def list_guides(batch_id: Optional[str] = None):
    """List completed guides."""
    orchestrator = get_orchestrator()
    guides = await orchestrator.list_guides(batch_id)

    return GuidesListResponse(
        guides=[
            GuideResponse(
                id=g["id"],
                title=g["title"],
                description=g.get("description", ""),
                slug=g["slug"],
                status=g["status"],
                batch_id=g["batch_id"],
            )
            for g in guides
        ],
        total=len(guides),
    )


@router.get("/guides/{guide_id}")
async def get_guide(guide_id: str):
    """Get a specific guide."""
    orchestrator = get_orchestrator()
    guide = await orchestrator.get_guide(guide_id)

    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")

    return GuideResponse(
        id=guide["id"],
        title=guide["title"],
        description=guide.get("description", ""),
        slug=guide["slug"],
        status=guide["status"],
        batch_id=guide["batch_id"],
    )


@router.get("/guides/{guide_id}/html", response_class=HTMLResponse)
async def get_guide_html(guide_id: str):
    """Get the HTML content of a guide."""
    orchestrator = get_orchestrator()
    html = await orchestrator.get_guide_html(guide_id)

    if not html:
        raise HTTPException(status_code=404, detail="Guide HTML not found")

    return HTMLResponse(content=html)


# ==================== Utility ====================


@router.get("/allowed-extensions")
async def get_allowed_extensions():
    """Get list of allowed file extensions."""
    from ..storage.file_store import ALLOWED_EXTENSIONS

    return {"extensions": sorted(ALLOWED_EXTENSIONS)}
