"""Stage 1: File upload and validation."""

import logging
import uuid
from pathlib import Path
from typing import BinaryIO

from ..models import FileStatus, PipelineStage
from ..progress import ProgressTracker
from ...storage.database import Database
from ...storage.file_store import FileStore

logger = logging.getLogger(__name__)


class UploadStage:
    """
    Stage 1: Upload and validate files.

    - Validates file types
    - Stores files locally
    - Creates database records
    """

    def __init__(
        self,
        db: Database,
        file_store: FileStore,
        progress: ProgressTracker,
    ):
        self.db = db
        self.file_store = file_store
        self.progress = progress

    async def process(
        self,
        batch_id: str,
        files: list[tuple[str, bytes]],  # (filename, content)
    ) -> list[str]:
        """
        Process uploaded files.

        Args:
            batch_id: The batch ID
            files: List of (filename, content) tuples

        Returns:
            List of created file IDs
        """
        await self.progress.start_stage(PipelineStage.UPLOADING, len(files))

        file_ids = []
        processed = 0
        failed = 0

        for filename, content in files:
            try:
                # Validate and store file
                if not self.file_store.validate_file(filename):
                    logger.warning(f"Skipping invalid file type: {filename}")
                    failed += 1
                    await self.progress.update_item_progress(
                        processed=processed,
                        failed=failed,
                        message=f"Skipped {filename} (invalid type)",
                    )
                    continue

                # Store file
                stored_path = await self.file_store.store_upload(
                    batch_id, filename, content
                )

                # Create database record
                file_id = str(uuid.uuid4())
                await self.db.create_file(
                    file_id=file_id,
                    batch_id=batch_id,
                    filename=filename,
                    original_path=filename,
                    stored_path=str(stored_path),
                )

                file_ids.append(file_id)
                processed += 1

                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    current_file=filename,
                    message=f"Uploaded {filename}",
                )

            except Exception as e:
                logger.error(f"Failed to upload {filename}: {e}")
                failed += 1
                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    message=f"Failed to upload {filename}",
                )

        logger.info(
            f"Upload stage complete: {processed} uploaded, {failed} failed"
        )
        return file_ids
