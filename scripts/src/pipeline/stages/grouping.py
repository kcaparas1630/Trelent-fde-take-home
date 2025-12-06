"""Stage 3: Topic analysis and grouping."""

import logging
import re
import uuid

from ..models import PipelineStage
from ..progress import ProgressTracker
from ...clients.openai_client import OpenAIClient
from ...storage.database import Database

logger = logging.getLogger(__name__)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:50]  # Limit length


class GroupingStage:
    """
    Stage 3: Analyze content and group by topic.

    - Analyzes markdown content from all files
    - Uses OpenAI to identify topics
    - Groups files by topic
    """

    def __init__(
        self,
        db: Database,
        openai: OpenAIClient,
        progress: ProgressTracker,
    ):
        self.db = db
        self.openai = openai
        self.progress = progress

    async def process(self, batch_id: str, file_ids: list[str]) -> list[str]:
        """
        Group files by topic.

        Args:
            batch_id: The batch ID
            file_ids: List of successfully ingested file IDs

        Returns:
            List of created topic group IDs
        """
        await self.progress.start_stage(PipelineStage.GROUPING, 1)

        if not file_ids:
            logger.warning("No files to group")
            return []

        try:
            # Gather documents for analysis
            documents = []
            for file_id in file_ids:
                file_record = await self.db.get_file(file_id)
                if file_record and file_record.get("markdown"):
                    documents.append(
                        {
                            "id": file_id,
                            "filename": file_record["filename"],
                            "markdown": file_record["markdown"],
                        }
                    )

            if not documents:
                logger.warning("No documents with markdown content to group")
                return []

            await self.progress.update_item_progress(
                processed=0,
                message="Analyzing content topics...",
            )

            # Analyze topics
            topic_groups = await self.openai.analyze_topics(documents)

            # Create topic group records
            group_ids = []
            for group_data in topic_groups:
                group_id = str(uuid.uuid4())

                # Get file IDs that exist in our document list
                valid_file_ids = [
                    fid
                    for fid in group_data.get("document_ids", [])
                    if fid in file_ids
                ]

                if not valid_file_ids:
                    continue

                topic = group_data.get("topic", "Documentation")
                slug = group_data.get("slug") or slugify(topic)
                description = group_data.get("description", "")

                await self.db.create_topic_group(
                    group_id=group_id,
                    batch_id=batch_id,
                    topic=topic,
                    slug=slug,
                    description=description,
                    file_ids=valid_file_ids,
                )

                group_ids.append(group_id)
                logger.info(
                    f"Created topic group '{topic}' with {len(valid_file_ids)} files"
                )

            await self.progress.update_item_progress(
                processed=1,
                message=f"Created {len(group_ids)} topic groups",
            )

            logger.info(f"Grouping stage complete: {len(group_ids)} groups created")
            return group_ids

        except Exception as e:
            logger.error(f"Error in grouping stage: {e}")
            # Fallback: create single group with all files
            group_id = str(uuid.uuid4())
            await self.db.create_topic_group(
                group_id=group_id,
                batch_id=batch_id,
                topic="Documentation",
                slug="documentation",
                description="General documentation",
                file_ids=file_ids,
            )
            return [group_id]
