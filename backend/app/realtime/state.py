"""Thread-safe current-state snapshot used by the health endpoint."""

from threading import Lock
from typing import Dict, Union

from backend.app.config import (
    DEFAULT_EEG_INFERENCE_CONFIG,
    EEGInferenceConfig,
)


HealthValue = Union[str, bool, int, float]


class LocalAgentState:
    def __init__(
        self,
        model_provider: str,
        inference_config: EEGInferenceConfig = DEFAULT_EEG_INFERENCE_CONFIG,
    ) -> None:
        self._lock = Lock()
        self._device_connected = False
        self._model_provider = model_provider
        self._inference_config = inference_config

    def set_device_connected(self, connected: bool) -> None:
        with self._lock:
            self._device_connected = bool(connected)

    def health_snapshot(self) -> Dict[str, HealthValue]:
        with self._lock:
            return {
                "status": "ok",
                "device_connected": self._device_connected,
                "model_provider": self._model_provider,
                "sampling_rate_hz": self._inference_config.sampling_rate_hz,
                "inference_window_samples": (
                    self._inference_config.window_samples
                ),
                "inference_window_sec": (
                    self._inference_config.window_size_sec
                ),
                "inference_stride_samples": (
                    self._inference_config.stride_samples
                ),
                "inference_stride_sec": self._inference_config.stride_sec,
            }
