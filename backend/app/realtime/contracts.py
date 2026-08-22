"""JSON-compatible realtime transport contracts."""

from typing import Dict, List, Literal, TypedDict, Union

from backend.app.model.contracts import CognitiveState


class DeviceStatusData(TypedDict):
    connected: bool
    device: str
    sampling_rate_hz: int
    channel_order: List[str]


class DeviceStatusMessage(TypedDict):
    type: Literal["device_status"]
    data: DeviceStatusData


class EEGChunkData(TypedDict):
    sampling_rate_hz: int
    channel_order: List[str]
    timestamps: List[float]
    samples: List[List[float]]


class EEGChunkMessage(TypedDict):
    type: Literal["eeg_chunk"]
    data: EEGChunkData


class CognitivePredictionData(TypedDict):
    timestamp: float
    state: CognitiveState
    confidence: float
    probabilities: Dict[CognitiveState, float]


class CognitivePredictionMessage(TypedDict):
    type: Literal["cognitive_prediction"]
    data: CognitivePredictionData


RealtimeMessage = Union[
    DeviceStatusMessage,
    EEGChunkMessage,
    CognitivePredictionMessage,
]

REALTIME_MESSAGE_PRIORITY = (
    "device_status",
    "cognitive_prediction",
    "eeg_chunk",
)
