"""Small exception boundary for model inference failures."""


class ModelInferenceError(RuntimeError):
    """Base exception that the acquisition runtime can safely isolate."""


class InvalidModelInput(ModelInferenceError):
    """Raised before a provider sees an invalid raw EEG window."""


class ModelExecutionError(ModelInferenceError):
    """Raised when the configured provider fails during execution."""


class InvalidModelOutput(ModelInferenceError):
    """Raised when a raw provider result violates the output contract."""
