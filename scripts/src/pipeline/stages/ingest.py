"""Stage 2: Trelent API ingestion."""

import logging
from pathlib import Path

from ..models import FileStatus, PipelineStage
from ..progress import ProgressTracker
from ...clients.trelent import TrelentClient, TrelentError
from ...storage.database import Database

logger = logging.getLogger(__name__)


class IngestStage:
    """
    Stage 2: Ingest files through Trelent API.

    - Sends files to Trelent for conversion
    - Polls for completion
    - Stores markdown results
    - Continues on individual file failures
    """

    def __init__(
        self,
        db: Database,
        trelent: TrelentClient,
        progress: ProgressTracker,
    ):
        self.db = db
        self.trelent = trelent
        self.progress = progress

    async def process(self, batch_id: str, file_ids: list[str]) -> list[str]:
        """
        Process files through Trelent ingestion.

        Args:
            batch_id: The batch ID
            file_ids: List of file IDs to process

        Returns:
            List of successfully ingested file IDs
        """
        await self.progress.start_stage(PipelineStage.INGESTING, len(file_ids))

        successful_ids = []
        processed = 0
        failed = 0

        for file_id in file_ids:
            file_record = await self.db.get_file(file_id)
            if not file_record:
                logger.warning(f"File record not found: {file_id}")
                failed += 1
                continue

            filename = file_record["filename"]
            stored_path = file_record["stored_path"]

            try:
                # Update status to ingesting
                await self.db.update_file(file_id, status=FileStatus.INGESTING.value)

                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    current_file=filename,
                    message=f"Ingesting {filename}...",
                )

                is_text_file = filename.lower().endswith(('.txt', '.text'))

                # Text files: read directly without Trelent API
                if is_text_file:
                    logger.info(f"Reading text file directly: {filename}")
                    markdown = Path(stored_path).read_text(encoding='utf-8', errors='ignore')
                else:
                    # Other files: use Trelent API
                    async with self.trelent:
                        markdown = await self.trelent.ingest_file(
                            Path(stored_path),
                            poll_interval=3.0,
                            max_wait=300.0,
                        )

                # Update with markdown result
                logger.info(f"Saving markdown for {filename}: {len(markdown)} characters")
                await self.db.update_file(
                    file_id,
                    status=FileStatus.INGESTED.value,
                    markdown=markdown,
                )

                successful_ids.append(file_id)
                processed += 1

                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    current_file=filename,
                    message=f"Ingested {filename}",
                )

                logger.info(f"Successfully ingested: {filename}")

            except TrelentError as e:
                logger.error(f"Trelent error for {filename}: {e}")
                await self.db.update_file(
                    file_id,
                    status=FileStatus.FAILED.value,
                    error_message=str(e),
                )
                failed += 1

                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    message=f"Failed: {filename} - {str(e)[:50]}",
                )

            except Exception as e:
                logger.error(f"Unexpected error ingesting {filename}: {e}")
                await self.db.update_file(
                    file_id,
                    status=FileStatus.FAILED.value,
                    error_message=f"Unexpected error: {e}",
                )
                failed += 1

                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    message=f"Error: {filename}",
                )

        logger.info(
            f"Ingest stage complete: {len(successful_ids)} ingested, {failed} failed"
        )
        return successful_ids
