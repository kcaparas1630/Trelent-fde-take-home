"""Stage 1: File upload and validation."""

import hashlib
import logging
import uuid

from ..models import PipelineStage
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
        duplicates = 0

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

                # Check for duplicate by filename first
                existing_file = await self.db.find_file_by_name(filename)
                if existing_file:
                    logger.info(
                        f"Skipping duplicate filename: {filename} "
                        f"(already processed in batch {existing_file['batch_id']})"
                    )
                    processed += 1
                    duplicates += 1
                    await self.progress.update_item_progress(
                        processed=processed,
                        failed=failed,
                        current_file=filename,
                        message=f"Skipped {filename} (duplicate)",
                    )
                    continue

                # Compute content hash for duplicate detection
                content_hash = hashlib.sha256(content).hexdigest()

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
                    content_hash=content_hash,
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
            f"Upload stage complete: {len(file_ids)} new, {duplicates} duplicates, {failed} failed"
        )

        # If all files were duplicates, raise a specific error
        if not file_ids and duplicates > 0:
            if duplicates == 1:
                raise ValueError("File has already been uploaded and processed")
            else:
                raise ValueError(f"All {duplicates} files have already been uploaded and processed")

        return file_ids
