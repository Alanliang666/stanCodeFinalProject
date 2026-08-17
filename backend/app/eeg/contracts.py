"""Internal raw EEG contracts shared by acquisition and future consumers."""

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np


SAMPLING_RATE_HZ = 256
MUSE_EEG_CHANNEL_ORDER: Tuple[str, ...] = (
    "TP9",
    "AF7",
    "AF8",
    "TP10",
)
CHANNEL_COUNT = len(MUSE_EEG_CHANNEL_ORDER)


@dataclass(frozen=True)
class EEGChunk:
    """Variable-size raw Muse EEG chunk in time-major ``(N, 4)`` form."""

    sampling_rate_hz: int
    channel_order: Tuple[str, ...]
    timestamps: np.ndarray
    samples: np.ndarray
    sample_count: int = field(init=False)

    def __post_init__(self) -> None:
        timestamps = np.array(self.timestamps, dtype=np.float64, copy=True)
        samples = np.array(self.samples, dtype=np.float64, copy=True)
        channel_order = tuple(self.channel_order)

        if self.sampling_rate_hz != SAMPLING_RATE_HZ:
            raise ValueError(
                "sampling_rate_hz must be {0}".format(SAMPLING_RATE_HZ)
            )
        if channel_order != MUSE_EEG_CHANNEL_ORDER:
            raise ValueError(
                "channel_order must be {0}".format(MUSE_EEG_CHANNEL_ORDER)
            )
        if timestamps.ndim != 1:
            raise ValueError("timestamps must have shape (N,)")
        if samples.ndim != 2 or samples.shape[1] != CHANNEL_COUNT:
            raise ValueError(
                "samples must have shape (N, {0})".format(CHANNEL_COUNT)
            )
        if samples.shape[0] != timestamps.shape[0]:
            raise ValueError(
                "timestamps and samples must contain the same sample count"
            )
        if samples.shape[0] == 0:
            raise ValueError("EEGChunk must contain at least one sample")
        if not np.all(np.isfinite(timestamps)):
            raise ValueError("timestamps must contain only finite values")

        timestamps.setflags(write=False)
        samples.setflags(write=False)
        object.__setattr__(self, "channel_order", channel_order)
        object.__setattr__(self, "timestamps", timestamps)
        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "sample_count", int(samples.shape[0]))
