"""Small receive-only WebSocket client for local transport smoke tests."""

import argparse
import asyncio
import json
from typing import Optional, Sequence

import websockets


async def receive_messages(url: str, message_count: int) -> None:
    async with websockets.connect(url) as websocket:
        for _ in range(message_count):
            message = json.loads(await websocket.recv())
            message_type = message.get("type", "unknown")
            if message_type == "eeg_chunk":
                sample_count = len(message["data"]["samples"])
                print("eeg_chunk: {0} samples".format(sample_count))
            elif message_type == "device_status":
                print(
                    "device_status: connected={0}, device={1}".format(
                        message["data"]["connected"],
                        message["data"]["device"],
                    )
                )
            elif message_type == "cognitive_prediction":
                print(
                    "cognitive_prediction: {0} ({1:.3f})".format(
                        message["data"]["state"],
                        message["data"]["confidence"],
                    )
                )
            else:
                print("message: {0}".format(message_type))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Receive Local Agent messages.")
    parser.add_argument("--url", default="ws://localhost:8000/ws")
    parser.add_argument("--messages", type=int, default=12)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_argument_parser().parse_args(argv)
    if args.messages <= 0:
        raise ValueError("messages must be positive")
    asyncio.run(receive_messages(args.url, args.messages))


if __name__ == "__main__":
    main()
