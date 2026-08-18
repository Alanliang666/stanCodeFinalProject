"""Async tests for client isolation and per-client backpressure."""

import asyncio
import time
import unittest

from backend.app.realtime.messages import (
    create_device_status_message,
    create_eeg_chunk_message,
)
from backend.app.realtime.websocket_manager import WebSocketManager
from backend.tests.helpers import make_chunk


class FakeWebSocket:
    def __init__(self, send_gate=None, fail_send=False) -> None:
        self.accepted = False
        self.closed = False
        self.sent_messages = []
        self.send_gate = send_gate
        self.fail_send = fail_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message) -> None:
        if self.send_gate is not None:
            await self.send_gate.wait()
        if self.fail_send:
            raise RuntimeError("client disconnected")
        self.sent_messages.append(message)

    async def close(self) -> None:
        self.closed = True


async def wait_for_message_count(websocket, count: int) -> None:
    for _ in range(100):
        if len(websocket.sent_messages) >= count:
            return
        await asyncio.sleep(0.001)
    raise AssertionError("timed out waiting for WebSocket messages")


class WebSocketManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.log_lines = []
        self.manager = WebSocketManager(
            create_device_status_message(False),
            write_line=self.log_lines.append,
        )

    async def asyncTearDown(self) -> None:
        await self.manager.close_all()

    async def test_connect_immediately_receives_current_device_status(self) -> None:
        websocket = FakeWebSocket()

        await self.manager.connect(websocket)
        await wait_for_message_count(websocket, 1)

        self.assertTrue(websocket.accepted)
        self.assertEqual(websocket.sent_messages[0]["type"], "device_status")
        self.assertFalse(websocket.sent_messages[0]["data"]["connected"])

    async def test_multiple_clients_receive_same_broadcast(self) -> None:
        first = FakeWebSocket()
        second = FakeWebSocket()
        await self.manager.connect(first)
        await self.manager.connect(second)
        await wait_for_message_count(first, 1)
        await wait_for_message_count(second, 1)

        message = create_eeg_chunk_message(make_chunk(12))
        await self.manager.broadcast(message)
        await wait_for_message_count(first, 2)
        await wait_for_message_count(second, 2)

        self.assertEqual(first.sent_messages[-1], message)
        self.assertEqual(second.sent_messages[-1], message)

    async def test_one_disconnect_does_not_affect_other_client(self) -> None:
        first = FakeWebSocket()
        second = FakeWebSocket()
        first_id = await self.manager.connect(first)
        await self.manager.connect(second)
        await wait_for_message_count(second, 1)

        await self.manager.disconnect(first_id)
        await self.manager.broadcast(create_device_status_message(True))
        await wait_for_message_count(second, 2)

        self.assertEqual(self.manager.client_count, 1)
        self.assertTrue(second.sent_messages[-1]["data"]["connected"])

    async def test_disconnecting_unknown_client_is_safe(self) -> None:
        await self.manager.disconnect("already-disconnected")
        self.assertEqual(self.manager.client_count, 0)

    async def test_send_failure_is_isolated(self) -> None:
        failing = FakeWebSocket(fail_send=True)
        healthy = FakeWebSocket()
        await self.manager.connect(failing)
        await self.manager.connect(healthy)
        await wait_for_message_count(healthy, 1)
        await asyncio.sleep(0.01)

        await self.manager.broadcast(create_device_status_message(True))
        await wait_for_message_count(healthy, 2)

        self.assertEqual(self.manager.client_count, 1)
        self.assertTrue(healthy.sent_messages[-1]["data"]["connected"])

    async def test_slow_client_does_not_block_broadcast_or_fast_client(self) -> None:
        slow_gate = asyncio.Event()
        slow = FakeWebSocket(send_gate=slow_gate)
        fast = FakeWebSocket()
        slow_id = await self.manager.connect(slow)
        await self.manager.connect(fast)
        await wait_for_message_count(fast, 1)

        started_at = time.perf_counter()
        for index in range(1_000):
            await self.manager.broadcast(
                create_eeg_chunk_message(
                    make_chunk(12, start_index=index * 12)
                )
            )
        broadcast_duration = time.perf_counter() - started_at
        await wait_for_message_count(fast, 2)

        self.assertLess(broadcast_duration, 0.5)
        self.assertLessEqual(self.manager.client_pending_count(slow_id), 1)
        self.assertGreater(self.manager.client_dropped_eeg_count(slow_id), 0)
        self.assertEqual(fast.sent_messages[-1]["type"], "eeg_chunk")
        slow_gate.set()


if __name__ == "__main__":
    unittest.main()
