"""Hardware-independent tests for BrainFlow matrix conversion."""

import unittest

import numpy as np

from backend.app.eeg.contracts import MUSE_EEG_CHANNEL_ORDER
from backend.app.muse.muse_collector import MuseCollector


class _FakeBoard:
    def __init__(self, board_data: np.ndarray) -> None:
        self._board_data = board_data

    def get_board_data(self) -> np.ndarray:
        return self._board_data


class MuseCollectorReadTests(unittest.TestCase):
    def test_brainflow_channel_major_matrix_becomes_time_major_chunk(self) -> None:
        # BrainFlow rows intentionally do not match the required product order.
        board_data = np.array(
            [
                [10.0, 10.1, 10.2],  # timestamp row
                [70.0, 71.0, 72.0],  # AF7
                [100.0, 101.0, 102.0],  # TP10
                [90.0, 91.0, 92.0],  # TP9
                [80.0, 81.0, 82.0],  # AF8
            ],
            dtype=np.float64,
        )
        collector = MuseCollector()
        collector._board = _FakeBoard(board_data)
        collector._streaming = True
        collector._ordered_eeg_rows = (3, 1, 4, 2)
        collector._timestamp_row = 0

        chunk = collector.read_chunk()

        self.assertIsNotNone(chunk)
        assert chunk is not None
        self.assertEqual(chunk.channel_order, MUSE_EEG_CHANNEL_ORDER)
        self.assertEqual(chunk.samples.shape, (3, 4))
        np.testing.assert_array_equal(
            chunk.samples,
            np.array(
                [
                    [90.0, 70.0, 80.0, 100.0],
                    [91.0, 71.0, 81.0, 101.0],
                    [92.0, 72.0, 82.0, 102.0],
                ]
            ),
        )
        np.testing.assert_array_equal(
            chunk.timestamps,
            np.array([10.0, 10.1, 10.2]),
        )

    def test_empty_brainflow_read_returns_no_chunk(self) -> None:
        collector = MuseCollector()
        collector._board = _FakeBoard(np.empty((5, 0)))
        collector._streaming = True
        collector._ordered_eeg_rows = (3, 1, 4, 2)
        collector._timestamp_row = 0

        self.assertIsNone(collector.read_chunk())


if __name__ == "__main__":
    unittest.main()
