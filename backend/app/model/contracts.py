"""Formal raw-window input and cognitive prediction output contracts."""

from dataclasses import dataclass
import math
from numbers import Real
from types import MappingProxyType
from typing import Any, Literal, Mapping, Tuple

import numpy as np

from backend.app.config import (
    DEFAULT_EEG_INFERENCE_CONFIG,
    EEGInferenceConfig,
)
from backend.app.eeg.contracts import (
    EEGChunk,
    MUSE_EEG_CHANNEL_ORDER,
)


CognitiveState = Literal[
    "relaxed_openeye",
    "concentration",
    "relaxed_closeeye",
]
MODEL_OUTPUT_CLASSES: Tuple[str, ...] = (
    "relaxed_openeye",
    "concentration",
    "relaxed_closeeye",
)
PROBABILITY_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ModelInputContract:
    sampling_rate_hz: int
    window_size_sec: float
    channel_order: Tuple[str, ...]
    raw_shape: Tuple[int, int]

    @classmethod
    def from_config(
        cls,
        config: EEGInferenceConfig,
    ) -> "ModelInputContract":
        return cls(
            sampling_rate_hz=config.sampling_rate_hz,
            window_size_sec=config.window_size_sec,
            channel_order=MUSE_EEG_CHANNEL_ORDER,
            raw_shape=(
                config.window_samples,
                len(MUSE_EEG_CHANNEL_ORDER),
            ),
        )

    def validate_raw_window(self, raw_window: np.ndarray) -> None:
        if not isinstance(raw_window, np.ndarray):
            raise ValueError("raw_window must be a numpy.ndarray")
        if raw_window.shape != self.raw_shape:
            raise ValueError(
                "raw_window must have shape {0}, received {1}".format(
                    self.raw_shape,
                    raw_window.shape,
                )
            )
        if not np.all(np.isfinite(raw_window)):
            raise ValueError("raw_window must contain only finite values")

    def validate_window(self, window: EEGChunk) -> None:
        if window.sampling_rate_hz != self.sampling_rate_hz:
            raise ValueError("window sampling rate does not match model contract")
        if window.channel_order != self.channel_order:
            raise ValueError("window channel order does not match model contract")
        if window.sample_count != self.raw_shape[0]:
            raise ValueError("window sample count does not match model contract")
        self.validate_raw_window(window.samples)


MODEL_INPUT_CONTRACT = ModelInputContract.from_config(
    DEFAULT_EEG_INFERENCE_CONFIG
)


@dataclass(frozen=True)
class CognitivePrediction:
    state: CognitiveState
    confidence: float
    probabilities: Mapping[str, float]

    def __post_init__(self) -> None:
        if self.state not in MODEL_OUTPUT_CLASSES:
            raise ValueError("state must be one of {0}".format(MODEL_OUTPUT_CLASSES))

        confidence = _validate_probability_value(
            "confidence",
            self.confidence,
        )
        if not isinstance(self.probabilities, Mapping):
            raise ValueError("probabilities must be a mapping")

        received_classes = set(self.probabilities.keys())
        required_classes = set(MODEL_OUTPUT_CLASSES)
        if received_classes != required_classes:
            missing = sorted(required_classes - received_classes)
            unexpected = sorted(received_classes - required_classes)
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise ValueError(
                "probabilities classes do not match contract ({0})".format(
                    "; ".join(details)
                )
            )

        probabilities = {
            state: _validate_probability_value(
                "probabilities[{0}]".format(state),
                self.probabilities[state],
            )
            for state in MODEL_OUTPUT_CLASSES
        }
        probability_sum = sum(probabilities.values())
        if not math.isclose(
            probability_sum,
            1.0,
            rel_tol=PROBABILITY_TOLERANCE,
            abs_tol=PROBABILITY_TOLERANCE,
        ):
            raise ValueError(
                "probabilities must sum to 1, received {0:.12f}".format(
                    probability_sum
                )
            )

        state_probability = probabilities[self.state]
        highest_probability = max(probabilities.values())
        if not math.isclose(
            state_probability,
            highest_probability,
            rel_tol=PROBABILITY_TOLERANCE,
            abs_tol=PROBABILITY_TOLERANCE,
        ):
            raise ValueError("state must correspond to the highest probability")
        if not math.isclose(
            confidence,
            state_probability,
            rel_tol=PROBABILITY_TOLERANCE,
            abs_tol=PROBABILITY_TOLERANCE,
        ):
            raise ValueError("confidence must equal probabilities[state]")

        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(
            self,
            "probabilities",
            MappingProxyType(probabilities),
        )

    @classmethod
    def from_raw_result(cls, raw_result: Mapping[str, Any]) -> "CognitivePrediction":
        if not isinstance(raw_result, Mapping):
            raise ValueError("model result must be a mapping")
        try:
            state = raw_result["state"]
            confidence = raw_result["confidence"]
            probabilities = raw_result["probabilities"]
        except KeyError as error:
            raise ValueError(
                "model result is missing field: {0}".format(error.args[0])
            ) from error

        return cls(
            state=state,
            confidence=confidence,
            probabilities=probabilities,
        )


def _validate_probability_value(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("{0} must be a finite number".format(name))
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError("{0} must be finite".format(name))
    if not 0.0 <= numeric_value <= 1.0:
        raise ValueError("{0} must be between 0 and 1".format(name))
    return numeric_value
