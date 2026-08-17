"""Timestamp continuity validation for raw one-second EEG candidates."""

from dataclasses import dataclass
from typing import Iterable, List, Optional

import numpy as np

from backend.app.eeg.buffer import WINDOW_SIZE
from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)


EXPECTED_SAMPLE_INTERVAL_SECONDS = 1.0 / SAMPLING_RATE_HZ
MAX_INTERVAL_MULTIPLIER = 1.5
DURATION_TOLERANCE_RATIO = 0.10


@dataclass(frozen=True)
class WindowValidationResult:
    valid: bool
    reason: Optional[str] = None
    duration_seconds: Optional[float] = None


class EEGWindowValidator:
    """Rejects incomplete, misordered, or discontinuous raw EEG windows."""

    def __init__(
        self,
        max_interval_multiplier: float = MAX_INTERVAL_MULTIPLIER,
        duration_tolerance_ratio: float = DURATION_TOLERANCE_RATIO,
    ) -> None:
        if max_interval_multiplier <= 1:
            raise ValueError("max_interval_multiplier must be greater than 1")
        if duration_tolerance_ratio < 0:
            raise ValueError("duration_tolerance_ratio cannot be negative")

        self.max_interval_seconds = (
            EXPECTED_SAMPLE_INTERVAL_SECONDS * max_interval_multiplier
        )
        self.duration_tolerance_ratio = duration_tolerance_ratio

    def validate(self, window: EEGChunk) -> WindowValidationResult:
        if window.sample_count != WINDOW_SIZE:
            return WindowValidationResult(
                valid=False,
                reason="sample count must be {0}".format(WINDOW_SIZE),
            )
        if window.channel_order != MUSE_EEG_CHANNEL_ORDER:
            return WindowValidationResult(
                valid=False,
                reason="channel order mismatch",
            )
        if window.samples.shape != (WINDOW_SIZE, len(MUSE_EEG_CHANNEL_ORDER)):
            return WindowValidationResult(
                valid=False,
                reason="sample shape mismatch",
            )

        intervals = np.diff(window.timestamps)
        if np.any(intervals <= 0):
            return WindowValidationResult(
                valid=False,
                reason="timestamps must be strictly increasing",
            )

        largest_interval = float(np.max(intervals))
        if largest_interval > self.max_interval_seconds:
            return WindowValidationResult(
                valid=False,
                reason=(
                    "timestamp gap detected: {0:.6f}s exceeds {1:.6f}s"
                ).format(largest_interval, self.max_interval_seconds),
            )

        duration = float(window.timestamps[-1] - window.timestamps[0])
        expected_duration = (
            (WINDOW_SIZE - 1) * EXPECTED_SAMPLE_INTERVAL_SECONDS
        )
        duration_tolerance = expected_duration * self.duration_tolerance_ratio
        if abs(duration - expected_duration) > duration_tolerance:
            return WindowValidationResult(
                valid=False,
                reason=(
                    "window duration {0:.6f}s is outside the allowed range"
                ).format(duration),
                duration_seconds=duration,
            )

        return WindowValidationResult(
            valid=True,
            duration_seconds=duration,
        )


def filter_valid_windows(
    candidates: Iterable[EEGChunk],
    validator: Optional[EEGWindowValidator] = None,
) -> List[EEGChunk]:
    """Gate candidates before the future inference stage."""

    active_validator = validator or EEGWindowValidator()
    return [
        candidate
        for candidate in candidates
        if active_validator.validate(candidate).valid
    ]
