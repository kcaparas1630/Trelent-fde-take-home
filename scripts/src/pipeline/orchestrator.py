"""Pipeline orchestrator that coordinates all stages."""

import asyncio
import logging
import uuid
from typing import Optional

from .models import BatchProgress, BatchStatus, PipelineStage
from .progress import ProgressTracker
from .stages import (
    UploadStage,
    IngestStage,
    GroupingStage,
    RewriteStage,
    OutputStage,
)
from ..clients.trelent import TrelentClient
from ..clients.openai_client import OpenAIClient
from ..storage.database import Database
from ..storage.file_store import FileStore

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the document-to-HTML pipeline.

    Coordinates all 5 stages:
    1. Upload & Validation
    2. Trelent Ingestion
    3. Topic Grouping
    4. Content Rewriting
    5. HTML Generation

    NOTE: Multiple batches can run concurrently without blocking.
    Trelent API handles job queuing on their end, so this orchestrator
    doesn't need its own queue. Scalability depends on Trelent's infrastructure.
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        file_store: Optional[FileStore] = None,
        trelent: Optional[TrelentClient] = None,
        openai: Optional[OpenAIClient] = None,
    ):
        self.db = db or Database()
        self.file_store = file_store or FileStore()
        self.trelent = trelent or TrelentClient()
        self.openai = openai or OpenAIClient()

        self._running_batches: dict[str, asyncio.Task] = {}

    async def initialize(self):
        """Initialize all components."""
        await self.db.connect()

    async def shutdown(self):
        """Shutdown all components."""
        # Cancel running batches
        for batch_id, task in self._running_batches.items():
            if not task.done():
                task.cancel()
                logger.warning(f"Cancelled running batch: {batch_id}")

        await self.db.close()

    async def start_batch(
        self,
        files: list[tuple[str, bytes]],
        run_async: bool = True,
    ) -> str:
        """
        Start processing a batch of files.

        Args:
            files: List of (filename, content) tuples
            run_async: If True, run in background task

        Returns:
            Batch ID for tracking progress
        """
        batch_id = str(uuid.uuid4())

        # Create batch record
        await self.db.create_batch(batch_id, len(files))

        logger.info(f"Starting batch {batch_id} with {len(files)} files")

        if run_async:
            # Run in background
            task = asyncio.create_task(self._run_pipeline(batch_id, files))
            self._running_batches[batch_id] = task

            # Clean up when done
            task.add_done_callback(
                lambda t: self._running_batches.pop(batch_id, None)
            )
        else:
            # Run synchronously
            await self._run_pipeline(batch_id, files)

        return batch_id

    async def _run_pipeline(
        self,
        batch_id: str,
        files: list[tuple[str, bytes]],
    ):
        """Run the complete pipeline for a batch."""
        progress = ProgressTracker(self.db, batch_id)
        await progress.initialize(len(files))

        try:
            # Stage 1: Upload
            upload_stage = UploadStage(self.db, self.file_store, progress)
            file_ids = await upload_stage.process(batch_id, files)

            if not file_ids:
                await progress.mark_failed("No valid files to process")
                return

            # Stage 2: Ingest
            ingest_stage = IngestStage(self.db, self.trelent, progress)
            ingested_ids = await ingest_stage.process(batch_id, file_ids)

            if not ingested_ids:
                await progress.mark_failed("All files failed during ingestion")
                return

            # Stage 3: Group
            grouping_stage = GroupingStage(self.db, self.openai, progress)
            group_ids = await grouping_stage.process(batch_id, ingested_ids)

            if not group_ids:
                await progress.mark_failed("Failed to create topic groups")
                return

            # Stage 4: Rewrite
            rewrite_stage = RewriteStage(self.db, self.openai, progress)
            guide_ids = await rewrite_stage.process(batch_id, group_ids)

            if not guide_ids:
                await progress.mark_failed("All guides failed during rewriting")
                return

            # Stage 5: Output
            output_stage = OutputStage(
                self.db, self.openai, self.file_store, progress
            )
            completed_ids = await output_stage.process(batch_id, guide_ids)

            # Mark complete
            await progress.mark_completed()

            logger.info(
                f"Batch {batch_id} completed: {len(completed_ids)} guides generated"
            )

        except asyncio.CancelledError:
            logger.warning(f"Batch {batch_id} was cancelled")
            await progress.mark_failed("Processing was cancelled")
            raise

        except Exception as e:
            logger.error(f"Pipeline failed for batch {batch_id}: {e}", exc_info=True)
            await progress.mark_failed(str(e))

    async def get_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """Get progress for a batch."""
        batch = await self.db.get_batch(batch_id)
        if not batch:
            return None

        return BatchProgress(
            batch_id=batch_id,
            status=BatchStatus(batch.get("status", "pending")),
            stage=PipelineStage(batch.get("current_stage") or "pending"),
            progress=batch.get("progress", 0.0),
            total_files=batch.get("total_files", 0),
            processed_files=batch.get("processed_files", 0),
            failed_files=batch.get("failed_files", 0),
            error_message=batch.get("error_message"),
        )

    async def list_batches(self, limit: int = 50) -> list[dict]:
        """List all batches."""
        return await self.db.list_batches(limit)

    async def get_batch_files(self, batch_id: str) -> list[dict]:
        """Get all files for a batch."""
        return await self.db.list_batch_files(batch_id)

    async def get_failed_files(self, batch_id: str) -> list[dict]:
        """Get failed files for a batch."""
        return await self.db.get_failed_files(batch_id)

    async def retry_failed(self, batch_id: str) -> bool:
        """
        Retry failed files in a batch.

        Returns:
            True if retry started, False if no failed files
        """
        failed_files = await self.db.get_failed_files(batch_id)
        if not failed_files:
            return False

        # Get file content from stored paths
        files_to_retry = []
        for file_record in failed_files:
            stored_path = file_record.get("stored_path")
            if stored_path:
                from pathlib import Path

                path = Path(stored_path)
                if path.exists():
                    content = path.read_bytes()
                    files_to_retry.append((file_record["filename"], content))

        if not files_to_retry:
            return False

        # Start new batch with failed files
        # Note: In production, we might want to retry within the same batch
        await self.start_batch(files_to_retry, run_async=True)
        return True

    async def list_guides(
        self, batch_id: Optional[str] = None
    ) -> list[dict]:
        """List completed guides."""
        return await self.db.list_guides(batch_id)

    async def get_guide(self, guide_id: str) -> Optional[dict]:
        """Get a single guide."""
        return await self.db.get_guide(guide_id)

    async def get_guide_html(self, guide_id: str) -> Optional[str]:
        """Get the HTML content for a guide."""
        guide = await self.db.get_guide(guide_id)
        if not guide or not guide.get("html_path"):
            return None

        from pathlib import Path

        html_path = Path(guide["html_path"])
        if html_path.exists():
            return html_path.read_text(encoding="utf-8")
        return None
