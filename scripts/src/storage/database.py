"""SQLite database for batch and guide storage with progress tracking."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from ..utils.config import settings

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Simple connection pool stub for future scaling.

    Current implementation: Single connection with lock for thread safety.
    Future upgrade path: Replace with asyncpg pool for PostgreSQL or
    use a proper SQLite pool like aiosqlite-pool.

    TODO: For production scaling:
    - Switch to PostgreSQL with asyncpg for true connection pooling
    - Consider using encode/databases for async DB abstraction
    - Add connection health checks and automatic reconnection
    """

    def __init__(self, db_path: Path, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size  # Reserved for future use
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the connection pool."""
        async with self._lock:
            if self._connection is None:
                self._connection = await aiosqlite.connect(self.db_path)
                self._connection.row_factory = aiosqlite.Row
                # Enable WAL mode for better concurrent read performance
                await self._connection.execute("PRAGMA journal_mode=WAL")
                await self._connection.execute("PRAGMA synchronous=NORMAL")
                await self._connection.commit()

    async def close(self):
        """Close all connections in the pool."""
        async with self._lock:
            if self._connection:
                await self._connection.close()
                self._connection = None

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.

        Current: Returns the single connection with lock protection.
        Future: Will return a connection from an actual pool.
        """
        async with self._lock:
            if self._connection is None:
                await self.initialize()
            yield self._connection


class Database:
    """
    Async SQLite database for pipeline state management.

    Stores batches, files, topic groups, and guides.
    Uses a connection pool stub for future scaling.
    """

    def __init__(self, db_path: Optional[Path] = None, pool_size: int = 5):
        self.db_path = db_path or settings.db_path
        self._pool = ConnectionPool(self.db_path, pool_size)
        self._initialized = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Connect to database and initialize schema."""
        await self._pool.initialize()
        await self._init_schema()
        self._initialized = True

    async def close(self):
        """Close database connection pool."""
        await self._pool.close()
        self._initialized = False

    async def _init_schema(self):
        """Initialize database schema."""
        async with self._pool.acquire() as conn:
            await conn.executescript(
                """
                -- Batches table: tracks overall batch processing
                CREATE TABLE IF NOT EXISTS batches (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    progress REAL NOT NULL DEFAULT 0.0,
                    current_stage TEXT,
                    total_files INTEGER NOT NULL DEFAULT 0,
                    processed_files INTEGER NOT NULL DEFAULT 0,
                    failed_files INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Files table: individual files within a batch
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    original_path TEXT NOT NULL,
                    stored_path TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    trelent_job_id TEXT,
                    markdown TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (batch_id) REFERENCES batches(id)
                );

                -- Topic groups table: groups files by topic
                CREATE TABLE IF NOT EXISTS topic_groups (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (batch_id) REFERENCES batches(id)
                );

                -- File-to-topic mapping
                CREATE TABLE IF NOT EXISTS file_topics (
                    file_id TEXT NOT NULL,
                    topic_group_id TEXT NOT NULL,
                    PRIMARY KEY (file_id, topic_group_id),
                    FOREIGN KEY (file_id) REFERENCES files(id),
                    FOREIGN KEY (topic_group_id) REFERENCES topic_groups(id)
                );

                -- Guides table: final generated guides
                CREATE TABLE IF NOT EXISTS guides (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    topic_group_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    slug TEXT NOT NULL,
                    html_path TEXT,
                    rewritten_content TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (batch_id) REFERENCES batches(id),
                    FOREIGN KEY (topic_group_id) REFERENCES topic_groups(id)
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_files_batch ON files(batch_id);
                CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
                CREATE INDEX IF NOT EXISTS idx_guides_batch ON guides(batch_id);
                CREATE INDEX IF NOT EXISTS idx_topic_groups_batch ON topic_groups(batch_id);
            """
            )
            await conn.commit()

    # ==================== Batch Operations ====================

    async def create_batch(self, batch_id: str, total_files: int) -> dict:
        """Create a new batch record."""
        now = datetime.utcnow().isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO batches (id, total_files, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (batch_id, total_files, now, now),
            )
            await conn.commit()
        return await self.get_batch(batch_id)

    async def get_batch(self, batch_id: str) -> Optional[dict]:
        """Get batch by ID."""
        async with self._pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM batches WHERE id = ?", (batch_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_batches(self, limit: int = 50) -> list[dict]:
        """List all batches, newest first."""
        async with self._pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM batches ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_batch_progress(
        self,
        batch_id: str,
        progress: float,
        status: Optional[str] = None,
        current_stage: Optional[str] = None,
        processed_files: Optional[int] = None,
        failed_files: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Update batch progress and status."""
        updates = ["progress = ?", "updated_at = ?"]
        values = [progress, datetime.utcnow().isoformat()]

        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if current_stage is not None:
            updates.append("current_stage = ?")
            values.append(current_stage)
        if processed_files is not None:
            updates.append("processed_files = ?")
            values.append(processed_files)
        if failed_files is not None:
            updates.append("failed_files = ?")
            values.append(failed_files)
        if error_message is not None:
            updates.append("error_message = ?")
            values.append(error_message)

        values.append(batch_id)

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE batches SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            await conn.commit()

    # ==================== File Operations ====================

    async def create_file(
        self,
        file_id: str,
        batch_id: str,
        filename: str,
        original_path: str,
        stored_path: str,
    ) -> dict:
        """Create a new file record."""
        now = datetime.utcnow().isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO files (id, batch_id, filename, original_path, stored_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (file_id, batch_id, filename, original_path, stored_path, now, now),
            )
            await conn.commit()
        return await self.get_file(file_id)

    async def get_file(self, file_id: str) -> Optional[dict]:
        """Get file by ID."""
        async with self._pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM files WHERE id = ?", (file_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_batch_files(
        self, batch_id: str, status: Optional[str] = None
    ) -> list[dict]:
        """List all files in a batch."""
        async with self._pool.acquire() as conn:
            if status:
                cursor = await conn.execute(
                    "SELECT * FROM files WHERE batch_id = ? AND status = ? ORDER BY filename",
                    (batch_id, status),
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM files WHERE batch_id = ? ORDER BY filename",
                    (batch_id,),
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_file(
        self,
        file_id: str,
        status: Optional[str] = None,
        trelent_job_id: Optional[str] = None,
        markdown: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Update file record."""
        updates = ["updated_at = ?"]
        values = [datetime.utcnow().isoformat()]

        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if trelent_job_id is not None:
            updates.append("trelent_job_id = ?")
            values.append(trelent_job_id)
        if markdown is not None:
            updates.append("markdown = ?")
            values.append(markdown)
        if error_message is not None:
            updates.append("error_message = ?")
            values.append(error_message)

        values.append(file_id)

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE files SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            await conn.commit()

    async def get_failed_files(self, batch_id: str) -> list[dict]:
        """Get all failed files in a batch."""
        return await self.list_batch_files(batch_id, status="failed")

    # ==================== Topic Group Operations ====================

    async def create_topic_group(
        self,
        group_id: str,
        batch_id: str,
        topic: str,
        slug: str,
        description: str,
        file_ids: list[str],
    ) -> dict:
        """Create a topic group and assign files."""
        now = datetime.utcnow().isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO topic_groups (id, batch_id, topic, slug, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (group_id, batch_id, topic, slug, description, now),
            )

            # Assign files to group
            for file_id in file_ids:
                await conn.execute(
                    "INSERT OR IGNORE INTO file_topics (file_id, topic_group_id) VALUES (?, ?)",
                    (file_id, group_id),
                )

            await conn.commit()
        return await self.get_topic_group(group_id)

    async def get_topic_group(self, group_id: str) -> Optional[dict]:
        """Get topic group by ID with assigned file IDs."""
        async with self._pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM topic_groups WHERE id = ?", (group_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            group = dict(row)

            # Get assigned file IDs
            cursor = await conn.execute(
                "SELECT file_id FROM file_topics WHERE topic_group_id = ?", (group_id,)
            )
            file_rows = await cursor.fetchall()
            group["file_ids"] = [r["file_id"] for r in file_rows]

            return group

    async def list_batch_topic_groups(self, batch_id: str) -> list[dict]:
        """List all topic groups in a batch."""
        async with self._pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM topic_groups WHERE batch_id = ? ORDER BY topic",
                (batch_id,),
            )
            rows = await cursor.fetchall()
            groups = []
            for row in rows:
                group = dict(row)
                # Get assigned file IDs
                cursor = await conn.execute(
                    "SELECT file_id FROM file_topics WHERE topic_group_id = ?",
                    (group["id"],),
                )
                file_rows = await cursor.fetchall()
                group["file_ids"] = [r["file_id"] for r in file_rows]
                groups.append(group)
            return groups

    # ==================== Guide Operations ====================

    async def create_guide(
        self,
        guide_id: str,
        batch_id: str,
        topic_group_id: str,
        title: str,
        description: str,
        slug: str,
    ) -> dict:
        """Create a guide record."""
        now = datetime.utcnow().isoformat()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guides (id, batch_id, topic_group_id, title, description, slug, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (guide_id, batch_id, topic_group_id, title, description, slug, now, now),
            )
            await conn.commit()
        return await self.get_guide(guide_id)

    async def get_guide(self, guide_id: str) -> Optional[dict]:
        """Get guide by ID."""
        async with self._pool.acquire() as conn:
            cursor = await conn.execute(
                "SELECT * FROM guides WHERE id = ?", (guide_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_guides(
        self, batch_id: Optional[str] = None, status: str = "completed"
    ) -> list[dict]:
        """List guides, optionally filtered by batch."""
        async with self._pool.acquire() as conn:
            if batch_id:
                cursor = await conn.execute(
                    "SELECT * FROM guides WHERE batch_id = ? AND status = ? ORDER BY title",
                    (batch_id, status),
                )
            else:
                cursor = await conn.execute(
                    "SELECT * FROM guides WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_guide(
        self,
        guide_id: str,
        status: Optional[str] = None,
        html_path: Optional[str] = None,
        rewritten_content: Optional[str] = None,
    ):
        """Update guide record."""
        updates = ["updated_at = ?"]
        values = [datetime.utcnow().isoformat()]

        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if html_path is not None:
            updates.append("html_path = ?")
            values.append(html_path)
        if rewritten_content is not None:
            updates.append("rewritten_content = ?")
            values.append(rewritten_content)

        values.append(guide_id)

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE guides SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            await conn.commit()
