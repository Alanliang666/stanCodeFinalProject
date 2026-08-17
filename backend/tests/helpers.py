"""Deterministic raw EEG fixtures used by backend unit tests."""

from typing import Optional

import numpy as np

from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)


def make_timestamps(
    sample_count: int,
    start_index: int = 0,
) -> np.ndarray:
    return (
        start_index + np.arange(sample_count, dtype=np.float64)
    ) / SAMPLING_RATE_HZ


def make_chunk(
    sample_count: int,
    start_index: int = 0,
    timestamps: Optional[np.ndarray] = None,
) -> EEGChunk:
    sample_indices = start_index + np.arange(
        sample_count,
        dtype=np.float64,
    )
    samples = np.column_stack(
        tuple(sample_indices + (channel_index * 1_000.0) for channel_index in range(4))
    )
    return EEGChunk(
        sampling_rate_hz=SAMPLING_RATE_HZ,
        channel_order=MUSE_EEG_CHANNEL_ORDER,
        timestamps=(
            make_timestamps(sample_count, start_index)
            if timestamps is None
            else timestamps
        ),
        samples=samples,
    )
