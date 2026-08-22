"""Centralized runtime configuration for EEG inference aggregation."""

from dataclasses import dataclass
import os
from typing import Mapping, Optional

from backend.app.eeg.contracts import SAMPLING_RATE_HZ


EEG_WINDOW_SAMPLES_ENVIRONMENT_VARIABLE = "EEG_WINDOW_SAMPLES"
EEG_STRIDE_SAMPLES_ENVIRONMENT_VARIABLE = "EEG_STRIDE_SAMPLES"
DEFAULT_EEG_WINDOW_SAMPLES = 256
DEFAULT_EEG_STRIDE_SAMPLES = 256


class EEGInferenceConfigError(ValueError):
    """Raised when the EEG inference aggregation configuration is invalid."""


@dataclass(frozen=True)
class EEGInferenceConfig:
    window_samples: int = DEFAULT_EEG_WINDOW_SAMPLES
    stride_samples: int = DEFAULT_EEG_STRIDE_SAMPLES

    def __post_init__(self) -> None:
        if isinstance(self.window_samples, bool) or not isinstance(
            self.window_samples,
            int,
        ):
            raise EEGInferenceConfigError("window_samples must be an integer")
        if isinstance(self.stride_samples, bool) or not isinstance(
            self.stride_samples,
            int,
        ):
            raise EEGInferenceConfigError("stride_samples must be an integer")
        if self.window_samples <= 0:
            raise EEGInferenceConfigError("window_samples must be positive")
        if self.stride_samples <= 0:
            raise EEGInferenceConfigError("stride_samples must be positive")
        if self.stride_samples > self.window_samples:
            raise EEGInferenceConfigError(
                "stride_samples must not exceed window_samples"
            )

    @property
    def sampling_rate_hz(self) -> int:
        return SAMPLING_RATE_HZ

    @property
    def window_size_sec(self) -> float:
        return self.window_samples / self.sampling_rate_hz

    @property
    def stride_sec(self) -> float:
        return self.stride_samples / self.sampling_rate_hz

    @classmethod
    def from_environment(
        cls,
        environment: Optional[Mapping[str, str]] = None,
    ) -> "EEGInferenceConfig":
        active_environment = os.environ if environment is None else environment
        return cls(
            window_samples=_parse_integer_environment_variable(
                active_environment,
                EEG_WINDOW_SAMPLES_ENVIRONMENT_VARIABLE,
                DEFAULT_EEG_WINDOW_SAMPLES,
            ),
            stride_samples=_parse_integer_environment_variable(
                active_environment,
                EEG_STRIDE_SAMPLES_ENVIRONMENT_VARIABLE,
                DEFAULT_EEG_STRIDE_SAMPLES,
            ),
        )


DEFAULT_EEG_INFERENCE_CONFIG = EEGInferenceConfig()


def load_eeg_inference_config(
    environment: Optional[Mapping[str, str]] = None,
) -> EEGInferenceConfig:
    """Parse environment variables once at the runtime composition root."""

    return EEGInferenceConfig.from_environment(environment)


def _parse_integer_environment_variable(
    environment: Mapping[str, str],
    name: str,
    default: int,
) -> int:
    raw_value = environment.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except (TypeError, ValueError) as error:
        raise EEGInferenceConfigError(
            "{0} must be an integer, received {1!r}".format(name, raw_value)
        ) from error
