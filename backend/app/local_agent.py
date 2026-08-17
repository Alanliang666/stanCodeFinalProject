"""Single-process local EEG acquisition, inference, and publishing agent."""

import math
from threading import Event, Thread
import time
from typing import Callable, Optional, Protocol

import numpy as np

from backend.app.eeg.buffer import EEGInferenceBuffer
from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)
from backend.app.eeg.window_validator import EEGWindowValidator
from backend.app.model.exceptions import (
    InvalidModelInput,
    InvalidModelOutput,
    ModelExecutionError,
)
from backend.app.model.inference_service import ModelInferenceService
from backend.app.muse.muse_collector import MuseCollector
from backend.app.realtime.publisher import RealtimePublisher
from backend.app.realtime.state import LocalAgentState


class EEGSource(Protocol):
    display_name: str
    device_name: str

    def connect(self) -> None:
        ...

    def read_chunk(self) -> Optional[EEGChunk]:
        ...

    def close(self) -> None:
        ...


class MuseEEGSource:
    """Adds Local Agent source metadata without changing MuseCollector."""

    display_name = "MUSE 2"
    device_name = "Muse 2"

    def __init__(self, collector: MuseCollector) -> None:
        self._collector = collector

    def connect(self) -> None:
        self._collector.connect()

    def read_chunk(self) -> Optional[EEGChunk]:
        return self._collector.read_chunk()

    def close(self) -> None:
        self._collector.close()


class SyntheticEEGSource:
    """Minimal deterministic-ish source for transport smoke testing only."""

    display_name = "MOCK / SYNTHETIC STREAM"
    device_name = "Synthetic Muse 2"

    def __init__(self, chunk_size: int = 32) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size
        self._sample_index = 0
        self._started_at = 0.0
        self._connected = False

    def connect(self) -> None:
        self._sample_index = 0
        self._started_at = time.time()
        self._connected = True

    def read_chunk(self) -> Optional[EEGChunk]:
        if not self._connected:
            raise RuntimeError("synthetic source is not connected")

        indices = self._sample_index + np.arange(
            self.chunk_size,
            dtype=np.float64,
        )
        offsets = indices / SAMPLING_RATE_HZ
        frequencies = (7.0, 10.0, 13.0, 5.0)
        samples = np.column_stack(
            tuple(
                np.sin(2.0 * math.pi * frequency * offsets)
                for frequency in frequencies
            )
        )
        timestamps = self._started_at + offsets
        self._sample_index += self.chunk_size
        return EEGChunk(
            sampling_rate_hz=SAMPLING_RATE_HZ,
            channel_order=MUSE_EEG_CHANNEL_ORDER,
            timestamps=timestamps,
            samples=samples,
        )

    def close(self) -> None:
        self._connected = False


class LocalRealtimeAgent:
    """Runs the synchronous source/model pipeline outside the ASGI event loop."""

    def __init__(
        self,
        source: EEGSource,
        publisher: RealtimePublisher,
        inference_service: ModelInferenceService,
        state: LocalAgentState,
        poll_interval: float,
        write_line: Callable[[str], None] = print,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self.source = source
        self.publisher = publisher
        self.inference_service = inference_service
        self.state = state
        self.poll_interval = poll_interval
        self._write_line = write_line
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(
            target=self.run,
            name="muse-realtime-agent",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 20.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        self._thread = None

    def run(self) -> None:
        buffer = EEGInferenceBuffer()
        validator = EEGWindowValidator()
        connected = False
        self.state.set_device_connected(False)
        self.publisher.publish_device_status(False, self.source.device_name)

        try:
            if self.source.display_name == "MOCK / SYNTHETIC STREAM":
                self._write_line("Synthetic source: starting...")
            else:
                self._write_line("Muse: connecting...")
            self.source.connect()
            connected = True
            self.state.set_device_connected(True)
            self.publisher.publish_device_status(True, self.source.device_name)
            self._write_line(
                "Synthetic source connected"
                if self.source.display_name == "MOCK / SYNTHETIC STREAM"
                else "Muse connected"
            )
            self._write_line("Sampling: {0} Hz".format(SAMPLING_RATE_HZ))
            self._write_line(
                "Channels: {0}".format(" / ".join(MUSE_EEG_CHANNEL_ORDER))
            )

            while not self._stop_event.is_set():
                chunk = self.source.read_chunk()
                if chunk is None:
                    self._stop_event.wait(self.poll_interval)
                    continue

                # Realtime EEG branches before waiting for the model window.
                self.publisher.publish_eeg_chunk(chunk)
                for candidate in buffer.append(chunk):
                    validation = validator.validate(candidate)
                    if not validation.valid:
                        self._write_line(
                            "WINDOW SKIPPED: {0}".format(validation.reason)
                        )
                        continue

                    try:
                        prediction = self.inference_service.predict(candidate)
                    except InvalidModelInput as error:
                        self._write_line("MODEL INPUT INVALID: {0}".format(error))
                        continue
                    except InvalidModelOutput as error:
                        self._write_line("MODEL OUTPUT INVALID: {0}".format(error))
                        continue
                    except ModelExecutionError as error:
                        self._write_line("MODEL EXECUTION ERROR: {0}".format(error))
                        continue

                    self.publisher.publish_prediction(
                        prediction,
                        timestamp=float(candidate.timestamps[-1]),
                    )

                self._stop_event.wait(self.poll_interval)
        except Exception as error:
            self._write_line("Local source stopped: {0}".format(error))
        finally:
            try:
                self.source.close()
            finally:
                if connected:
                    self._write_line(
                        "Synthetic stream stopped"
                        if self.source.display_name == "MOCK / SYNTHETIC STREAM"
                        else "Muse stream stopped"
                    )
                self.state.set_device_connected(False)
                self.publisher.publish_device_status(
                    False,
                    self.source.device_name,
                )
