"""FIFO ring buffer that creates fixed-size raw EEG window candidates."""

from collections import deque
from itertools import islice
from typing import Deque, List

import numpy as np

from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)


WINDOW_SECONDS = 1
WINDOW_SIZE = SAMPLING_RATE_HZ * WINDOW_SECONDS
DEFAULT_STRIDE = WINDOW_SIZE


class EEGInferenceBuffer:
    """Accumulates variable-size chunks and emits ``(256, 4)`` candidates."""

    def __init__(
        self,
        window_size: int = WINDOW_SIZE,
        stride: int = DEFAULT_STRIDE,
    ) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        if stride <= 0 or stride > window_size:
            raise ValueError("stride must be between 1 and window_size")

        self.window_size = window_size
        self.stride = stride
        self._timestamps: Deque[float] = deque()
        self._samples: Deque[np.ndarray] = deque()

    @property
    def buffered_sample_count(self) -> int:
        return len(self._timestamps)

    def clear(self) -> None:
        self._timestamps.clear()
        self._samples.clear()

    def append(self, chunk: EEGChunk) -> List[EEGChunk]:
        if chunk.sampling_rate_hz != SAMPLING_RATE_HZ:
            raise ValueError("chunk sampling rate does not match the buffer")
        if chunk.channel_order != MUSE_EEG_CHANNEL_ORDER:
            raise ValueError("chunk channel order does not match the buffer")

        self._timestamps.extend(float(value) for value in chunk.timestamps)
        self._samples.extend(
            np.array(row, dtype=np.float64, copy=True)
            for row in chunk.samples
        )

        candidates: List[EEGChunk] = []
        while self.buffered_sample_count >= self.window_size:
            timestamps = np.fromiter(
                islice(self._timestamps, 0, self.window_size),
                dtype=np.float64,
                count=self.window_size,
            )
            samples = np.vstack(
                list(islice(self._samples, 0, self.window_size))
            )
            candidates.append(
                EEGChunk(
                    sampling_rate_hz=SAMPLING_RATE_HZ,
                    channel_order=MUSE_EEG_CHANNEL_ORDER,
                    timestamps=timestamps,
                    samples=samples,
                )
            )

            for _ in range(self.stride):
                self._timestamps.popleft()
                self._samples.popleft()

        return candidates
