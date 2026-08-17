"""Hardware- and artifact-independent Model Inference tests."""

import unittest

import numpy as np

from backend.app.eeg.window_validator import EXPECTED_SAMPLE_INTERVAL_SECONDS
from backend.app.main import predict_and_log_model_result
from backend.app.model.contracts import (
    CognitivePrediction,
    MODEL_INPUT_CONTRACT,
)
from backend.app.model.exceptions import (
    InvalidModelInput,
    InvalidModelOutput,
    ModelExecutionError,
)
from backend.app.model.inference_service import ModelInferenceService
from backend.app.model.provider import StubModelProvider
from backend.tests.helpers import make_chunk, make_timestamps


def valid_raw_result():
    return {
        "state": "neutral",
        "confidence": 0.82,
        "probabilities": {
            "neutral": 0.82,
            "concentrating": 0.18,
        },
    }


class RecordingProvider:
    display_name = "TEST MODEL"

    def __init__(self, result=None, error=None) -> None:
        self.result = valid_raw_result() if result is None else result
        self.error = error
        self.call_count = 0
        self.received_windows = []

    def predict(self, raw_window):
        self.call_count += 1
        self.received_windows.append(raw_window)
        if self.error is not None:
            raise self.error
        return self.result


class FailsOnceProvider(RecordingProvider):
    def predict(self, raw_window):
        self.call_count += 1
        self.received_windows.append(raw_window)
        if self.call_count == 1:
            raise RuntimeError("temporary provider failure")
        return valid_raw_result()


