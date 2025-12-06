"""Progress tracking for pipeline stages."""

import logging
from typing import Optional

from .models import BatchProgress, BatchStatus, PipelineStage
from ..storage.database import Database

logger = logging.getLogger(__name__)


# Progress ranges for each stage (as percentages)
STAGE_PROGRESS = {
    PipelineStage.PENDING: (0.0, 0.0),
    PipelineStage.UPLOADING: (0.0, 5.0),
    PipelineStage.INGESTING: (5.0, 38.0),  # 33% of work
    PipelineStage.GROUPING: (38.0, 45.0),  # 7% of work
    PipelineStage.REWRITING: (45.0, 85.0),  # 40% of work
    PipelineStage.GENERATING: (85.0, 100.0),  # 15% of work
    PipelineStage.COMPLETED: (100.0, 100.0),
}


class ProgressTracker:
    """
    Tracks and persists pipeline progress.

    Calculates overall progress based on current stage and items processed.
    """

    def __init__(self, db: Database, batch_id: str):
        self.db = db
        self.batch_id = batch_id
        self._current_stage = PipelineStage.PENDING
        self._total_items = 0
        self._processed_items = 0
        self._failed_items = 0
        self._current_file: Optional[str] = None
        self._message: Optional[str] = None

    async def initialize(self, total_files: int):
        """Initialize tracking for a batch."""
        self._total_items = total_files
        self._processed_items = 0
        self._failed_items = 0
        await self._persist()

    async def start_stage(self, stage: PipelineStage, total_items: int = 0):
        """Mark the start of a pipeline stage."""
        self._current_stage = stage
        if total_items > 0:
            self._total_items = total_items
        self._processed_items = 0
        self._message = f"Starting {stage.value}..."
        logger.info(f"Batch {self.batch_id}: Starting stage {stage.value}")
        await self._persist()

    async def update_item_progress(
        self,
        processed: int,
        failed: int = 0,
        current_file: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Update progress within a stage."""
        self._processed_items = processed
        self._failed_items = failed
        self._current_file = current_file
        if message:
            self._message = message
        await self._persist()

    async def complete_stage(self, stage: PipelineStage):
        """Mark a stage as complete."""
        self._current_stage = stage
        self._message = f"Completed {stage.value}"
        await self._persist()

    async def mark_completed(self):
        """Mark the batch as completed."""
        self._current_stage = PipelineStage.COMPLETED
        self._message = "Processing complete"
        status = BatchStatus.COMPLETED
        if self._failed_items > 0:
            status = BatchStatus.PARTIAL_FAILED
            self._current_stage = PipelineStage.PARTIAL_FAILED
        await self._persist(status=status)

    async def mark_failed(self, error_message: str):
        """Mark the batch as failed."""
        self._current_stage = PipelineStage.FAILED
        self._message = error_message
        await self._persist(status=BatchStatus.FAILED, error_message=error_message)

    def calculate_progress(self) -> float:
        """Calculate overall progress percentage."""
        if self._current_stage == PipelineStage.COMPLETED:
            return 100.0

        if self._current_stage == PipelineStage.FAILED:
            return self._calculate_stage_progress()

        return self._calculate_stage_progress()

    def _calculate_stage_progress(self) -> float:
        """Calculate progress within current stage."""
        stage_start, stage_end = STAGE_PROGRESS.get(
            self._current_stage, (0.0, 100.0)
        )
        stage_range = stage_end - stage_start

        if self._total_items == 0:
            item_progress = 0.0
        else:
            item_progress = self._processed_items / self._total_items

        return stage_start + (stage_range * item_progress)

    async def get_progress(self) -> BatchProgress:
        """Get current progress information."""
        batch = await self.db.get_batch(self.batch_id)
        if not batch:
            return BatchProgress(
                batch_id=self.batch_id,
                status=BatchStatus.PENDING,
                stage=PipelineStage.PENDING,
                progress=0.0,
                total_files=0,
                processed_files=0,
                failed_files=0,
            )

        return BatchProgress(
            batch_id=self.batch_id,
            status=BatchStatus(batch.get("status", "pending")),
            stage=PipelineStage(batch.get("current_stage", "pending")),
            progress=batch.get("progress", 0.0),
            total_files=batch.get("total_files", 0),
            processed_files=batch.get("processed_files", 0),
            failed_files=batch.get("failed_files", 0),
            current_file=self._current_file,
            message=self._message,
            error_message=batch.get("error_message"),
        )

    async def _persist(
        self,
        status: Optional[BatchStatus] = None,
        error_message: Optional[str] = None,
    ):
        """Persist progress to database."""
        progress = self.calculate_progress()

        await self.db.update_batch_progress(
            batch_id=self.batch_id,
            progress=progress,
            status=status.value if status else BatchStatus.PROCESSING.value,
            current_stage=self._current_stage.value,
            processed_files=self._processed_items,
            failed_files=self._failed_items,
            error_message=error_message,
        )
