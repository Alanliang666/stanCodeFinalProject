"""Tests for the timestamp continuity gate before future inference."""

import unittest

import numpy as np

from backend.app.eeg.buffer import WINDOW_SIZE
from backend.app.eeg.window_validator import (
    EEGWindowValidator,
    filter_valid_windows,
)
from backend.tests.helpers import make_chunk, make_timestamps


class EEGWindowValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = EEGWindowValidator()

    def test_exact_256_hz_timestamps_pass(self) -> None:
        window = make_chunk(WINDOW_SIZE)

        result = self.validator.validate(window)

        self.assertTrue(result.valid)
        self.assertIsNone(result.reason)
        self.assertAlmostEqual(result.duration_seconds, 255 / 256)

    def test_large_artificial_timestamp_gap_fails(self) -> None:
        timestamps = make_timestamps(WINDOW_SIZE)
        timestamps[128:] += 0.1
        window = make_chunk(WINDOW_SIZE, timestamps=timestamps)

        result = self.validator.validate(window)

        self.assertFalse(result.valid)
        self.assertIn("timestamp gap detected", result.reason or "")

    def test_one_missing_sample_interval_fails(self) -> None:
        timestamps = make_timestamps(WINDOW_SIZE)
        timestamps[128:] += 1 / 256
        window = make_chunk(WINDOW_SIZE, timestamps=timestamps)

        result = self.validator.validate(window)

        self.assertFalse(result.valid)
        self.assertIn("timestamp gap detected", result.reason or "")

    def test_non_increasing_timestamps_fail(self) -> None:
        timestamps = make_timestamps(WINDOW_SIZE)
        timestamps[128] = timestamps[127]
        window = make_chunk(WINDOW_SIZE, timestamps=timestamps)

        result = self.validator.validate(window)

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "timestamps must be strictly increasing")

    def test_candidate_with_wrong_sample_count_fails(self) -> None:
        candidate = make_chunk(WINDOW_SIZE - 1)

        result = self.validator.validate(candidate)

        self.assertFalse(result.valid)
        self.assertIn("sample count", result.reason or "")

    def test_filter_excludes_invalid_candidate_before_inference(self) -> None:
        valid = make_chunk(WINDOW_SIZE)
        timestamps = make_timestamps(WINDOW_SIZE, start_index=WINDOW_SIZE)
        timestamps[64:] += 0.2
        invalid = make_chunk(
            WINDOW_SIZE,
            start_index=WINDOW_SIZE,
            timestamps=timestamps,
        )

        accepted = filter_valid_windows([valid, invalid], self.validator)

        self.assertEqual(accepted, [valid])


if __name__ == "__main__":
    unittest.main()
