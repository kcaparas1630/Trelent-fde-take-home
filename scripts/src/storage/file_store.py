"""File storage management for uploads and outputs."""

import logging
import shutil
from pathlib import Path
from typing import Optional

from ..utils.config import settings

logger = logging.getLogger(__name__)

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".txt",
    ".html",
    ".htm",
    ".rtf",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".csv",
}


class FileStoreError(Exception):
    """Exception for file storage errors."""

    pass


class FileStore:
    """
    Manages file storage for uploads and generated outputs.

    Organizes files by batch ID for easy cleanup and retrieval.
    """

    def __init__(
        self,
        uploads_dir: Optional[Path] = None,
        outputs_dir: Optional[Path] = None,
    ):
        self.uploads_dir = uploads_dir or settings.uploads_dir
        self.outputs_dir = outputs_dir or settings.outputs_dir

        # Ensure directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        ext = Path(filename).suffix.lower()
        return ext in ALLOWED_EXTENSIONS

    def get_batch_upload_dir(self, batch_id: str) -> Path:
        """Get the upload directory for a batch."""
        batch_dir = self.uploads_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        return batch_dir

    def get_batch_output_dir(self, batch_id: str) -> Path:
        """Get the output directory for a batch."""
        batch_dir = self.outputs_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        return batch_dir

    async def store_upload(
        self,
        batch_id: str,
        filename: str,
        content: bytes,
    ) -> Path:
        """
        Store an uploaded file.

        Args:
            batch_id: The batch this file belongs to
            filename: Original filename
            content: File content as bytes

        Returns:
            Path to the stored file

        Raises:
            FileStoreError: If file type not allowed or storage fails
        """
        if not self.validate_file(filename):
            raise FileStoreError(
                f"File type not allowed: {filename}. "
                f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        batch_dir = self.get_batch_upload_dir(batch_id)
        file_path = batch_dir / filename

        # Handle duplicate filenames
        counter = 1
        original_stem = file_path.stem
        while file_path.exists():
            file_path = batch_dir / f"{original_stem}_{counter}{file_path.suffix}"
            counter += 1

        try:
            file_path.write_bytes(content)
            logger.info(f"Stored upload: {file_path}")
            return file_path
        except IOError as e:
            raise FileStoreError(f"Failed to store file: {e}") from e

    async def store_output(
        self,
        batch_id: str,
        slug: str,
        html_content: str,
    ) -> Path:
        """
        Store a generated HTML guide.

        Args:
            batch_id: The batch this guide belongs to
            slug: URL-friendly name for the guide
            html_content: Complete HTML content

        Returns:
            Path to the stored HTML file
        """
        batch_dir = self.get_batch_output_dir(batch_id)
        file_path = batch_dir / f"{slug}.html"

        try:
            file_path.write_text(html_content, encoding="utf-8")
            logger.info(f"Stored output: {file_path}")
            return file_path
        except IOError as e:
            raise FileStoreError(f"Failed to store output: {e}") from e

    def get_upload(self, batch_id: str, filename: str) -> Optional[Path]:
        """Get path to an uploaded file if it exists."""
        file_path = self.uploads_dir / batch_id / filename
        return file_path if file_path.exists() else None

    def get_output(self, batch_id: str, slug: str) -> Optional[Path]:
        """Get path to an output file if it exists."""
        file_path = self.outputs_dir / batch_id / f"{slug}.html"
        return file_path if file_path.exists() else None

    def read_output(self, batch_id: str, slug: str) -> Optional[str]:
        """Read HTML content from an output file."""
        file_path = self.get_output(batch_id, slug)
        if file_path:
            return file_path.read_text(encoding="utf-8")
        return None

    def list_batch_uploads(self, batch_id: str) -> list[Path]:
        """List all uploaded files for a batch."""
        batch_dir = self.uploads_dir / batch_id
        if not batch_dir.exists():
            return []
        return [
            f for f in batch_dir.iterdir() if f.is_file() and self.validate_file(f.name)
        ]

    def list_batch_outputs(self, batch_id: str) -> list[Path]:
        """List all output files for a batch."""
        batch_dir = self.outputs_dir / batch_id
        if not batch_dir.exists():
            return []
        return [f for f in batch_dir.iterdir() if f.is_file() and f.suffix == ".html"]

    def delete_batch(self, batch_id: str):
        """Delete all files for a batch (uploads and outputs)."""
        uploads = self.uploads_dir / batch_id
        outputs = self.outputs_dir / batch_id

        if uploads.exists():
            shutil.rmtree(uploads)
            logger.info(f"Deleted uploads for batch: {batch_id}")

        if outputs.exists():
            shutil.rmtree(outputs)
            logger.info(f"Deleted outputs for batch: {batch_id}")

    def get_allowed_extensions(self) -> list[str]:
        """Get list of allowed file extensions."""
        return sorted(ALLOWED_EXTENSIONS)
