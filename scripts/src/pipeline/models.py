"""Data models for the pipeline."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PipelineStage(str, Enum):
    """Pipeline processing stages."""

    PENDING = "pending"
    UPLOADING = "uploading"
    INGESTING = "ingesting"
    GROUPING = "grouping"
    REWRITING = "rewriting"
    GENERATING = "generating"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class BatchStatus(str, Enum):
    """Batch processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class FileStatus(str, Enum):
    """Individual file processing status."""

    PENDING = "pending"
    INGESTING = "ingesting"
    INGESTED = "ingested"
    FAILED = "failed"


class FileInfo(BaseModel):
    """Information about a file being processed."""

    id: str
    batch_id: str
    filename: str
    original_path: str
    stored_path: Optional[str] = None
    status: FileStatus = FileStatus.PENDING
    trelent_job_id: Optional[str] = None
    markdown: Optional[str] = None
    error_message: Optional[str] = None


class TopicGroup(BaseModel):
    """A group of files organized by topic."""

    id: str
    batch_id: str
    topic: str
    slug: str
    description: str
    file_ids: list[str] = []


class Guide(BaseModel):
    """A generated HTML guide."""

    id: str
    batch_id: str
    topic_group_id: str
    title: str
    description: str
    slug: str
    html_path: Optional[str] = None
    rewritten_content: Optional[str] = None
    status: str = "pending"


class BatchProgress(BaseModel):
    """Progress information for a batch."""

    batch_id: str
    status: BatchStatus
    stage: PipelineStage
    progress: float  # 0.0 to 100.0
    total_files: int
    processed_files: int
    failed_files: int
    current_file: Optional[str] = None
    message: Optional[str] = None
    error_message: Optional[str] = None
