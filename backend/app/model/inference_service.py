"""Validated raw EEG to validated cognitive prediction orchestration."""

from typing import Optional

import numpy as np

from backend.app.eeg.contracts import EEGChunk
from backend.app.eeg.window_validator import EEGWindowValidator
from backend.app.model.contracts import (
    CognitivePrediction,
    MODEL_INPUT_CONTRACT,
)
from backend.app.model.exceptions import (
    InvalidModelInput,
    InvalidModelOutput,
    ModelExecutionError,
)
from backend.app.model.provider import ModelProvider


class ModelInferenceService:
    """Keeps validation and provider execution behind one stable boundary."""

    def __init__(
        self,
        provider: ModelProvider,
        window_validator: Optional[EEGWindowValidator] = None,
    ) -> None:
        self.provider = provider
        self._window_validator = window_validator or EEGWindowValidator()

    def predict(self, window: EEGChunk) -> CognitivePrediction:
        validation = self._window_validator.validate(window)
        if not validation.valid:
            raise InvalidModelInput(
                "EEG window validation failed: {0}".format(validation.reason)
            )

        try:
            MODEL_INPUT_CONTRACT.validate_window(window)
        except (TypeError, ValueError) as error:
            raise InvalidModelInput(str(error)) from error

        # Give provider-owned preprocessing a writable copy and keep the source
        # EEGChunk immutable for future parallel consumers.
        raw_window = np.array(window.samples, dtype=np.float64, copy=True)
        try:
            raw_result = self.provider.predict(raw_window)
        except Exception as error:
            raise ModelExecutionError(str(error)) from error

        try:
            return CognitivePrediction.from_raw_result(raw_result)
        except (TypeError, ValueError) as error:
            raise InvalidModelOutput(str(error)) from error
