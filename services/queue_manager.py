import asyncio
from dataclasses import dataclass
from typing import Callable, Awaitable, Any
from config.settings import settings
from utils.logger import logger


@dataclass
class QueueItem:
    task_id: str
    user_id: int
    url: str
    handler_func: Callable[[str, int, str], Awaitable[Any]]


class QueueManager:
    def __init__(self):
        self.queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        self.active_tasks = 0
        self.workers = []
        self._running = False

    async def start(self):
        """Start worker task pool based on max_concurrent_downloads config."""
        if self._running:
            return
        self._running = True
        worker_count = max(1, settings.max_concurrent_downloads)
        logger.info(f"Starting {worker_count} Queue Manager workers...")
        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop(i + 1))
            self.workers.append(task)

    async def stop(self):
        """Cancel and stop all queue workers."""
        self._running = False
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        logger.info("Queue Manager stopped.")

    async def add_task(self, task_id: str, user_id: int, url: str, handler_func: Callable[[str, int, str], Awaitable[Any]]) -> int:
        """Enqueues task and returns position in queue."""
        item = QueueItem(task_id=task_id, user_id=user_id, url=url, handler_func=handler_func)
        await self.queue.put(item)
        return self.queue.qsize()

    async def _worker_loop(self, worker_id: int):
        while self._running:
            try:
                item = await self.queue.get()
                self.active_tasks += 1
                logger.info(f"[Worker {worker_id}] Processing task {item.task_id} for user {item.user_id}")
                try:
                    await item.handler_func(item.task_id, item.user_id, item.url)
                except Exception as e:
                    logger.error(f"[Worker {worker_id}] Task {item.task_id} failed with error: {e}")
                finally:
                    self.active_tasks -= 1
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Unexpected error in loop: {e}")


queue_manager = QueueManager()
