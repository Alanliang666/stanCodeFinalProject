"""Model provider abstraction and the single Model Team integration point."""

from importlib import import_module
import os
import time
from types import ModuleType
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence, Tuple

import numpy as np

from backend.app.config import DEFAULT_EEG_WINDOW_SAMPLES
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
MODEL_TEAM_SUPPORTED_WINDOWS_NAME = "SUPPORTED_WINDOW_SAMPLES"
MODEL_TEAM_SINGLE_WINDOW_NAME = "WINDOW_SIZE_SAMPLES"
MODEL_TEAM_EXPECTED_CALLABLE = (
    MODEL_TEAM_MODULE_PATH + "." + MODEL_TEAM_CALLABLE_NAME
)


class ModelProvider(Protocol):
    display_name: str
    supported_window_samples: Optional[Tuple[int, ...]]

    def predict(self, raw_window: np.ndarray) -> RawModelResult:
        """Run the provider-owned pipeline on a validated ``(N, 4)`` window."""


class StubModelProvider:
    """Time-based three-state demo provider; it is not a trained model."""

    display_name = "STUB MODEL"
    supported_window_samples: Optional[Tuple[int, ...]] = None
    state_duration_seconds = 3.0

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._started_at = clock()

    def predict(self, raw_window: np.ndarray) -> RawModelResult:
        elapsed = max(0.0, self._clock() - self._started_at)
        state_index = int(elapsed / self.state_duration_seconds) % 3
        if state_index == 1:
            return {
                "state": "concentration",
                "confidence": 0.88,
                "probabilities": {
                    "relaxed_openeye": 0.06,
                    "concentration": 0.88,
                    "relaxed_closeeye": 0.06,
                },
            }
        if state_index == 2:
            return {
                "state": "relaxed_closeeye",
                "confidence": 0.84,
                "probabilities": {
                    "relaxed_openeye": 0.08,
                    "concentration": 0.08,
                    "relaxed_closeeye": 0.84,
                },
            }
        return {
            "state": "relaxed_openeye",
            "confidence": 0.82,
            "probabilities": {
                "relaxed_openeye": 0.82,
                "concentration": 0.10,
                "relaxed_closeeye": 0.08,
            },
        }


class ModelTeamFunctionProvider:
    """Adapts the Model Team's ``predict_mental_state(raw_window)`` function."""

    def __init__(
        self,
        predict_function: ModelPredictFunction,
        display_name: str = "MODEL TEAM - predict_mental_state",
        supported_window_samples: Optional[Sequence[int]] = None,
    ) -> None:
        self._predict_function = predict_function
        self.display_name = display_name
        declared_windows = (
            supported_window_samples
            if supported_window_samples is not None
            else getattr(
                predict_function,
                MODEL_TEAM_SUPPORTED_WINDOWS_NAME,
                None,
            )
        )
        self.supported_window_samples = _normalize_supported_windows(
            declared_windows
        )

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
    supported_windows = _read_module_supported_windows(module)
    if supported_windows is None:
        return predict_function

    def predict_with_capability(raw_window: np.ndarray) -> RawModelResult:
        return predict_function(raw_window)

    setattr(
        predict_with_capability,
        MODEL_TEAM_SUPPORTED_WINDOWS_NAME,
        supported_windows,
    )
    return predict_with_capability


def _read_module_supported_windows(
    module: ModuleType,
) -> Optional[Tuple[int, ...]]:
    declared_windows = getattr(
        module,
        MODEL_TEAM_SUPPORTED_WINDOWS_NAME,
        None,
    )
    if declared_windows is None:
        single_window = getattr(module, MODEL_TEAM_SINGLE_WINDOW_NAME, None)
        if single_window is None:
            return None
        declared_windows = (single_window,)
    try:
        return _normalize_supported_windows(declared_windows)
    except ValueError as error:
        raise _model_team_load_error(str(error)) from error


def _normalize_supported_windows(
    declared_windows: Optional[Sequence[int]],
) -> Optional[Tuple[int, ...]]:
    if declared_windows is None:
        return None
    if isinstance(declared_windows, (str, bytes)):
        raise ValueError("model window capability must be a sequence of integers")
    try:
        normalized = tuple(declared_windows)
    except TypeError as error:
        raise ValueError(
            "model window capability must be a sequence of integers"
        ) from error
    if not normalized:
        raise ValueError("model window capability must not be empty")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in normalized
    ):
        raise ValueError(
            "model window capability must contain positive integer samples"
        )
    return tuple(dict.fromkeys(normalized))


def validate_model_provider_window(
    provider: ModelProvider,
    configured_window_samples: int,
) -> None:
    supported_windows = getattr(provider, "supported_window_samples", None)
    if (
        supported_windows is not None
        and configured_window_samples not in supported_windows
    ):
        raise ModelProviderLoadError(
            "MODEL INPUT CONTRACT MISMATCH\n"
            "Configured EEG window: {0} samples\n"
            "Model supports: {1}\n"
            "Refusing to start due to incompatible model input contract.".format(
                configured_window_samples,
                ", ".join(str(value) for value in supported_windows),
            )
        )


def create_runtime_model_provider(
    provider_mode: Optional[str] = None,
    model_function_loader: ModelFunctionLoader = (
        load_model_team_predict_function
    ),
    configured_window_samples: int = DEFAULT_EEG_WINDOW_SAMPLES,
) -> ModelProvider:
    """Create the configured provider without silently changing modes."""

    configured_mode = (
        provider_mode
        if provider_mode is not None
        else os.getenv(MODEL_PROVIDER_ENVIRONMENT_VARIABLE, STUB_PROVIDER_MODE)
    )
    normalized_mode = configured_mode.strip().lower()

    if normalized_mode == STUB_PROVIDER_MODE:
        provider = StubModelProvider()
        validate_model_provider_window(provider, configured_window_samples)
        return provider
    if normalized_mode == MODEL_TEAM_PROVIDER_MODE:
        predict_function = model_function_loader()
        if not callable(predict_function):
            raise _model_team_load_error(
                "Configured Model Team loader did not return a callable."
            )
        provider = ModelTeamFunctionProvider(predict_function)
        validate_model_provider_window(provider, configured_window_samples)
        return provider

    raise ModelProviderLoadError(
        "Unsupported MODEL_PROVIDER value: {0!r}. Expected 'stub' or "
        "'model_team'.".format(configured_mode)
    )