class ModelInferenceTests(unittest.TestCase):
    def test_valid_window_reaches_stub_provider(self) -> None:
        provider = RecordingProvider()
        service = ModelInferenceService(provider)

        prediction = service.predict(make_chunk(256))

        self.assertEqual(provider.call_count, 1)
        self.assertEqual(provider.received_windows[0].shape, (256, 4))
        self.assertTrue(provider.received_windows[0].flags.writeable)
        self.assertEqual(prediction.state, "neutral")

    def test_invalid_timestamp_window_never_calls_provider(self) -> None:
        provider = RecordingProvider()
        service = ModelInferenceService(provider)
        timestamps = make_timestamps(256)
        timestamps[128:] += 0.1

        with self.assertRaises(InvalidModelInput):
            service.predict(make_chunk(256, timestamps=timestamps))

        self.assertEqual(provider.call_count, 0)

    def test_normal_raw_result_becomes_cognitive_prediction(self) -> None:
        prediction = CognitivePrediction.from_raw_result(valid_raw_result())

        self.assertEqual(prediction.state, "neutral")
        self.assertEqual(prediction.confidence, 0.82)
        self.assertEqual(prediction.probabilities["concentrating"], 0.18)

    def test_illegal_state_is_rejected(self) -> None:
        result = valid_raw_result()
        result["state"] = "focused"
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(InvalidModelOutput, "state must be"):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_relaxed_state_is_rejected(self) -> None:
        result = valid_raw_result()
        result["state"] = "relaxed"
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(InvalidModelOutput, "state must be"):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_confidence_outside_unit_interval_is_rejected(self) -> None:
        for confidence in (-0.01, 1.01):
            with self.subTest(confidence=confidence):
                result = valid_raw_result()
                result["confidence"] = confidence
                provider = RecordingProvider(result=result)

                with self.assertRaisesRegex(
                    InvalidModelOutput,
                    "confidence must be between 0 and 1",
                ):
                    ModelInferenceService(provider).predict(make_chunk(256))

    def test_missing_probability_class_is_rejected(self) -> None:
        result = valid_raw_result()
        del result["probabilities"]["neutral"]
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(InvalidModelOutput, "missing: neutral"):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_relaxed_probability_class_is_rejected(self) -> None:
        result = valid_raw_result()
        result["probabilities"]["relaxed"] = 0.0
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(InvalidModelOutput, "unexpected: relaxed"):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_nan_and_infinite_probabilities_are_rejected(self) -> None:
        for invalid_probability in (float("nan"), float("inf")):
            with self.subTest(probability=invalid_probability):
                result = valid_raw_result()
                result["probabilities"]["neutral"] = invalid_probability
                provider = RecordingProvider(result=result)

                with self.assertRaisesRegex(InvalidModelOutput, "must be finite"):
                    ModelInferenceService(provider).predict(make_chunk(256))

    def test_probability_sum_far_from_one_is_rejected(self) -> None:
        result = valid_raw_result()
        result["probabilities"] = {
            "neutral": 0.7,
            "concentrating": 0.4,
        }
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(InvalidModelOutput, "must sum to 1"):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_state_not_matching_highest_probability_is_rejected(self) -> None:
        result = valid_raw_result()
        result["state"] = "neutral"
        result["confidence"] = 0.1
        result["probabilities"] = {
            "neutral": 0.1,
            "concentrating": 0.9,
        }
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(
            InvalidModelOutput,
            "state must correspond to the highest probability",
        ):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_confidence_not_matching_state_probability_is_rejected(self) -> None:
        result = valid_raw_result()
        result["confidence"] = 0.6
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(
            InvalidModelOutput,
            "confidence must equal probabilities",
        ):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_provider_exception_is_isolated_and_next_prediction_can_run(self) -> None:
        provider = FailsOnceProvider()
        service = ModelInferenceService(provider)
        log_lines = []

        first = predict_and_log_model_result(
            service,
            make_chunk(256),
            log_lines.append,
        )
        second = predict_and_log_model_result(
            service,
            make_chunk(256, start_index=256),
            log_lines.append,
        )

        self.assertIsNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(provider.call_count, 2)
        self.assertIn("MODEL EXECUTION ERROR", log_lines)
        self.assertIn("MODEL PREDICTION", log_lines)

    def test_wrong_input_shape_is_rejected_before_provider(self) -> None:
        provider = RecordingProvider()
        service = ModelInferenceService(provider)

        with self.assertRaisesRegex(InvalidModelInput, "sample count"):
            service.predict(make_chunk(255))

        self.assertEqual(provider.call_count, 0)

    def test_raw_input_contract_rejects_non_256_by_4_array(self) -> None:
        with self.assertRaisesRegex(ValueError, "shape"):
            MODEL_INPUT_CONTRACT.validate_raw_window(np.zeros((256, 3)))

    def test_stub_provider_alternates_binary_demo_every_three_seconds(self) -> None:
        current_time = [100.0]
        provider = StubModelProvider(clock=lambda: current_time[0])
        service = ModelInferenceService(provider)

        neutral = service.predict(make_chunk(256))
        current_time[0] = 103.0
        concentrating = service.predict(make_chunk(256))
        current_time[0] = 106.0
        neutral_again = service.predict(make_chunk(256))

        self.assertEqual(neutral.state, "neutral")
        self.assertEqual(neutral.confidence, 0.82)
        self.assertEqual(
            set(neutral.probabilities),
            {"neutral", "concentrating"},
        )
        self.assertEqual(concentrating.state, "concentrating")
        self.assertEqual(concentrating.confidence, 0.90)
        self.assertEqual(neutral_again.state, "neutral")

    def test_provider_exception_is_wrapped_as_model_execution_error(self) -> None:
        provider = RecordingProvider(error=RuntimeError("model failed"))

        with self.assertRaisesRegex(ModelExecutionError, "model failed"):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_gap_below_two_samples_still_obeys_existing_validator(self) -> None:
        provider = RecordingProvider()
        timestamps = make_timestamps(256)
        adjustment = 0.006133 - EXPECTED_SAMPLE_INTERVAL_SECONDS
        timestamps[128:] += adjustment

        with self.assertRaises(InvalidModelInput):
            ModelInferenceService(provider).predict(
                make_chunk(256, timestamps=timestamps)
            )

        self.assertEqual(provider.call_count, 0)


if __name__ == "__main__":
    unittest.main()
