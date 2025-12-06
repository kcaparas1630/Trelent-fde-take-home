"""Stage 4: OpenAI content rewriting."""

import logging
import uuid

from ..models import PipelineStage
from ..progress import ProgressTracker
from ...clients.openai_client import OpenAIClient, OpenAIError
from ...storage.database import Database

logger = logging.getLogger(__name__)


class RewriteStage:
    """
    Stage 4: Rewrite content using OpenAI.

    - Takes grouped files
    - Combines content within each group
    - Rewrites for clarity and consistency
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

    async def process(self, batch_id: str, group_ids: list[str]) -> list[str]:
        """
        Rewrite content for each topic group.

        Args:
            batch_id: The batch ID
            group_ids: List of topic group IDs

        Returns:
            List of created guide IDs
        """
        await self.progress.start_stage(PipelineStage.REWRITING, len(group_ids))

        if not group_ids:
            logger.warning("No groups to rewrite")
            return []

        guide_ids = []
        processed = 0
        failed = 0

        for group_id in group_ids:
            group = await self.db.get_topic_group(group_id)
            if not group:
                logger.warning(f"Topic group not found: {group_id}")
                failed += 1
                continue

            topic = group["topic"]
            description = group.get("description", "")
            file_ids = group.get("file_ids", [])

            try:
                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    current_file=topic,
                    message=f"Rewriting: {topic}...",
                )

                # Gather markdown content from files
                markdown_contents = []
                for file_id in file_ids:
                    file_record = await self.db.get_file(file_id)
                    if file_record and file_record.get("markdown"):
                        markdown_contents.append(file_record["markdown"])

                if not markdown_contents:
                    logger.warning(f"No content for group: {topic}")
                    failed += 1
                    continue

                # Rewrite content
                rewritten = await self.openai.rewrite_content(
                    markdown_contents=markdown_contents,
                    topic=topic,
                    topic_description=description,
                )

                # Create guide record
                guide_id = str(uuid.uuid4())
                await self.db.create_guide(
                    guide_id=guide_id,
                    batch_id=batch_id,
                    topic_group_id=group_id,
                    title=topic,
                    description=description,
                    slug=group["slug"],
                )

                # Store rewritten content
                await self.db.update_guide(
                    guide_id=guide_id,
                    rewritten_content=rewritten,
                    status="rewritten",
                )

                guide_ids.append(guide_id)
                processed += 1

                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    message=f"Rewritten: {topic}",
                )

                logger.info(f"Successfully rewrote: {topic}")

            except OpenAIError as e:
                logger.error(f"OpenAI error rewriting {topic}: {e}")
                failed += 1
                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    message=f"Failed: {topic}",
                )

            except Exception as e:
                logger.error(f"Unexpected error rewriting {topic}: {e}")
                failed += 1
                await self.progress.update_item_progress(
                    processed=processed,
                    failed=failed,
                    message=f"Error: {topic}",
                )

        logger.info(
            f"Rewrite stage complete: {len(guide_ids)} rewritten, {failed} failed"
        )
        return guide_ids
