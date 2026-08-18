"""BrainFlow-backed Muse 2 EEG acquisition without downstream processing."""

from typing import Any, Dict, Optional, Tuple

import numpy as np

from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)


class BrainFlowUnavailableError(RuntimeError):
    """Raised when hardware acquisition is requested without BrainFlow."""


def _load_brainflow() -> Tuple[Any, Any, Any]:
    try:
        from brainflow.board_shim import (
            BoardIds,
            BoardShim,
            BrainFlowInputParams,
        )
    except ImportError as error:
        raise BrainFlowUnavailableError(
            "BrainFlow is not installed. Run: "
            "python -m pip install -r backend/requirements.txt"
        ) from error

    return BoardShim, BoardIds, BrainFlowInputParams


def _normalize_channel_name(name: str) -> str:
    return str(name).strip().upper()


class MuseCollector:
    """Owns the Muse 2 session and converts default-preset EEG to EEGChunk."""

    def __init__(
        self,
        mac_address: Optional[str] = None,
        serial_number: Optional[str] = None,
    ) -> None:
        self.mac_address = mac_address
        self.serial_number = serial_number
        self._board: Optional[Any] = None
        self._board_id: Optional[int] = None
        self._ordered_eeg_rows: Optional[Tuple[int, ...]] = None
        self._timestamp_row: Optional[int] = None
        self._prepared = False
        self._streaming = False

    def prepare_session(self) -> None:
        if self._prepared:
            return

        BoardShim, BoardIds, BrainFlowInputParams = _load_brainflow()
        board_id = BoardIds.MUSE_2_BOARD.value
        params = BrainFlowInputParams()
        params.other_info = "p21"
        params.timeout = 15
        if self.mac_address:
            params.mac_address = self.mac_address
        if self.serial_number:
            params.serial_number = self.serial_number

        sampling_rate = BoardShim.get_sampling_rate(board_id)
        if sampling_rate != SAMPLING_RATE_HZ:
            raise RuntimeError(
                "Muse 2 sampling rate mismatch: expected {0}, received {1}".format(
                    SAMPLING_RATE_HZ,
                    sampling_rate,
                )
            )

        eeg_rows = BoardShim.get_eeg_channels(board_id)
        eeg_names = BoardShim.get_eeg_names(board_id)
        if len(eeg_rows) != len(eeg_names):
            raise RuntimeError(
                "BrainFlow EEG row metadata does not match EEG channel names"
            )

        row_by_name: Dict[str, int] = {
            _normalize_channel_name(name): int(row)
            for name, row in zip(eeg_names, eeg_rows)
        }
        missing_channels = [
            channel
            for channel in MUSE_EEG_CHANNEL_ORDER
            if channel not in row_by_name
        ]
        if missing_channels:
            raise RuntimeError(
                "BrainFlow Muse 2 metadata is missing required EEG channels: "
                + ", ".join(missing_channels)
            )

        board = BoardShim(board_id, params)
        board.prepare_session()

        self._board = board
        self._board_id = board_id
        self._ordered_eeg_rows = tuple(
            row_by_name[channel] for channel in MUSE_EEG_CHANNEL_ORDER
        )
        self._timestamp_row = int(BoardShim.get_timestamp_channel(board_id))
        self._prepared = True

    def start_stream(self) -> None:
        if not self._prepared or self._board is None:
            raise RuntimeError("prepare_session must be called before start_stream")
        if self._streaming:
            return

        self._board.start_stream()
        self._streaming = True

    def connect(self) -> None:
        self.prepare_session()
        self.start_stream()

    def read_chunk(self) -> Optional[EEGChunk]:
        if not self._streaming or self._board is None:
            raise RuntimeError("Muse stream is not running")
        if self._ordered_eeg_rows is None or self._timestamp_row is None:
            raise RuntimeError("Muse channel metadata has not been initialized")

        board_data = np.asarray(self._board.get_board_data(), dtype=np.float64)
        if board_data.ndim != 2:
            raise RuntimeError("BrainFlow returned a non-matrix board data value")
        if board_data.shape[1] == 0:
            return None

        samples = board_data[list(self._ordered_eeg_rows), :].T
        timestamps = board_data[self._timestamp_row, :]
        return EEGChunk(
            sampling_rate_hz=SAMPLING_RATE_HZ,
            channel_order=MUSE_EEG_CHANNEL_ORDER,
            timestamps=timestamps,
            samples=samples,
        )

    def stop_stream(self) -> None:
        if not self._streaming or self._board is None:
            return

        self._board.stop_stream()
        self._streaming = False

    def release_session(self) -> None:
        if not self._prepared or self._board is None:
            return

        if self._streaming:
            self.stop_stream()
        self._board.release_session()
        self._prepared = False
        self._board = None

    def close(self) -> None:
        self.stop_stream()
        self.release_session()

    def __enter__(self) -> "MuseCollector":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
