"""Tests for variable BrainFlow chunk accumulation and window emission."""

import unittest

import numpy as np

from backend.app.eeg.buffer import EEGInferenceBuffer
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

    def test_fewer_than_configured_samples_does_not_emit_window(self) -> None:
        buffer = EEGInferenceBuffer()

        candidates = buffer.append(make_chunk(255))

        self.assertEqual(candidates, [])
        self.assertEqual(buffer.buffered_sample_count, 255)

    def test_256_window_and_stride_accumulate_variable_chunks(self) -> None:
        buffer = EEGInferenceBuffer(
            window_samples=256,
            stride_samples=256,
        )

        candidates = []
        start_index = 0
        for sample_count in (17, 71, 32, 136):
            candidates.extend(
                buffer.append(make_chunk(sample_count, start_index))
            )
            start_index += sample_count

        self.assertEqual(len(candidates), 1)
        window = candidates[0]
        self.assertEqual(window.sample_count, 256)
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

    def test_512_window_and_stride_emit_non_overlapping_windows(self) -> None:
        buffer = EEGInferenceBuffer(
            window_samples=512,
            stride_samples=512,
        )

        candidates = buffer.append(make_chunk(1_024))

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].samples.shape, (512, 4))
        self.assertEqual(candidates[1].samples.shape, (512, 4))
        self.assertEqual(candidates[0].samples[0, 0], 0.0)
        self.assertEqual(candidates[0].samples[-1, 0], 511.0)
        self.assertEqual(candidates[1].samples[0, 0], 512.0)
        self.assertEqual(candidates[1].samples[-1, 0], 1_023.0)
        self.assertEqual(buffer.buffered_sample_count, 0)

    def test_512_window_with_256_stride_retains_overlap(self) -> None:
        buffer = EEGInferenceBuffer(
            window_samples=512,
            stride_samples=256,
        )

        candidates = buffer.append(make_chunk(768))

        self.assertEqual(len(candidates), 2)
        np.testing.assert_array_equal(
            candidates[0].samples[:, 0],
            np.arange(0, 512),
        )
        np.testing.assert_array_equal(
            candidates[1].samples[:, 0],
            np.arange(256, 768),
        )
        self.assertEqual(buffer.buffered_sample_count, 256)


if __name__ == "__main__":
    unittest.main()
