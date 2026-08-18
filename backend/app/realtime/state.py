"""Thread-safe current-state snapshot used by the health endpoint."""

from threading import Lock
from typing import Dict, Union


HealthValue = Union[str, bool]


class LocalAgentState:
    def __init__(self, model_provider: str) -> None:
        self._lock = Lock()
        self._device_connected = False
        self._model_provider = model_provider

    def set_device_connected(self, connected: bool) -> None:
        with self._lock:
            self._device_connected = bool(connected)

    def health_snapshot(self) -> Dict[str, HealthValue]:
        with self._lock:
            return {
                "status": "ok",
                "device_connected": self._device_connected,
                "model_provider": self._model_provider,
            }
