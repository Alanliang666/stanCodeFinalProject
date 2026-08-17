"""Streaming diagnostics for the Muse Phase 1 development runtime."""

from collections import Counter
from dataclasses import dataclass
import time
from typing import Callable, Dict, Optional

import numpy as np

from backend.app.eeg.contracts import EEGChunk
from backend.app.eeg.window_validator import (
    EXPECTED_SAMPLE_INTERVAL_SECONDS,
    WindowValidationResult,
)


DIAGNOSTIC_GAP_MULTIPLIER = 1.5
MISSING_SAMPLE_GAP_MULTIPLIER = 2.0


@dataclass(frozen=True)
class CandidateDiagnostic:
    """Measurements for one candidate, independent of its PASS/FAIL result."""

    duration_seconds: float
    maximum_timestamp_gap_seconds: Optional[float]


@dataclass(frozen=True)
class MusePhase1Summary:
    runtime_seconds: float
    total_chunks: int
    chunk_sample_count_distribution: Dict[int, int]
    total_samples: int
    total_candidate_windows: int
    pass_windows: int
    fail_windows: int
    pass_percentage: float
    window_duration_mean_seconds: Optional[float]
    window_duration_min_seconds: Optional[float]
    window_duration_max_seconds: Optional[float]
    timestamp_interval_mean_seconds: Optional[float]
    timestamp_interval_min_seconds: Optional[float]
    timestamp_interval_max_seconds: Optional[float]
    gaps_over_1_5x_expected: int
    gaps_over_2_0x_expected: int


