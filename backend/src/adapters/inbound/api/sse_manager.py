import asyncio
from uuid import UUID


class SSEConnectionManager:
    def __init__(self) -> None:
        self._queues: dict[UUID, list[asyncio.Queue]] = {}

    def register(self, user_id: UUID) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(user_id, []).append(queue)
        return queue

    def unregister(self, user_id: UUID, queue: asyncio.Queue) -> None:
        queues = self._queues.get(user_id, [])
        if queue in queues:
            queues.remove(queue)

    async def push(self, user_id: UUID, data: dict) -> None:
        for queue in list(self._queues.get(user_id, [])):
            await queue.put(data)


sse_manager = SSEConnectionManager()
