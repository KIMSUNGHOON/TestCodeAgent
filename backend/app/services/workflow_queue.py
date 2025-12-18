"""
Workflow Queue Manager

Manages concurrent workflow execution with request queuing and rate limiting.
Prevents server overload by limiting simultaneous LLM instances.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator, Callable, Dict, Any
from collections import OrderedDict

logger = logging.getLogger(__name__)


class WorkflowQueue:
    """
    Manages workflow execution queue with concurrency control.

    Features:
    - Limits maximum concurrent workflows
    - Queue management for excess requests
    - Position tracking for waiting requests
    - Semaphore-based flow control
    """

    def __init__(self, max_concurrent: int = 10):
        """
        Initialize workflow queue.

        Args:
            max_concurrent: Maximum number of simultaneous workflow executions
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0
        self.total_processed = 0
        self.queue_size = 0
        self._lock = asyncio.Lock()

    async def execute_with_queue(
        self,
        session_id: str,
        workflow_fn: Callable[[], AsyncGenerator[Dict[str, Any], None]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute workflow with queue management.

        Args:
            session_id: Session identifier
            workflow_fn: Async generator function that yields workflow updates

        Yields:
            Workflow updates including queue status
        """
        # Calculate queue position
        async with self._lock:
            self.queue_size += 1
            queue_position = self.active_count + self.queue_size

        # Notify user of queue position if waiting
        if queue_position > self.max_concurrent:
            wait_position = queue_position - self.max_concurrent
            estimated_wait = wait_position * 30  # 30 seconds per workflow estimate

            yield {
                "type": "queue_status",
                "status": "waiting",
                "queue_position": wait_position,
                "estimated_wait_seconds": estimated_wait,
                "message": f"현재 대기 중입니다. 대기 순서: {wait_position}번, 예상 대기 시간: {estimated_wait}초"
            }

            logger.info(
                f"Session {session_id} queued at position {wait_position} "
                f"(estimated wait: {estimated_wait}s)"
            )

        # Wait for semaphore (blocks if at max_concurrent)
        async with self.semaphore:
            async with self._lock:
                self.active_count += 1
                self.queue_size -= 1

            start_time = datetime.now()

            yield {
                "type": "queue_status",
                "status": "started",
                "message": "워크플로우를 시작합니다"
            }

            logger.info(
                f"Session {session_id} started execution "
                f"(active: {self.active_count}/{self.max_concurrent})"
            )

            try:
                # Execute actual workflow
                async for update in workflow_fn():
                    yield update

            except Exception as e:
                logger.error(f"Workflow error for session {session_id}: {e}")
                yield {
                    "type": "error",
                    "error": str(e),
                    "message": f"워크플로우 실행 중 오류가 발생했습니다: {str(e)}"
                }

            finally:
                # Release resources
                async with self._lock:
                    self.active_count -= 1
                    self.total_processed += 1

                duration = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"Session {session_id} completed in {duration:.1f}s "
                    f"(active: {self.active_count}/{self.max_concurrent}, "
                    f"total processed: {self.total_processed})"
                )

    async def get_status(self) -> Dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Dictionary with queue statistics
        """
        async with self._lock:
            return {
                "max_concurrent": self.max_concurrent,
                "active_count": self.active_count,
                "queue_size": self.queue_size,
                "total_processed": self.total_processed,
                "available_slots": self.max_concurrent - self.active_count
            }


class WorkflowCacheManager:
    """
    Manages workflow cache with LRU eviction and TTL.

    Features:
    - LRU (Least Recently Used) eviction
    - TTL (Time To Live) based expiration
    - Memory usage control
    """

    def __init__(
        self,
        max_cache_size: int = 100,
        ttl_hours: int = 1
    ):
        """
        Initialize cache manager.

        Args:
            max_cache_size: Maximum number of cached workflows
            ttl_hours: Time to live in hours
        """
        self.max_cache_size = max_cache_size
        self.ttl = timedelta(hours=ttl_hours)
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }

    async def get(self, session_id: str) -> Any:
        """
        Get workflow from cache.

        Args:
            session_id: Session identifier

        Returns:
            Cached workflow or None if not found/expired
        """
        async with self._lock:
            if session_id not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[session_id]

            # Check TTL
            if datetime.now() - entry["created_at"] > self.ttl:
                logger.info(f"Cache expired for session {session_id}")
                del self._cache[session_id]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(session_id)
            self._stats["hits"] += 1

            logger.debug(
                f"Cache hit for session {session_id} "
                f"(age: {(datetime.now() - entry['created_at']).total_seconds():.0f}s)"
            )

            return entry["workflow"]

    async def set(self, session_id: str, workflow: Any) -> None:
        """
        Add workflow to cache.

        Args:
            session_id: Session identifier
            workflow: Workflow instance to cache
        """
        async with self._lock:
            # LRU eviction if at max size
            if len(self._cache) >= self.max_cache_size and session_id not in self._cache:
                oldest_session = next(iter(self._cache))
                del self._cache[oldest_session]
                self._stats["evictions"] += 1
                logger.info(
                    f"Evicted oldest workflow: {oldest_session} "
                    f"(cache size: {len(self._cache)}/{self.max_cache_size})"
                )

            self._cache[session_id] = {
                "workflow": workflow,
                "created_at": datetime.now()
            }

            logger.info(
                f"Cached workflow for session {session_id} "
                f"(cache size: {len(self._cache)}/{self.max_cache_size})"
            )

    async def remove(self, session_id: str) -> None:
        """
        Remove workflow from cache.

        Args:
            session_id: Session identifier
        """
        async with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
                logger.info(f"Removed workflow from cache: {session_id}")

    async def clear(self) -> int:
        """
        Clear all cached workflows.

        Returns:
            Number of workflows cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} workflows from cache")
            return count

    async def cleanup_expired(self) -> int:
        """
        Remove expired workflows from cache.

        Returns:
            Number of workflows removed
        """
        async with self._lock:
            now = datetime.now()
            expired = [
                sid for sid, entry in self._cache.items()
                if now - entry["created_at"] > self.ttl
            ]

            for sid in expired:
                del self._cache[sid]

            if expired:
                logger.info(f"Cleaned up {len(expired)} expired workflows")
                self._stats["expirations"] += len(expired)

            return len(expired)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        async with self._lock:
            hit_rate = (
                self._stats["hits"] / (self._stats["hits"] + self._stats["misses"])
                if (self._stats["hits"] + self._stats["misses"]) > 0
                else 0
            )

            return {
                "cache_size": len(self._cache),
                "max_cache_size": self.max_cache_size,
                "ttl_hours": self.ttl.total_seconds() / 3600,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": f"{hit_rate:.2%}",
                "evictions": self._stats["evictions"],
                "expirations": self._stats["expirations"]
            }