class MusePhase1Diagnostics:
    """Collects streaming statistics without changing validation decisions."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        self._started_at = clock()
        self._total_chunks = 0
        self._chunk_sample_counts: Counter = Counter()
        self._total_samples = 0
        self._total_candidate_windows = 0
        self._pass_windows = 0
        self._fail_windows = 0

        self._window_duration_count = 0
        self._window_duration_sum = 0.0
        self._window_duration_min: Optional[float] = None
        self._window_duration_max: Optional[float] = None

        self._timestamp_interval_count = 0
        self._timestamp_interval_sum = 0.0
        self._timestamp_interval_min: Optional[float] = None
        self._timestamp_interval_max: Optional[float] = None
        self._gaps_over_1_5x_expected = 0
        self._gaps_over_2_0x_expected = 0
        self._last_timestamp: Optional[float] = None

    def observe_chunk(self, chunk: EEGChunk) -> None:
        """Records chunk sizes and continuous intervals across chunk boundaries."""

        self._total_chunks += 1
        self._chunk_sample_counts[chunk.sample_count] += 1
        self._total_samples += chunk.sample_count

        internal_intervals = np.diff(chunk.timestamps)
        if self._last_timestamp is None:
            intervals = internal_intervals
        else:
            boundary_interval = np.array(
                [float(chunk.timestamps[0]) - self._last_timestamp],
                dtype=np.float64,
            )
            intervals = np.concatenate((boundary_interval, internal_intervals))

        if intervals.size:
            self._timestamp_interval_count += int(intervals.size)
            self._timestamp_interval_sum += float(np.sum(intervals))
            interval_min = float(np.min(intervals))
            interval_max = float(np.max(intervals))
            self._timestamp_interval_min = self._minimum(
                self._timestamp_interval_min,
                interval_min,
            )
            self._timestamp_interval_max = self._maximum(
                self._timestamp_interval_max,
                interval_max,
            )
            self._gaps_over_1_5x_expected += int(
                np.count_nonzero(
                    intervals
                    > EXPECTED_SAMPLE_INTERVAL_SECONDS
                    * DIAGNOSTIC_GAP_MULTIPLIER
                )
            )
            self._gaps_over_2_0x_expected += int(
                np.count_nonzero(
                    intervals
                    > EXPECTED_SAMPLE_INTERVAL_SECONDS
                    * MISSING_SAMPLE_GAP_MULTIPLIER
                )
            )

        self._last_timestamp = float(chunk.timestamps[-1])

    def observe_candidate(
        self,
        candidate: EEGChunk,
        validation: WindowValidationResult,
    ) -> CandidateDiagnostic:
        """Records one fixed window and returns details for runtime logging."""

        self._total_candidate_windows += 1
        if validation.valid:
            self._pass_windows += 1
        else:
            self._fail_windows += 1

        duration = float(candidate.timestamps[-1] - candidate.timestamps[0])
        self._window_duration_count += 1
        self._window_duration_sum += duration
        self._window_duration_min = self._minimum(
            self._window_duration_min,
            duration,
        )
        self._window_duration_max = self._maximum(
            self._window_duration_max,
            duration,
        )

        intervals = np.diff(candidate.timestamps)
        maximum_gap = (
            float(np.max(intervals)) if intervals.size else None
        )
        return CandidateDiagnostic(
            duration_seconds=duration,
            maximum_timestamp_gap_seconds=maximum_gap,
        )

    def snapshot(self) -> MusePhase1Summary:
        total_windows = self._total_candidate_windows
        pass_percentage = (
            (self._pass_windows / total_windows) * 100.0
            if total_windows
            else 0.0
        )
        return MusePhase1Summary(
            runtime_seconds=max(0.0, self._clock() - self._started_at),
            total_chunks=self._total_chunks,
            chunk_sample_count_distribution=dict(
                sorted(self._chunk_sample_counts.items())
            ),
            total_samples=self._total_samples,
            total_candidate_windows=total_windows,
            pass_windows=self._pass_windows,
            fail_windows=self._fail_windows,
            pass_percentage=pass_percentage,
            window_duration_mean_seconds=self._mean_or_none(
                self._window_duration_sum,
                self._window_duration_count,
            ),
            window_duration_min_seconds=self._window_duration_min,
            window_duration_max_seconds=self._window_duration_max,
            timestamp_interval_mean_seconds=self._mean_or_none(
                self._timestamp_interval_sum,
                self._timestamp_interval_count,
            ),
            timestamp_interval_min_seconds=self._timestamp_interval_min,
            timestamp_interval_max_seconds=self._timestamp_interval_max,
            gaps_over_1_5x_expected=self._gaps_over_1_5x_expected,
            gaps_over_2_0x_expected=self._gaps_over_2_0x_expected,
        )

    def format_summary(self) -> str:
        summary = self.snapshot()
        chunk_distribution = self._format_chunk_distribution(
            summary.chunk_sample_count_distribution
        )
        return "\n".join(
            (
                "",
                "=== Muse Phase 1 Summary ===",
                "",
                "Runtime: {0:.1f} sec".format(summary.runtime_seconds),
                "Total Chunks: {0}".format(summary.total_chunks),
                "Chunk Sample Count Distribution:",
                chunk_distribution,
                "Total Samples: {0}".format(summary.total_samples),
                "Total Windows: {0}".format(summary.total_candidate_windows),
                "PASS: {0}".format(summary.pass_windows),
                "FAIL: {0}".format(summary.fail_windows),
                "PASS Rate: {0:.2f}%".format(summary.pass_percentage),
                "",
                "Window Duration (all candidates):",
                "mean {0}".format(
                    self._format_seconds(summary.window_duration_mean_seconds)
                ),
                "min  {0}".format(
                    self._format_seconds(summary.window_duration_min_seconds)
                ),
                "max  {0}".format(
                    self._format_seconds(summary.window_duration_max_seconds)
                ),
                "",
                "Timestamp Interval (continuous stream):",
                "expected {0:.3f} ms".format(
                    EXPECTED_SAMPLE_INTERVAL_SECONDS * 1_000.0
                ),
                "mean     {0}".format(
                    self._format_milliseconds(
                        summary.timestamp_interval_mean_seconds
                    )
                ),
                "min      {0}".format(
                    self._format_milliseconds(
                        summary.timestamp_interval_min_seconds
                    )
                ),
                "max      {0}".format(
                    self._format_milliseconds(
                        summary.timestamp_interval_max_seconds
                    )
                ),
                "",
                "Gap Count:",
                ">1.5x ({0:.3f} ms): {1}".format(
                    EXPECTED_SAMPLE_INTERVAL_SECONDS
                    * DIAGNOSTIC_GAP_MULTIPLIER
                    * 1_000.0,
                    summary.gaps_over_1_5x_expected,
                ),
                ">2.0x ({0:.3f} ms): {1}".format(
                    EXPECTED_SAMPLE_INTERVAL_SECONDS
                    * MISSING_SAMPLE_GAP_MULTIPLIER
                    * 1_000.0,
                    summary.gaps_over_2_0x_expected,
                ),
            )
        )

    @staticmethod
    def _minimum(current: Optional[float], value: float) -> float:
        return value if current is None else min(current, value)

    @staticmethod
    def _maximum(current: Optional[float], value: float) -> float:
        return value if current is None else max(current, value)

    @staticmethod
    def _mean_or_none(total: float, count: int) -> Optional[float]:
        return total / count if count else None

    @staticmethod
    def _format_seconds(value: Optional[float]) -> str:
        return "n/a" if value is None else "{0:.6f} sec".format(value)

    @staticmethod
    def _format_milliseconds(value: Optional[float]) -> str:
        return "n/a" if value is None else "{0:.3f} ms".format(value * 1_000.0)

    @staticmethod
    def _format_chunk_distribution(distribution: Dict[int, int]) -> str:
        if not distribution:
            return "  (none)"
        return "\n".join(
            "  {0} samples: {1} chunks".format(sample_count, chunk_count)
            for sample_count, chunk_count in distribution.items()
        )
