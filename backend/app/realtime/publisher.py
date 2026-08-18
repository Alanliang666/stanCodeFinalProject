"""Non-blocking sync-to-async realtime publisher boundary."""

import asyncio
from threading import Lock
from typing import Awaitable, Callable, Dict, List, Optional, Protocol

from backend.app.eeg.contracts import EEGChunk
from backend.app.model.contracts import CognitivePrediction
from backend.app.realtime.contracts import (
    REALTIME_MESSAGE_PRIORITY,
    RealtimeMessage,
)
from backend.app.realtime.messages import (
    create_cognitive_prediction_message,
    create_device_status_message,
    create_eeg_chunk_message,
)


DeliverMessage = Callable[[RealtimeMessage], Awaitable[None]]


class RealtimePublisher(Protocol):
    def publish_device_status(
        self,
        connected: bool,
        device: str = "Muse 2",
    ) -> None:
        ...

    def publish_eeg_chunk(self, chunk: EEGChunk) -> None:
        ...

    def publish_prediction(
        self,
        prediction: CognitivePrediction,
        timestamp: Optional[float] = None,
    ) -> None:
        ...


class LatestMessageBuffer:
    """Thread-safe, fixed-memory latest-only buffer for three message types."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._pending: Dict[str, RealtimeMessage] = {}
        self._dropped_eeg_messages = 0

    def offer(self, message: RealtimeMessage) -> None:
        message_type = message["type"]
        with self._lock:
            if message_type == "eeg_chunk" and message_type in self._pending:
                self._dropped_eeg_messages += 1
            self._pending[message_type] = message

    def take_all(self) -> List[RealtimeMessage]:
        with self._lock:
            messages = [
                self._pending.pop(message_type)
                for message_type in REALTIME_MESSAGE_PRIORITY
                if message_type in self._pending
            ]
        return messages

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    @property
    def dropped_eeg_messages(self) -> int:
        with self._lock:
            return self._dropped_eeg_messages


class QueuedRealtimePublisher:
    """Sync producer API with bounded latest-only async delivery."""

    def __init__(self, delivery_poll_seconds: float = 0.005) -> None:
        if delivery_poll_seconds <= 0:
            raise ValueError("delivery_poll_seconds must be positive")
        self._buffer = LatestMessageBuffer()
        self._delivery_poll_seconds = delivery_poll_seconds
        self._delivery_task: Optional[asyncio.Task] = None
        self._running = False

    def publish_device_status(
        self,
        connected: bool,
        device: str = "Muse 2",
    ) -> None:
        self._buffer.offer(create_device_status_message(connected, device))

    def publish_eeg_chunk(self, chunk: EEGChunk) -> None:
        self._buffer.offer(create_eeg_chunk_message(chunk))

    def publish_prediction(
        self,
        prediction: CognitivePrediction,
        timestamp: Optional[float] = None,
    ) -> None:
        self._buffer.offer(
            create_cognitive_prediction_message(prediction, timestamp)
        )

    def start_delivery(self, deliver_message: DeliverMessage) -> None:
        if self._delivery_task is not None:
            return
        self._running = True
        self._delivery_task = asyncio.create_task(
            self._delivery_loop(deliver_message)
        )

    async def stop_delivery(self) -> None:
        self._running = False
        task = self._delivery_task
        if task is not None:
            await task
        self._delivery_task = None

    async def _delivery_loop(self, deliver_message: DeliverMessage) -> None:
        while self._running:
            messages = self._buffer.take_all()
            if not messages:
                await asyncio.sleep(self._delivery_poll_seconds)
                continue
            for message in messages:
                await deliver_message(message)

        for message in self._buffer.take_all():
            await deliver_message(message)

    @property
    def pending_message_count(self) -> int:
        return self._buffer.pending_count

    @property
    def dropped_eeg_message_count(self) -> int:
        return self._buffer.dropped_eeg_messages
