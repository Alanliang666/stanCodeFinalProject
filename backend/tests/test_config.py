"""Tests for centralized EEG inference runtime configuration."""

import unittest

from backend.app.config import (
    EEGInferenceConfig,
    EEGInferenceConfigError,
    load_eeg_inference_config,
)


class EEGInferenceConfigTests(unittest.TestCase):
    def test_defaults_are_256_non_overlapping_samples(self) -> None:
        config = load_eeg_inference_config({})

        self.assertEqual(config.window_samples, 256)
        self.assertEqual(config.stride_samples, 256)
        self.assertEqual(config.sampling_rate_hz, 256)
        self.assertEqual(config.window_size_sec, 1.0)
        self.assertEqual(config.stride_sec, 1.0)

    def test_environment_is_parsed_once_into_derived_values(self) -> None:
        config = load_eeg_inference_config(
            {
                "EEG_WINDOW_SAMPLES": "512",
                "EEG_STRIDE_SAMPLES": "256",
            }
        )

        self.assertEqual(config.window_samples, 512)
        self.assertEqual(config.stride_samples, 256)
        self.assertEqual(config.window_size_sec, 2.0)
        self.assertEqual(config.stride_sec, 1.0)

    def test_stride_greater_than_window_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            EEGInferenceConfigError,
            "must not exceed",
        ):
            EEGInferenceConfig(window_samples=256, stride_samples=512)

    def test_non_positive_window_is_rejected(self) -> None:
        for window_samples in (0, -1):
            with self.subTest(window_samples=window_samples):
                with self.assertRaisesRegex(
                    EEGInferenceConfigError,
                    "window_samples must be positive",
                ):
                    EEGInferenceConfig(
                        window_samples=window_samples,
                        stride_samples=1,
                    )

    def test_non_positive_stride_is_rejected(self) -> None:
        for stride_samples in (0, -1):
            with self.subTest(stride_samples=stride_samples):
                with self.assertRaisesRegex(
                    EEGInferenceConfigError,
                    "stride_samples must be positive",
                ):
                    EEGInferenceConfig(
                        window_samples=256,
                        stride_samples=stride_samples,
                    )

    def test_non_integer_environment_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            EEGInferenceConfigError,
            "EEG_WINDOW_SAMPLES must be an integer",
        ):
            load_eeg_inference_config(
                {
                    "EEG_WINDOW_SAMPLES": "two seconds",
                    "EEG_STRIDE_SAMPLES": "256",
                }
            )


if __name__ == "__main__":
    unittest.main()
