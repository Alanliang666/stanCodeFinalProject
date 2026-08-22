"""Tests for bounded sync-to-async realtime publishing."""

import asyncio
import time
import unittest

from backend.app.model.contracts import CognitivePrediction
from backend.app.realtime.messages import (
    create_cognitive_prediction_message,
    create_device_status_message,
    create_eeg_chunk_message,
)
from backend.app.realtime.publisher import (
    LatestMessageBuffer,
    QueuedRealtimePublisher,
)
from backend.tests.helpers import make_chunk


def concentration_prediction() -> CognitivePrediction:
    return CognitivePrediction.from_raw_result(
        {
            "state": "concentration",
            "confidence": 0.88,
            "probabilities": {
                "relaxed_openeye": 0.06,
                "concentration": 0.88,
                "relaxed_closeeye": 0.06,
            },
        }
    )


class LatestMessageBufferTests(unittest.TestCase):
    def test_backpressure_keeps_only_latest_eeg_message(self) -> None:
        buffer = LatestMessageBuffer()
        message = create_eeg_chunk_message(make_chunk(12))

        for _ in range(1_000):
            buffer.offer(message)

        self.assertEqual(buffer.pending_count, 1)
        self.assertEqual(buffer.dropped_eeg_messages, 999)

    def test_control_messages_are_delivered_before_eeg(self) -> None:
        buffer = LatestMessageBuffer()
        buffer.offer(create_eeg_chunk_message(make_chunk(12)))
        buffer.offer(
            create_cognitive_prediction_message(concentration_prediction())
        )
        buffer.offer(create_device_status_message(True))

        messages = buffer.take_all()

        self.assertEqual(
            [message["type"] for message in messages],
            ["device_status", "cognitive_prediction", "eeg_chunk"],
        )
        self.assertEqual(buffer.pending_count, 0)


class QueuedRealtimePublisherTests(unittest.IsolatedAsyncioTestCase):
    async def test_publisher_delivers_all_three_message_types(self) -> None:
        delivered = []

        async def record_delivery(message) -> None:
            delivered.append(message)

        publisher = QueuedRealtimePublisher(delivery_poll_seconds=0.001)
        publisher.start_delivery(record_delivery)

        publisher.publish_device_status(True)
        publisher.publish_eeg_chunk(make_chunk(12))
        publisher.publish_prediction(concentration_prediction(), timestamp=10.0)
        await asyncio.sleep(0.02)
        await publisher.stop_delivery()

        self.assertEqual(
            [message["type"] for message in delivered],
            ["device_status", "cognitive_prediction", "eeg_chunk"],
        )

    async def test_slow_delivery_does_not_block_sync_producer(self) -> None:
        delivery_started = asyncio.Event()
        release_delivery = asyncio.Event()

        async def slow_delivery(message) -> None:
            delivery_started.set()
            await release_delivery.wait()

        publisher = QueuedRealtimePublisher(delivery_poll_seconds=0.001)
        publisher.start_delivery(slow_delivery)
        publisher.publish_eeg_chunk(make_chunk(12))
        await asyncio.wait_for(delivery_started.wait(), timeout=1.0)

        started_at = time.perf_counter()
        for index in range(1_000):
            publisher.publish_eeg_chunk(make_chunk(12, start_index=index * 12))
        producer_duration = time.perf_counter() - started_at

        self.assertLess(producer_duration, 0.5)
        self.assertLessEqual(publisher.pending_message_count, 1)
        self.assertGreater(publisher.dropped_eeg_message_count, 0)
        release_delivery.set()
        await publisher.stop_delivery()


if __name__ == "__main__":
    unittest.main()
