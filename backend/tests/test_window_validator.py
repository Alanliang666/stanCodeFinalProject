"""Tests for the timestamp continuity gate before future inference."""

import unittest

from backend.app.eeg.window_validator import (
    EXPECTED_SAMPLE_INTERVAL_SECONDS,
    EEGWindowValidator,
    filter_valid_windows,
)
from backend.tests.helpers import make_chunk, make_timestamps


class EEGWindowValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = EEGWindowValidator()

    def test_exact_256_hz_timestamps_pass(self) -> None:
        window = make_chunk(256)

        result = self.validator.validate(window)

        self.assertTrue(result.valid)
        self.assertIsNone(result.reason)
        self.assertAlmostEqual(result.duration_seconds, 255 / 256)

    def test_512_window_is_accepted_with_derived_duration(self) -> None:
        validator = EEGWindowValidator(window_samples=512)

        result = validator.validate(make_chunk(512))

        self.assertTrue(result.valid)
        self.assertAlmostEqual(result.duration_seconds, 511 / 256)
        self.assertAlmostEqual(
            validator.expected_duration_seconds,
            511 / 256,
        )

    def test_512_mode_rejects_256_window(self) -> None:
        result = EEGWindowValidator(window_samples=512).validate(
            make_chunk(256)
        )

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "sample count must be 512")

    def test_expected_interval_remains_one_over_256_for_all_windows(self) -> None:
        self.assertEqual(EXPECTED_SAMPLE_INTERVAL_SECONDS, 1 / 256)
        for window_samples in (256, 512):
            with self.subTest(window_samples=window_samples):
                validator = EEGWindowValidator(
                    window_samples=window_samples
                )
                self.assertAlmostEqual(
                    validator.max_interval_seconds,
                    (1 / 256) * 1.5,
                )

    def test_large_artificial_timestamp_gap_fails(self) -> None:
        timestamps = make_timestamps(256)
        timestamps[128:] += 0.1
        window = make_chunk(256, timestamps=timestamps)

        result = self.validator.validate(window)

        self.assertFalse(result.valid)
        self.assertIn("timestamp gap detected", result.reason or "")

    def test_one_missing_sample_interval_fails(self) -> None:
        timestamps = make_timestamps(256)
        timestamps[128:] += 1 / 256
        window = make_chunk(256, timestamps=timestamps)

        result = self.validator.validate(window)

        self.assertFalse(result.valid)
        self.assertIn("timestamp gap detected", result.reason or "")

    def test_non_increasing_timestamps_fail(self) -> None:
        timestamps = make_timestamps(256)
        timestamps[128] = timestamps[127]
        window = make_chunk(256, timestamps=timestamps)

        result = self.validator.validate(window)

        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "timestamps must be strictly increasing")

    def test_candidate_with_wrong_sample_count_fails(self) -> None:
        candidate = make_chunk(255)

        result = self.validator.validate(candidate)

        self.assertFalse(result.valid)
        self.assertIn("sample count", result.reason or "")

    def test_filter_excludes_invalid_candidate_before_inference(self) -> None:
        valid = make_chunk(256)
        timestamps = make_timestamps(256, start_index=256)
        timestamps[64:] += 0.2
        invalid = make_chunk(
            256,
            start_index=256,
            timestamps=timestamps,
        )

        accepted = filter_valid_windows([valid, invalid], self.validator)

        self.assertEqual(accepted, [valid])


if __name__ == "__main__":
    unittest.main()
