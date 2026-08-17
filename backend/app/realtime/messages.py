"""Serialization boundary from internal contracts to transport messages."""

import time
from typing import Optional

from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
    SAMPLING_RATE_HZ,
)
from backend.app.model.contracts import (
    CognitivePrediction,
    MODEL_OUTPUT_CLASSES,
)
from backend.app.realtime.contracts import (
    CognitivePredictionMessage,
    DeviceStatusMessage,
    EEGChunkMessage,
)


def create_device_status_message(
    connected: bool,
    device: str = "Muse 2",
) -> DeviceStatusMessage:
    return {
        "type": "device_status",
        "data": {
            "connected": bool(connected),
            "device": device,
            "sampling_rate_hz": SAMPLING_RATE_HZ,
            "channel_order": list(MUSE_EEG_CHANNEL_ORDER),
        },
    }


def create_eeg_chunk_message(chunk: EEGChunk) -> EEGChunkMessage:
    """Convert NumPy arrays only at the JSON transport boundary."""

    return {
        "type": "eeg_chunk",
        "data": {
            "sampling_rate_hz": chunk.sampling_rate_hz,
            "channel_order": list(chunk.channel_order),
            "timestamps": chunk.timestamps.tolist(),
            "samples": chunk.samples.tolist(),
        },
    }


def create_cognitive_prediction_message(
    prediction: CognitivePrediction,
    timestamp: Optional[float] = None,
) -> CognitivePredictionMessage:
    if not isinstance(prediction, CognitivePrediction):
        raise TypeError("prediction must be a validated CognitivePrediction")

    return {
        "type": "cognitive_prediction",
        "data": {
            "timestamp": time.time() if timestamp is None else float(timestamp),
            "state": prediction.state,
            "confidence": prediction.confidence,
            "probabilities": {
                state: prediction.probabilities[state]
                for state in MODEL_OUTPUT_CLASSES
            },
        },
    }
