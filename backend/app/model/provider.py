"""Model provider abstraction and the single Model Team integration point."""

from importlib import import_module
import os
import time
from types import ModuleType
from typing import Any, Callable, Mapping, Optional, Protocol

import numpy as np

from backend.app.model.exceptions import ModelProviderLoadError


RawModelResult = Mapping[str, Any]
ModelPredictFunction = Callable[[np.ndarray], RawModelResult]
ModelFunctionLoader = Callable[[], ModelPredictFunction]

MODEL_PROVIDER_ENVIRONMENT_VARIABLE = "MODEL_PROVIDER"
STUB_PROVIDER_MODE = "stub"
MODEL_TEAM_PROVIDER_MODE = "model_team"
MODEL_TEAM_MODULE_PATH = "backend.app.model.inference"
MODEL_TEAM_RELATIVE_MODULE = ".inference"
MODEL_TEAM_CALLABLE_NAME = "predict_mental_state"
MODEL_TEAM_EXPECTED_CALLABLE = (
    MODEL_TEAM_MODULE_PATH + "." + MODEL_TEAM_CALLABLE_NAME
)


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
    """Adapts the Model Team's ``predict_mental_state(raw_window)`` function."""

    def __init__(
        self,
        predict_function: ModelPredictFunction,
        display_name: str = "MODEL TEAM - predict_mental_state",
    ) -> None:
        self._predict_function = predict_function
        self.display_name = display_name

    def predict(self, raw_window: np.ndarray) -> RawModelResult:
        return self._predict_function(raw_window)


def _model_team_load_error(reason: str) -> ModelProviderLoadError:
    return ModelProviderLoadError(
        "REAL MODEL LOAD FAILED\n"
        "{0}\n"
        "Expected callable:\n"
        "{1}".format(reason, MODEL_TEAM_EXPECTED_CALLABLE)
    )


def _import_model_team_module() -> ModuleType:
    try:
        return import_module(MODEL_TEAM_RELATIVE_MODULE, package=__package__)
    except Exception as error:
        raise _model_team_load_error(
            "Model Team inference package is not installed."
        ) from error


def load_model_team_predict_function() -> ModelPredictFunction:
    """Load the Model Team callable once during provider construction."""

    module = _import_model_team_module()
    predict_function = getattr(module, MODEL_TEAM_CALLABLE_NAME, None)
    if not callable(predict_function):
        raise _model_team_load_error(
            "Model Team inference package does not expose the required callable."
        )
    return predict_function


def create_runtime_model_provider(
    provider_mode: Optional[str] = None,
    model_function_loader: ModelFunctionLoader = (
        load_model_team_predict_function
    ),
) -> ModelProvider:
    """Create the configured provider without silently changing modes."""

    configured_mode = (
        provider_mode
        if provider_mode is not None
        else os.getenv(MODEL_PROVIDER_ENVIRONMENT_VARIABLE, STUB_PROVIDER_MODE)
    )
    normalized_mode = configured_mode.strip().lower()

    if normalized_mode == STUB_PROVIDER_MODE:
        return StubModelProvider()
    if normalized_mode == MODEL_TEAM_PROVIDER_MODE:
        predict_function = model_function_loader()
        if not callable(predict_function):
            raise _model_team_load_error(
                "Configured Model Team loader did not return a callable."
            )
        return ModelTeamFunctionProvider(predict_function)

    raise ModelProviderLoadError(
        "Unsupported MODEL_PROVIDER value: {0!r}. Expected 'stub' or "
        "'model_team'.".format(configured_mode)
    )
