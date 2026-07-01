import asyncio
import uuid


class SSEManager:
    """Manages active SSE connections per research_id."""

    def __init__(self):
        self._connections: dict[uuid.UUID, list[asyncio.Queue]] = {}

    async def connect(
        self, research_id: uuid.UUID, user_id: uuid.UUID
    ) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        if research_id not in self._connections:
            self._connections[research_id] = []
        self._connections[research_id].append(queue)
        return queue

    async def push_event(
        self, research_id: uuid.UUID, event_type: str, data: dict
    ) -> None:
        queues = self._connections.get(research_id, [])
        for queue in queues:
            await queue.put({"event": event_type, "data": data})

    def disconnect(self, research_id: uuid.UUID, queue: asyncio.Queue) -> None:
        queues = self._connections.get(research_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._connections.pop(research_id, None)


sse_manager = SSEManager()
