"""Tests for Muse Phase 1 runtime statistics."""

import unittest

import numpy as np

from backend.app.eeg.diagnostics import MusePhase1Diagnostics
from backend.app.eeg.window_validator import (
    EXPECTED_SAMPLE_INTERVAL_SECONDS,
    EEGWindowValidator,
)
from backend.tests.helpers import make_chunk, make_timestamps


class MusePhase1DiagnosticsTests(unittest.TestCase):
    def test_chunk_distribution_and_intervals_cross_chunk_boundaries(self) -> None:
        now = [100.0]
        diagnostics = MusePhase1Diagnostics(clock=lambda: now[0])

        diagnostics.observe_chunk(make_chunk(12, start_index=0))
        diagnostics.observe_chunk(make_chunk(24, start_index=12))
        now[0] = 105.0
        summary = diagnostics.snapshot()

        self.assertEqual(summary.runtime_seconds, 5.0)
        self.assertEqual(summary.total_chunks, 2)
        self.assertEqual(
            summary.chunk_sample_count_distribution,
            {12: 1, 24: 1},
        )
        self.assertEqual(summary.total_samples, 36)
        self.assertAlmostEqual(
            summary.timestamp_interval_mean_seconds,
            EXPECTED_SAMPLE_INTERVAL_SECONDS,
        )
        self.assertAlmostEqual(
            summary.timestamp_interval_min_seconds,
            EXPECTED_SAMPLE_INTERVAL_SECONDS,
        )
        self.assertAlmostEqual(
            summary.timestamp_interval_max_seconds,
            EXPECTED_SAMPLE_INTERVAL_SECONDS,
        )

    def test_gap_counters_distinguish_1_5x_from_2_0x(self) -> None:
        expected = EXPECTED_SAMPLE_INTERVAL_SECONDS
        timestamps = np.array(
            [
                0.0,
                expected,
                expected + 0.006133,
                expected + 0.006133 + (expected * 2.1),
            ],
            dtype=np.float64,
        )
        diagnostics = MusePhase1Diagnostics()

        diagnostics.observe_chunk(make_chunk(4, timestamps=timestamps))
        summary = diagnostics.snapshot()

        self.assertEqual(summary.gaps_over_1_5x_expected, 2)
        self.assertEqual(summary.gaps_over_2_0x_expected, 1)
        self.assertAlmostEqual(summary.timestamp_interval_max_seconds, expected * 2.1)

    def test_candidate_statistics_track_pass_fail_and_maximum_gap(self) -> None:
        diagnostics = MusePhase1Diagnostics()
        validator = EEGWindowValidator()
        passing_candidate = make_chunk(256)
        failing_timestamps = make_timestamps(256, start_index=256)
        gap_adjustment = 0.006133 - EXPECTED_SAMPLE_INTERVAL_SECONDS
        failing_timestamps[128:] += gap_adjustment
        failing_candidate = make_chunk(
            256,
            start_index=256,
            timestamps=failing_timestamps,
        )

        pass_diagnostic = diagnostics.observe_candidate(
            passing_candidate,
            validator.validate(passing_candidate),
        )
        fail_diagnostic = diagnostics.observe_candidate(
            failing_candidate,
            validator.validate(failing_candidate),
        )
        summary = diagnostics.snapshot()

        self.assertEqual(summary.total_candidate_windows, 2)
        self.assertEqual(summary.pass_windows, 1)
        self.assertEqual(summary.fail_windows, 1)
        self.assertEqual(summary.pass_percentage, 50.0)
        self.assertAlmostEqual(
            pass_diagnostic.maximum_timestamp_gap_seconds,
            EXPECTED_SAMPLE_INTERVAL_SECONDS,
        )
        self.assertAlmostEqual(
            fail_diagnostic.maximum_timestamp_gap_seconds,
            0.006133,
        )
        self.assertIsNotNone(summary.window_duration_mean_seconds)
        self.assertIsNotNone(summary.window_duration_min_seconds)
        self.assertIsNotNone(summary.window_duration_max_seconds)

    def test_formatted_summary_contains_required_sections(self) -> None:
        diagnostics = MusePhase1Diagnostics()

        summary = diagnostics.format_summary()

        self.assertIn("=== Muse Phase 1 Summary ===", summary)
        self.assertIn("Chunk Sample Count Distribution:", summary)
        self.assertIn("Window Duration", summary)
        self.assertIn("Timestamp Interval", summary)
        self.assertIn(">1.5x", summary)
        self.assertIn(">2.0x", summary)


if __name__ == "__main__":
    unittest.main()
