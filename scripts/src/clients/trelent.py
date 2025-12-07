"""Trelent Data Ingestion API client."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx

from ..utils.config import settings

logger = logging.getLogger(__name__)


class TrelentError(Exception):
    """Base exception for Trelent API errors."""

    pass


class TrelentJobError(TrelentError):
    """Exception for job processing errors."""

    pass


class TrelentClient:
    """
    Client for Trelent Data Ingestion API.

    Handles file upload, job creation, polling, and result retrieval.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.api_url = (api_url or settings.trelent_api_url).rstrip("/")
        self.api_token = api_token or settings.trelent_api_token
        self.timeout = timeout

        if not self.api_token:
            raise TrelentError("TRELENT_API_TOKEN is required")

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                },
                timeout=self.timeout,
                follow_redirects=True,
            )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        """Check if the API is healthy."""
        await self._ensure_client()
        try:
            response = await self._client.get("/healthz")
            return response.status_code == 200
        except httpx.HTTPError as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def upload_file(self, file_path: Path) -> str:
        """
        Upload a file to Trelent and return the file ID.

        Args:
            file_path: Path to the file to upload
        Returns:
            File ID for the uploaded file
        """
        await self._ensure_client()

        if not file_path.exists():
            raise TrelentError(f"File not found: {file_path}")

        # Read file content
        file_content = file_path.read_bytes()
        file_name = file_path.name

        # Determine content type
        content_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
            ".html": "text/html",
            ".rtf": "application/rtf",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".ppt": "application/vnd.ms-powerpoint",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
        }
        content_type = content_types.get(
            file_path.suffix.lower(), "application/octet-stream"
        )

        try:
            # Create multipart form data for file upload
            files = {"file": (file_name, file_content, content_type)}

            # Remove content-type header for multipart
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "X-File-Name": file_name,   
            }

            response = await self._client.put(
                "/files/",
                files=files,
                headers=headers,
            )

            if response.status_code not in (200, 201, 202):
                raise TrelentError(
                    f"File upload failed (Step 1): {response.status_code} - {response.text}"
                )

            data = response.json()
            file_id = data.get("id") or data.get("file_id")

            if not file_id:
                logger.warning(f"File upload successful but no ID returned: {data}")
                raise TrelentError(f"No file ID in response: {data}")

            logger.info(f"Uploaded file {file_name} with ID {file_id}")
            return file_id

        except httpx.HTTPError as e:
            raise TrelentError(f"HTTP error uploading file (Step 1): {e}") from e

    async def create_job(self, file_path: Path) -> str:
        """
        Create an ingestion job for a file.

        Args:
            file_path: Path to the file to ingest

        Returns:
            Job ID for tracking

        Raises:
            TrelentError: If job creation fails
        """
        file_id = await self.upload_file(file_path)

        await self._ensure_client()

        job_input = {
            "connector": {
                    "type": "file_upload",
                    "file_ids": [file_id],
            },
            "output": {
                "type": "s3-signed-url",
                "expires_minutes": 5,
            }
            
        }
        # Remove content-type header for multipart
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json", 
        }
        try:
            response = await self._client.post(
                "/jobs/",
                json=job_input,
                headers=headers,
            )

            if response.status_code not in (200, 201, 202):
                raise TrelentError(
                    f"Job creation failed (Step 2): {response.status_code} - {response.text}"
                )
            
            data = response.json()
            job_id = data.get("job_id") or data.get("id")

            if not job_id:
                raise TrelentError(f"No job ID in response: {data}")

            logger.info(f"Created job {job_id} for file {file_path.name}")
            return job_id

        except httpx.HTTPError as e:
            raise TrelentError(f"HTTP error creating job (Step 2): {e}") from e

    async def get_job_status(self, job_id: str) -> dict:
        """
        Get the status of a job.

        Args:
            job_id: The job ID to check

        Returns:
            Job status dict with status, progress, and result (if complete)
        """
        await self._ensure_client()

        try:
            response = await self._client.get(f"/jobs/{job_id}", params={"include_markdown": True})

            if response.status_code == 404:
                raise TrelentError(f"Job not found: {job_id}")

            if response.status_code != 200:
                raise TrelentError(
                    f"Failed to get job status: {response.status_code} - {response.text}"
                )

            return response.json()

        except httpx.HTTPError as e:
            raise TrelentError(f"HTTP error getting job status: {e}") from e

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        max_wait: float = 600.0,
        max_queued_time: float = 60.0,
    ) -> dict:
        """
        Wait for a job to complete.

        Args:
            job_id: The job ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
            max_queued_time: Maximum seconds a job can stay queued before failing

        Returns:
            Completed job data with markdown result

        Raises:
            TrelentJobError: If job fails or times out
        """
        elapsed = 0.0
        queued_time = 0.0
        consecutive_errors = 0
        max_consecutive_errors = 3

        while elapsed < max_wait:
            try:
                status = await self.get_job_status(job_id)
                consecutive_errors = 0  # Reset on successful request

                job_status = status.get("status", "").lower()

                if job_status in ("completed", "complete", "done"):
                    logger.info(f"Job {job_id} completed successfully")
                    return status

                if job_status in ("failed", "error"):
                    error_msg = status.get("error", "Unknown error")
                    errors = status.get("errors")
                    if errors:
                        error_msg = f"{error_msg} - Errors: {errors}"
                    raise TrelentJobError(f"Job {job_id} failed: {error_msg}")

                # Check if job is stuck in queued state
                if job_status == "queued":
                    queued_time += poll_interval
                    if queued_time >= max_queued_time:
                        raise TrelentJobError(
                            f"Job {job_id} stuck in queued state for {queued_time}s. "
                            f"The Trelent service may not be processing jobs."
                        )
                else:
                    queued_time = 0  # Reset if job progresses past queued


            except TrelentJobError:
                # Re-raise job errors immediately
                raise
            except Exception as e:
                consecutive_errors += 1
                logger.warning(
                    f"Error polling job {job_id} (attempt {consecutive_errors}/{max_consecutive_errors}): {e}"
                )

                if consecutive_errors >= max_consecutive_errors:
                    raise TrelentJobError(
                        f"Failed to poll job {job_id} after {consecutive_errors} consecutive errors. "
                        f"Last error: {e}"
                    ) from e

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TrelentJobError(f"Job {job_id} timed out after {max_wait}s")

    async def ingest_file(
        self,
        file_path: Path,
        poll_interval: float = 2.0,
        max_wait: float = 600.0,
        max_queued_time: float = 600.0,
    ) -> str:
        """
        Convenience method to ingest a file and return markdown.

        Args:
            file_path: Path to file to ingest
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
            max_queued_time: Maximum seconds a job can stay queued before failing

        Returns:
            Markdown content from the ingested file
        """
        job_id = await self.create_job(file_path)
        result = await self.wait_for_completion(job_id, poll_interval, max_wait, max_queued_time)

        # Extract markdown from result
        # First try the delivery field (for s3-signed-url output type)
        delivery = result.get("delivery")
        if delivery and isinstance(delivery, dict):
            # Delivery is a dict with file IDs as keys
            # Get the first file's delivery info
            for file_id, file_delivery in delivery.items():
                if isinstance(file_delivery, dict):
                    # First try direct markdown field
                    markdown = file_delivery.get("markdown")
                    if markdown:
                        logger.info(f"Successfully extracted markdown from delivery ({len(markdown)} characters)")
                        return markdown

                    # Then try markdown_delivery with URL
                    markdown_delivery = file_delivery.get("markdown_delivery")
                    if markdown_delivery and isinstance(markdown_delivery, dict):
                        url = markdown_delivery.get("url")
                        if url:
                            logger.info(f"Fetching markdown from delivery URL: {url}")
                            async with httpx.AsyncClient() as client:
                                response = await client.get(url)
                                if response.status_code == 200:
                                    logger.info(f"Successfully fetched markdown from URL ({len(response.text)} characters)")
                                    return response.text
                                else:
                                    logger.warning(f"Failed to fetch from delivery URL: {response.status_code}")

        # Fallback to checking other possible fields
        markdown = (
            result.get("markdown")
            or result.get("result", {}).get("markdown")
            or result.get("output")
            or result.get("content")
        )

        if not markdown:
            logger.warning(f"No markdown in job result: {result}")
            markdown = ""
        else:
            logger.info(f"Successfully extracted markdown ({len(markdown)} characters)")

        return markdown
