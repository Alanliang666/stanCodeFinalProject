"""Timestamp continuity validation for configured raw EEG candidates."""

from dataclasses import dataclass
from typing import Iterable, List, Optional

import numpy as np

from backend.app.config import DEFAULT_EEG_WINDOW_SAMPLES
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
        window_samples: int = DEFAULT_EEG_WINDOW_SAMPLES,
        max_interval_multiplier: float = MAX_INTERVAL_MULTIPLIER,
        duration_tolerance_ratio: float = DURATION_TOLERANCE_RATIO,
    ) -> None:
        if window_samples <= 0:
            raise ValueError("window_samples must be positive")
        if max_interval_multiplier <= 1:
            raise ValueError("max_interval_multiplier must be greater than 1")
        if duration_tolerance_ratio < 0:
            raise ValueError("duration_tolerance_ratio cannot be negative")

        self.window_samples = window_samples
        self.expected_duration_seconds = (
            (window_samples - 1) * EXPECTED_SAMPLE_INTERVAL_SECONDS
        )
        self.max_interval_seconds = (
            EXPECTED_SAMPLE_INTERVAL_SECONDS * max_interval_multiplier
        )
        self.duration_tolerance_ratio = duration_tolerance_ratio

    def validate(self, window: EEGChunk) -> WindowValidationResult:
        if window.sample_count != self.window_samples:
            return WindowValidationResult(
                valid=False,
                reason="sample count must be {0}".format(self.window_samples),
            )
        if window.channel_order != MUSE_EEG_CHANNEL_ORDER:
            return WindowValidationResult(
                valid=False,
                reason="channel order mismatch",
            )
        if window.samples.shape != (
            self.window_samples,
            len(MUSE_EEG_CHANNEL_ORDER),
        ):
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

        largest_interval = float(np.max(intervals)) if intervals.size else 0.0
        if largest_interval > self.max_interval_seconds:
            return WindowValidationResult(
                valid=False,
                reason=(
                    "timestamp gap detected: {0:.6f}s exceeds {1:.6f}s"
                ).format(largest_interval, self.max_interval_seconds),
            )

        duration = float(window.timestamps[-1] - window.timestamps[0])
        duration_tolerance = (
            self.expected_duration_seconds * self.duration_tolerance_ratio
        )
        if (
            abs(duration - self.expected_duration_seconds)
            > duration_tolerance
        ):
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
