"""Hardware- and artifact-independent Model Inference tests."""

import unittest

import numpy as np

from backend.app.config import EEGInferenceConfig
from backend.app.eeg.window_validator import EXPECTED_SAMPLE_INTERVAL_SECONDS
from backend.app.main import predict_and_log_model_result
from backend.app.model.contracts import (
    CognitivePrediction,
    MODEL_INPUT_CONTRACT,
    MODEL_OUTPUT_CLASSES,
    ModelInputContract,
)
from backend.app.model.exceptions import (
    InvalidModelInput,
    InvalidModelOutput,
    ModelExecutionError,
)
from backend.app.model.inference_service import ModelInferenceService
from backend.app.model.provider import StubModelProvider
from backend.tests.helpers import make_chunk, make_timestamps


def valid_raw_result(state="relaxed_openeye"):
    probabilities_by_state = {
        "relaxed_openeye": {
            "relaxed_openeye": 0.82,
            "concentration": 0.10,
            "relaxed_closeeye": 0.08,
        },
        "concentration": {
            "relaxed_openeye": 0.06,
            "concentration": 0.88,
            "relaxed_closeeye": 0.06,
        },
        "relaxed_closeeye": {
            "relaxed_openeye": 0.08,
            "concentration": 0.08,
            "relaxed_closeeye": 0.84,
        },
    }
    probabilities = probabilities_by_state[state]
    return {
        "state": state,
        "confidence": probabilities[state],
        "probabilities": probabilities,
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
    def test_model_output_classes_are_exactly_canonical(self) -> None:
        self.assertEqual(
            MODEL_OUTPUT_CLASSES,
            (
                "relaxed_openeye",
                "concentration",
                "relaxed_closeeye",
            ),
        )

    def test_valid_window_reaches_stub_provider(self) -> None:
        provider = RecordingProvider()
        service = ModelInferenceService(provider)

        prediction = service.predict(make_chunk(256))

        self.assertEqual(provider.call_count, 1)
        self.assertEqual(provider.received_windows[0].shape, (256, 4))
        self.assertTrue(provider.received_windows[0].flags.writeable)
        self.assertEqual(prediction.state, "relaxed_openeye")

    def test_invalid_timestamp_window_never_calls_provider(self) -> None:
        provider = RecordingProvider()
        service = ModelInferenceService(provider)
        timestamps = make_timestamps(256)
        timestamps[128:] += 0.1

        with self.assertRaises(InvalidModelInput):
            service.predict(make_chunk(256, timestamps=timestamps))

        self.assertEqual(provider.call_count, 0)

    def test_all_canonical_states_become_cognitive_predictions(self) -> None:
        for state in (
            "relaxed_openeye",
            "concentration",
            "relaxed_closeeye",
        ):
            with self.subTest(state=state):
                prediction = CognitivePrediction.from_raw_result(
                    valid_raw_result(state)
                )

                self.assertEqual(prediction.state, state)
                self.assertEqual(
                    prediction.confidence,
                    prediction.probabilities[state],
                )
                self.assertEqual(
                    set(prediction.probabilities),
                    {
                        "relaxed_openeye",
                        "concentration",
                        "relaxed_closeeye",
                    },
                )

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

    def test_legacy_states_are_rejected(self) -> None:
        for legacy_state in ("neutral", "concentrating"):
            with self.subTest(state=legacy_state):
                result = valid_raw_result()
                result["state"] = legacy_state
                provider = RecordingProvider(result=result)

                with self.assertRaisesRegex(
                    InvalidModelOutput,
                    "state must be",
                ):
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

    def test_each_missing_probability_class_is_rejected(self) -> None:
        for missing_state in (
            "relaxed_openeye",
            "concentration",
            "relaxed_closeeye",
        ):
            with self.subTest(missing_state=missing_state):
                result = valid_raw_result()
                del result["probabilities"][missing_state]
                provider = RecordingProvider(result=result)

                with self.assertRaisesRegex(
                    InvalidModelOutput,
                    "missing: {0}".format(missing_state),
                ):
                    ModelInferenceService(provider).predict(make_chunk(256))

    def test_legacy_probability_classes_are_rejected(self) -> None:
        for legacy_state in ("neutral", "concentrating"):
            with self.subTest(state=legacy_state):
                result = valid_raw_result()
                result["probabilities"][legacy_state] = 0.0
                provider = RecordingProvider(result=result)

                with self.assertRaisesRegex(
                    InvalidModelOutput,
                    "unexpected: {0}".format(legacy_state),
                ):
                    ModelInferenceService(provider).predict(make_chunk(256))

    def test_nan_and_infinite_probabilities_are_rejected(self) -> None:
        for invalid_probability in (float("nan"), float("inf")):
            with self.subTest(probability=invalid_probability):
                result = valid_raw_result()
                result["probabilities"][
                    "relaxed_openeye"
                ] = invalid_probability
                provider = RecordingProvider(result=result)

                with self.assertRaisesRegex(InvalidModelOutput, "must be finite"):
                    ModelInferenceService(provider).predict(make_chunk(256))

    def test_probability_sum_far_from_one_is_rejected(self) -> None:
        result = valid_raw_result()
        result["probabilities"] = {
            "relaxed_openeye": 0.7,
            "concentration": 0.2,
            "relaxed_closeeye": 0.2,
        }
        provider = RecordingProvider(result=result)

        with self.assertRaisesRegex(InvalidModelOutput, "must sum to 1"):
            ModelInferenceService(provider).predict(make_chunk(256))

    def test_state_not_matching_highest_probability_is_rejected(self) -> None:
        result = valid_raw_result()
        result["state"] = "relaxed_openeye"
        result["confidence"] = 0.1
        result["probabilities"] = {
            "relaxed_openeye": 0.1,
            "concentration": 0.8,
            "relaxed_closeeye": 0.1,
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

    def test_512_config_reaches_provider_as_512_by_4(self) -> None:
        config = EEGInferenceConfig(
            window_samples=512,
            stride_samples=256,
        )
        provider = RecordingProvider()
        service = ModelInferenceService(
            provider,
            inference_config=config,
        )

        prediction = service.predict(make_chunk(512))

        self.assertEqual(prediction.state, "relaxed_openeye")
        self.assertEqual(provider.received_windows[0].shape, (512, 4))
        self.assertEqual(
            ModelInputContract.from_config(config).raw_shape,
            (512, 4),
        )

    def test_stub_provider_accepts_256_and_512_configs(self) -> None:
        for window_samples in (256, 512):
            with self.subTest(window_samples=window_samples):
                config = EEGInferenceConfig(
                    window_samples=window_samples,
                    stride_samples=window_samples,
                )
                prediction = ModelInferenceService(
                    StubModelProvider(clock=lambda: 100.0),
                    inference_config=config,
                ).predict(make_chunk(window_samples))

                self.assertEqual(prediction.state, "relaxed_openeye")

    def test_stub_provider_cycles_three_states_every_three_seconds(self) -> None:
        current_time = [100.0]
        provider = StubModelProvider(clock=lambda: current_time[0])
        service = ModelInferenceService(provider)

        relaxed_openeye = service.predict(make_chunk(256))
        current_time[0] = 103.0
        concentration = service.predict(make_chunk(256))
        current_time[0] = 106.0
        relaxed_closeeye = service.predict(make_chunk(256))
        current_time[0] = 109.0
        relaxed_openeye_again = service.predict(make_chunk(256))

        self.assertEqual(relaxed_openeye.state, "relaxed_openeye")
        self.assertEqual(relaxed_openeye.confidence, 0.82)
        self.assertEqual(
            set(relaxed_openeye.probabilities),
            {"relaxed_openeye", "concentration", "relaxed_closeeye"},
        )
        self.assertEqual(concentration.state, "concentration")
        self.assertEqual(concentration.confidence, 0.88)
        self.assertEqual(relaxed_closeeye.state, "relaxed_closeeye")
        self.assertEqual(relaxed_closeeye.confidence, 0.84)
        self.assertEqual(relaxed_openeye_again.state, "relaxed_openeye")

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
