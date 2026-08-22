"""FIFO ring buffer that creates fixed-size raw EEG window candidates."""

from collections import deque
from itertools import islice
from typing import Deque, List

import numpy as np

from backend.app.config import (
    DEFAULT_EEG_STRIDE_SAMPLES,
    DEFAULT_EEG_WINDOW_SAMPLES,
)
from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)


class EEGInferenceBuffer:
    """Accumulates variable-size chunks and emits configured candidates."""

    def __init__(
        self,
        window_samples: int = DEFAULT_EEG_WINDOW_SAMPLES,
        stride_samples: int = DEFAULT_EEG_STRIDE_SAMPLES,
    ) -> None:
        if window_samples <= 0:
            raise ValueError("window_samples must be positive")
        if stride_samples <= 0 or stride_samples > window_samples:
            raise ValueError(
                "stride_samples must be between 1 and window_samples"
            )

        self.window_samples = window_samples
        self.stride_samples = stride_samples
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
        while self.buffered_sample_count >= self.window_samples:
            timestamps = np.fromiter(
                islice(self._timestamps, 0, self.window_samples),
                dtype=np.float64,
                count=self.window_samples,
            )
            samples = np.vstack(
                list(islice(self._samples, 0, self.window_samples))
            )
            candidates.append(
                EEGChunk(
                    sampling_rate_hz=SAMPLING_RATE_HZ,
                    channel_order=MUSE_EEG_CHANNEL_ORDER,
                    timestamps=timestamps,
                    samples=samples,
                )
            )

            for _ in range(self.stride_samples):
                self._timestamps.popleft()
                self._samples.popleft()

        return candidates
