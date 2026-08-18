"""Tests for runtime provider selection and the Model Team boundary."""

import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from backend.app.model.exceptions import (
    InvalidModelOutput,
    ModelExecutionError,
    ModelProviderLoadError,
)
from backend.app.model.inference_service import ModelInferenceService
from backend.app.model.provider import (
    MODEL_TEAM_EXPECTED_CALLABLE,
    ModelTeamFunctionProvider,
    StubModelProvider,
    create_runtime_model_provider,
    load_model_team_predict_function,
)
from backend.tests.helpers import make_chunk


def concentrating_result():
    return {
        "state": "concentrating",
        "confidence": 0.9,
        "probabilities": {
            "neutral": 0.1,
            "concentrating": 0.9,
        },
    }


class ModelProviderTests(unittest.TestCase):
    def test_stub_mode_returns_stub_provider(self) -> None:
        provider = create_runtime_model_provider("stub")

        self.assertIsInstance(provider, StubModelProvider)
        self.assertEqual(provider.display_name, "STUB MODEL")

    def test_environment_selects_stub_provider(self) -> None:
        with patch.dict(os.environ, {"MODEL_PROVIDER": "stub"}):
            provider = create_runtime_model_provider()

        self.assertIsInstance(provider, StubModelProvider)

    def test_model_team_mode_loads_function_once(self) -> None:
        load_count = 0

        def fake_predict(raw_window):
            return concentrating_result()

        def fake_loader():
            nonlocal load_count
            load_count += 1
            return fake_predict

        provider = create_runtime_model_provider(
            "model_team",
            model_function_loader=fake_loader,
        )
        service = ModelInferenceService(provider)
        first = service.predict(make_chunk(256))
        second = service.predict(make_chunk(256, start_index=256))

        self.assertIsInstance(provider, ModelTeamFunctionProvider)
        self.assertEqual(
            provider.display_name,
            "MODEL TEAM - predict_mental_state",
        )
        self.assertEqual(load_count, 1)
        self.assertEqual(first.state, "concentrating")
        self.assertEqual(second.state, "concentrating")

    def test_environment_selects_model_team_provider(self) -> None:
        with patch.dict(os.environ, {"MODEL_PROVIDER": "model_team"}):
            provider = create_runtime_model_provider(
                model_function_loader=lambda: concentrating_result_function,
            )

        self.assertIsInstance(provider, ModelTeamFunctionProvider)

    def test_model_function_receives_writable_copy_and_source_is_unchanged(
        self,
    ) -> None:
        window = make_chunk(256)
        original_samples = window.samples.copy()
        received = []

        def fake_predict(raw_window):
            received.append(raw_window)
            self.assertEqual(raw_window.shape, (256, 4))
            self.assertTrue(raw_window.flags.writeable)
            raw_window[0, 0] = 999.0
            return concentrating_result()

        prediction = ModelInferenceService(
            ModelTeamFunctionProvider(fake_predict)
        ).predict(window)

        self.assertEqual(prediction.state, "concentrating")
        self.assertEqual(len(received), 1)
        np.testing.assert_array_equal(window.samples, original_samples)

    def test_model_team_output_still_uses_cognitive_prediction_validation(
        self,
    ) -> None:
        def malformed_predict(raw_window):
            return {
                "state": "relaxed",
                "confidence": 0.6,
                "probabilities": {
                    "neutral": 0.4,
                    "concentrating": 0.5,
                    "relaxed": 0.1,
                },
            }

        service = ModelInferenceService(
            ModelTeamFunctionProvider(malformed_predict)
        )

        with self.assertRaises(InvalidModelOutput):
            service.predict(make_chunk(256))

    def test_model_team_function_exception_becomes_model_execution_error(
        self,
    ) -> None:
        def failing_predict(raw_window):
            raise RuntimeError("model artifact failure")

        service = ModelInferenceService(
            ModelTeamFunctionProvider(failing_predict)
        )

        with self.assertRaisesRegex(ModelExecutionError, "artifact failure"):
            service.predict(make_chunk(256))

    @patch(
        "backend.app.model.provider.import_module",
        side_effect=ModuleNotFoundError("missing inference module"),
    )
    def test_missing_model_team_package_fails_without_stub_fallback(
        self,
        import_mock,
    ) -> None:
        with self.assertRaisesRegex(
            ModelProviderLoadError,
            "REAL MODEL LOAD FAILED",
        ) as context:
            create_runtime_model_provider("model_team")

        self.assertIn(MODEL_TEAM_EXPECTED_CALLABLE, str(context.exception))
        import_mock.assert_called_once_with(
            ".inference",
            package="backend.app.model",
        )

    @patch(
        "backend.app.model.provider.import_module",
        return_value=SimpleNamespace(),
    )
    def test_missing_model_team_callable_fails_fast(self, import_mock) -> None:
        with self.assertRaisesRegex(
            ModelProviderLoadError,
            "does not expose the required callable",
        ):
            load_model_team_predict_function()

        import_mock.assert_called_once()

    def test_non_callable_loader_result_fails_fast(self) -> None:
        with self.assertRaisesRegex(
            ModelProviderLoadError,
            "did not return a callable",
        ):
            create_runtime_model_provider(
                "model_team",
                model_function_loader=lambda: None,
            )

    def test_unknown_provider_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ModelProviderLoadError,
            "Unsupported MODEL_PROVIDER value",
        ):
            create_runtime_model_provider("automatic")


def concentrating_result_function(raw_window):
    return concentrating_result()


if __name__ == "__main__":
    unittest.main()
