"""OpenAI API client wrapper for content rewriting."""

import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from ..utils.config import settings
from ..utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    """Base exception for OpenAI API errors."""

    pass


class OpenAIClient:
    """
    Client for OpenAI API.

    Handles content rewriting, topic grouping, and HTML generation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model

        if not self.api_key:
            raise OpenAIError("OPENAI_API_KEY is required")

        self._client = AsyncOpenAI(api_key=self.api_key)

    async def analyze_topics(
        self,
        documents: list[dict],
    ) -> list[dict]:
        """
        Analyze documents and group them by topic.

        Args:
            documents: List of dicts with 'id', 'filename', 'markdown' keys

        Returns:
            List of topic groups with assigned document IDs
        """
        # Create summaries for analysis
        summaries = []
        for doc in documents:
            # Take first 500 chars as summary
            preview = doc["markdown"][:500] if doc["markdown"] else ""
            summaries.append(
                {"id": doc["id"], "filename": doc["filename"], "preview": preview}
            )

        prompt = f"""Analyze these documents and group them by topic for a documentation library.

Documents:
{json.dumps(summaries, indent=2)}

Create logical topic groups based on the content. Each document should be assigned to exactly one group.

Return a JSON array of topic groups in this format:
[
  {{
    "topic": "Getting Started",
    "slug": "getting-started",
    "description": "Introduction and setup guides",
    "document_ids": ["id1", "id2"]
  }}
]

Common topics might include: Getting Started, Installation, Configuration, API Reference, Tutorials, Troubleshooting, FAQ, Best Practices, etc.

If there's only one document or documents don't have clear topics, create a single "General" group.

Return ONLY the JSON array, no other text."""

        try:
            response = await retry_with_backoff(
                self._call_completion,
                prompt,
                max_retries=3,
            )

            # Parse JSON response
            try:
                groups = json.loads(response)
                if not isinstance(groups, list):
                    groups = [groups]
                return groups
            except json.JSONDecodeError:
                # Try to extract JSON from response
                start = response.find("[")
                end = response.rfind("]") + 1
                if start >= 0 and end > start:
                    groups = json.loads(response[start:end])
                    return groups

                # Fallback: single group with all documents
                logger.warning("Could not parse topic groups, using fallback")
                return [
                    {
                        "topic": "Documentation",
                        "slug": "documentation",
                        "description": "General documentation",
                        "document_ids": [doc["id"] for doc in documents],
                    }
                ]

        except Exception as e:
            logger.error(f"Topic analysis failed: {e}")
            # Fallback
            return [
                {
                    "topic": "Documentation",
                    "slug": "documentation",
                    "description": "General documentation",
                    "document_ids": [doc["id"] for doc in documents],
                }
            ]

    async def rewrite_content(
        self,
        markdown_contents: list[str],
        topic: str,
        topic_description: str,
    ) -> str:
        """
        Rewrite and combine markdown content into a clean guide.

        Args:
            markdown_contents: List of markdown strings to combine
            topic: Topic name for the guide
            topic_description: Description of the topic

        Returns:
            Rewritten content as clean markdown
        """
        combined = "\n\n---\n\n".join(markdown_contents)

        prompt = f"""You are a technical writer creating clean, professional documentation.

Topic: {topic}
Description: {topic_description}

Source Content:
{combined}

Please rewrite this content as a clean, well-organized guide following these rules:

1. Use clear, concise language suitable for technical documentation
2. Organize with logical headings (use ## for main sections, ### for subsections)
3. Remove any duplicate information
4. Fix any formatting issues or inconsistencies
5. Ensure code blocks are properly formatted with language tags
6. Add a brief introduction at the start
7. Keep the same technical accuracy as the source
8. Use bullet points for lists where appropriate

Output the rewritten content as clean markdown. Do not include any meta-commentary."""

        try:
            content = await retry_with_backoff(
                self._call_completion,
                prompt,
                max_retries=3,
            )
            return content.strip()
        except Exception as e:
            logger.error(f"Content rewriting failed: {e}")
            raise OpenAIError(f"Failed to rewrite content: {e}") from e

    async def generate_html(
        self,
        markdown_content: str,
        title: str,
        description: str,
    ) -> str:
        """
        Convert markdown content to styled HTML.

        Args:
            markdown_content: The markdown content to convert
            title: Guide title
            description: Guide description

        Returns:
            Complete HTML document
        """
        prompt = f"""Convert this markdown documentation to clean, semantic HTML.

Title: {title}
Description: {description}

Markdown Content:
{markdown_content}

Requirements:
1. Use semantic HTML5 elements (article, section, header, nav, etc.)
2. Convert markdown headings to proper h1-h6 tags
3. Format code blocks with <pre><code class="language-X"> tags
4. Convert lists properly to <ul>/<ol> and <li>
5. Add appropriate class names for styling (e.g., "prose" for text content)
6. Do NOT include <html>, <head>, or <body> tags - just the content
7. The content will be inserted into an existing template

Return ONLY the HTML content, no markdown or commentary."""

        try:
            html_content = await retry_with_backoff(
                self._call_completion,
                prompt,
                max_retries=3,
            )
            return html_content.strip()
        except Exception as e:
            logger.error(f"HTML generation failed: {e}")
            raise OpenAIError(f"Failed to generate HTML: {e}") from e

    async def _call_completion(self, prompt: str) -> str:
        """Make a completion API call."""
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful technical writing assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        return response.choices[0].message.content or ""
