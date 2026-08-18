"""FastAPI entry point for the single-process Local Realtime Agent."""

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from typing import Callable, Optional, Sequence

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from backend.app.local_agent import (
    LocalRealtimeAgent,
    MuseEEGSource,
    SyntheticEEGSource,
)
from backend.app.model.inference_service import ModelInferenceService
from backend.app.model.provider import (
    ModelProvider,
    create_runtime_model_provider,
)
from backend.app.muse.muse_collector import MuseCollector
from backend.app.realtime.messages import create_device_status_message
from backend.app.realtime.publisher import QueuedRealtimePublisher
from backend.app.realtime.state import LocalAgentState
from backend.app.realtime.websocket_manager import WebSocketManager


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    source_mode: str = "muse"
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.source_mode not in ("muse", "synthetic"):
            raise ValueError("source_mode must be muse or synthetic")


def create_app(
    config: Optional[ServerConfig] = None,
    model_provider: Optional[ModelProvider] = None,
    start_agent: bool = True,
    write_line: Callable[[str], None] = print,
) -> FastAPI:
    active_config = config or ServerConfig()
    provider = model_provider or create_runtime_model_provider()
    state = LocalAgentState(provider.display_name)
    device_name = (
        "Synthetic Muse 2"
        if active_config.source_mode == "synthetic"
        else "Muse 2"
    )
    manager = WebSocketManager(
        initial_device_status=create_device_status_message(False, device_name),
        write_line=write_line,
    )
    publisher = QueuedRealtimePublisher()
    source = (
        SyntheticEEGSource()
        if active_config.source_mode == "synthetic"
        else MuseEEGSource(
            MuseCollector(
                mac_address=active_config.mac_address,
                serial_number=active_config.serial_number,
            )
        )
    )
    agent = LocalRealtimeAgent(
        source=source,
        publisher=publisher,
        inference_service=ModelInferenceService(provider),
        state=state,
        poll_interval=(
            source.chunk_size / 256.0
            if isinstance(source, SyntheticEEGSource)
            else 0.1
        ),
        write_line=write_line,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        write_line("LOCAL AGENT STARTED")
        write_line(
            "WebSocket: ws://localhost:{0}/ws".format(active_config.port)
        )
        write_line(
            "Health: http://localhost:{0}/health".format(active_config.port)
        )
        write_line("Model provider: {0}".format(provider.display_name))
        if active_config.source_mode == "synthetic":
            write_line("Source: MOCK / SYNTHETIC STREAM")

        publisher.start_delivery(manager.broadcast)
        if start_agent:
            agent.start()
        try:
            yield
        finally:
            if start_agent:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    agent.stop,
                )
            await publisher.stop_delivery()
            await manager.close_all()

    app = FastAPI(title="Muse Local Realtime Agent", lifespan=lifespan)
    app.state.realtime_manager = manager
    app.state.realtime_publisher = publisher
    app.state.local_agent = agent
    app.state.local_agent_state = state
    app.state.model_provider = provider

    @app.get("/health")
    async def health():
        return state.health_snapshot()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        client_id: Optional[str] = None
        try:
            client_id = await manager.connect(websocket)
            while True:
                # Incoming text is deliberately ignored. There are no remote
                # Muse or model control commands in this protocol.
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            if client_id is not None:
                await manager.disconnect(client_id)

    return app


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Muse acquisition, inference, and local WebSocket server.",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("LOCAL_AGENT_HOST", "0.0.0.0"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("LOCAL_AGENT_PORT", "8000")),
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        default=os.getenv("LOCAL_AGENT_SOURCE", "muse").lower() == "synthetic",
        help="Use the clearly labeled synthetic transport smoke-test source.",
    )
    parser.add_argument("--mac-address")
    parser.add_argument("--serial-number")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = build_argument_parser().parse_args(argv)
    config = ServerConfig(
        host=args.host,
        port=args.port,
        source_mode="synthetic" if args.synthetic else "muse",
        mac_address=args.mac_address,
        serial_number=args.serial_number,
    )
    app = create_app(config=config)
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
