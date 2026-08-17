"""Model provider abstraction and the single Model Team integration point."""

import time
from typing import Any, Callable, Mapping, Protocol

import numpy as np


RawModelResult = Mapping[str, Any]
ModelPredictFunction = Callable[[np.ndarray], RawModelResult]


class ModelProvider(Protocol):
    display_name: str

    def predict(self, raw_window: np.ndarray) -> RawModelResult:
        """Run the provider-owned pipeline on a validated ``(256, 4)`` window."""


class StubModelProvider:
    """Time-based binary demo provider; it is not a trained model."""

    display_name = "STUB MODEL"
    state_duration_seconds = 3.0

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._started_at = clock()

    def predict(self, raw_window: np.ndarray) -> RawModelResult:
        elapsed = max(0.0, self._clock() - self._started_at)
        is_concentrating = (
            int(elapsed / self.state_duration_seconds) % 2 == 1
        )
        if is_concentrating:
            return {
                "state": "concentrating",
                "confidence": 0.90,
                "probabilities": {
                    "neutral": 0.10,
                    "concentrating": 0.90,
                },
            }
        return {
            "state": "neutral",
            "confidence": 0.82,
            "probabilities": {
                "neutral": 0.82,
                "concentrating": 0.18,
            },
        }


class ModelTeamFunctionProvider:
    """Adapts the Model Team's future ``predict(raw_window)`` function."""

    def __init__(
        self,
        predict_function: ModelPredictFunction,
        display_name: str = "PRODUCTION MODEL",
    ) -> None:
        self._predict_function = predict_function
        self.display_name = display_name

    def predict(self, raw_window: np.ndarray) -> RawModelResult:
        return self._predict_function(raw_window)


def create_runtime_model_provider() -> ModelProvider:
    """Composition root to replace when the Model Team package arrives."""

    return StubModelProvider()
