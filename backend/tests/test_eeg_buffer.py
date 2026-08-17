"""Tests for variable BrainFlow chunk accumulation and window emission."""

import unittest

import numpy as np

from backend.app.eeg.buffer import EEGInferenceBuffer, WINDOW_SIZE
from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)
from backend.tests.helpers import make_chunk


class EEGInferenceBufferTests(unittest.TestCase):
    def test_variable_size_chunks_accumulate_without_emitting_early(self) -> None:
        buffer = EEGInferenceBuffer()
        start_index = 0

        for sample_count in (17, 9, 32):
            candidates = buffer.append(make_chunk(sample_count, start_index))
            self.assertEqual(candidates, [])
            start_index += sample_count

        self.assertEqual(buffer.buffered_sample_count, 58)

    def test_fewer_than_256_samples_does_not_emit_window(self) -> None:
        buffer = EEGInferenceBuffer()

        candidates = buffer.append(make_chunk(WINDOW_SIZE - 1))

        self.assertEqual(candidates, [])
        self.assertEqual(buffer.buffered_sample_count, WINDOW_SIZE - 1)

    def test_exactly_256_samples_emits_one_time_major_window(self) -> None:
        buffer = EEGInferenceBuffer()

        candidates = buffer.append(make_chunk(WINDOW_SIZE))

        self.assertEqual(len(candidates), 1)
        window = candidates[0]
        self.assertEqual(window.sample_count, WINDOW_SIZE)
        self.assertEqual(window.samples.shape, (256, 4))
        self.assertEqual(window.timestamps.shape, (256,))
        self.assertEqual(window.channel_order, MUSE_EEG_CHANNEL_ORDER)
        np.testing.assert_array_equal(
            window.samples[0],
            np.array([0.0, 1_000.0, 2_000.0, 3_000.0]),
        )
        self.assertEqual(buffer.buffered_sample_count, 0)

    def test_channel_order_is_fixed_by_contract(self) -> None:
        samples = np.zeros((1, 4), dtype=np.float64)
        timestamps = np.zeros(1, dtype=np.float64)

        with self.assertRaisesRegex(ValueError, "channel_order"):
            EEGChunk(
                sampling_rate_hz=SAMPLING_RATE_HZ,
                channel_order=("AF7", "AF8", "TP9", "TP10"),
                timestamps=timestamps,
                samples=samples,
            )

    def test_stride_128_supports_overlapping_future_windows(self) -> None:
        buffer = EEGInferenceBuffer(stride=128)

        first_candidates = buffer.append(make_chunk(256))
        second_candidates = buffer.append(make_chunk(128, start_index=256))

        self.assertEqual(len(first_candidates), 1)
        self.assertEqual(len(second_candidates), 1)
        self.assertEqual(buffer.buffered_sample_count, 128)
        self.assertAlmostEqual(second_candidates[0].timestamps[0], 128 / 256)


if __name__ == "__main__":
    unittest.main()
