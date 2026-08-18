"""Connected-client lifecycle and non-blocking latest-message broadcast."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from fastapi import WebSocket

from backend.app.realtime.contracts import (
    REALTIME_MESSAGE_PRIORITY,
    DeviceStatusMessage,
    RealtimeMessage,
)


class ClientDeliveryBuffer:
    """Per-client latest-only buffer with control messages ahead of EEG."""

    def __init__(self) -> None:
        self._pending: Dict[str, RealtimeMessage] = {}
        self._available = asyncio.Event()
        self.dropped_eeg_messages = 0

    def offer(self, message: RealtimeMessage) -> None:
        message_type = message["type"]
        if message_type == "eeg_chunk" and message_type in self._pending:
            self.dropped_eeg_messages += 1
        self._pending[message_type] = message
        self._available.set()

    async def next_message(self) -> RealtimeMessage:
        while True:
            for message_type in REALTIME_MESSAGE_PRIORITY:
                message = self._pending.pop(message_type, None)
                if message is not None:
                    if not self._pending:
                        self._available.clear()
                    return message
            self._available.clear()
            await self._available.wait()

    @property
    def pending_count(self) -> int:
        return len(self._pending)


@dataclass
class ManagedWebSocketClient:
    client_id: str
    websocket: WebSocket
    buffer: ClientDeliveryBuffer
    sender_task: asyncio.Task


class WebSocketManager:
    def __init__(
        self,
        initial_device_status: DeviceStatusMessage,
        write_line: Callable[[str], None] = print,
    ) -> None:
        self._clients: Dict[str, ManagedWebSocketClient] = {}
        self._current_device_status = initial_device_status
        self._latest_prediction: Optional[RealtimeMessage] = None
        self._write_line = write_line

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_id = uuid4().hex
        buffer = ClientDeliveryBuffer()
        sender_task = asyncio.create_task(
            self._send_loop(client_id, websocket, buffer)
        )
        client = ManagedWebSocketClient(
            client_id=client_id,
            websocket=websocket,
            buffer=buffer,
            sender_task=sender_task,
        )
        self._clients[client_id] = client
        buffer.offer(self._current_device_status)
        if self._latest_prediction is not None:
            buffer.offer(self._latest_prediction)
        self._write_line("Client connected: {0}".format(client_id))
        return client_id

    async def disconnect(self, client_id: str) -> None:
        client = self._clients.pop(client_id, None)
        if client is None:
            return
        client.sender_task.cancel()
        if client.sender_task is not asyncio.current_task():
            await asyncio.gather(client.sender_task, return_exceptions=True)
        try:
            await client.websocket.close()
        except Exception:
            pass
        self._write_line("Client disconnected: {0}".format(client_id))

    async def broadcast(self, message: RealtimeMessage) -> None:
        if message["type"] == "device_status":
            self._current_device_status = message
        elif message["type"] == "cognitive_prediction":
            self._latest_prediction = message

        for client in tuple(self._clients.values()):
            client.buffer.offer(message)

    async def close_all(self) -> None:
        for client_id in tuple(self._clients.keys()):
            await self.disconnect(client_id)

    async def _send_loop(
        self,
        client_id: str,
        websocket: WebSocket,
        buffer: ClientDeliveryBuffer,
    ) -> None:
        try:
            while True:
                message = await buffer.next_message()
                await websocket.send_json(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            removed = self._clients.pop(client_id, None)
            if removed is not None:
                self._write_line(
                    "Client disconnected: {0}".format(client_id)
                )

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def current_device_status(self) -> DeviceStatusMessage:
        return self._current_device_status

    def client_pending_count(self, client_id: str) -> int:
        client = self._clients.get(client_id)
        return 0 if client is None else client.buffer.pending_count

    def client_dropped_eeg_count(self, client_id: str) -> int:
        client = self._clients.get(client_id)
        return 0 if client is None else client.buffer.dropped_eeg_messages
