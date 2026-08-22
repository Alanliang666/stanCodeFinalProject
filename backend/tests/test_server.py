"""FastAPI health/WebSocket integration tests without Muse hardware."""

import unittest

from fastapi.testclient import TestClient

from backend.app.config import EEGInferenceConfig
from backend.app.server import ServerConfig, create_app
from backend.app.model.provider import ModelTeamFunctionProvider


class LocalAgentServerTests(unittest.TestCase):
    def test_health_endpoint_and_websocket_initial_status(self) -> None:
        app = create_app(
            config=ServerConfig(source_mode="muse"),
            start_agent=False,
            write_line=lambda line: None,
        )

        with TestClient(app) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json(),
                {
                    "status": "ok",
                    "device_connected": False,
                    "model_provider": "STUB MODEL",
                    "sampling_rate_hz": 256,
                    "inference_window_samples": 256,
                    "inference_window_sec": 1.0,
                    "inference_stride_samples": 256,
                    "inference_stride_sec": 1.0,
                },
            )

            with client.websocket_connect("/ws") as websocket:
                message = websocket.receive_json()
                self.assertEqual(message["type"], "device_status")
                self.assertFalse(message["data"]["connected"])

    def test_synthetic_server_streams_all_three_message_types(self) -> None:
        log_lines = []
        app = create_app(
            config=ServerConfig(source_mode="synthetic"),
            start_agent=True,
            write_line=log_lines.append,
        )

        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                received_types = set()
                for _ in range(20):
                    message = websocket.receive_json()
                    received_types.add(message["type"])
                    if received_types == {
                        "device_status",
                        "eeg_chunk",
                        "cognitive_prediction",
                    }:
                        break

        self.assertEqual(
            received_types,
            {"device_status", "eeg_chunk", "cognitive_prediction"},
        )
        self.assertIn("Source: MOCK / SYNTHETIC STREAM", log_lines)
        self.assertIn("Model provider: STUB MODEL", log_lines)
        self.assertIn("EEG sampling rate: 256 Hz", log_lines)
        self.assertIn(
            "Inference window: 256 samples (1.000 sec)",
            log_lines,
        )
        self.assertIn(
            "Inference stride: 256 samples (1.000 sec)",
            log_lines,
        )

    def test_synthetic_source_is_independent_from_model_team_provider(self) -> None:
        def fake_predict_mental_state(raw_window):
            self.assertEqual(raw_window.shape, (256, 4))
            self.assertTrue(raw_window.flags.writeable)
            return {
                "state": "concentration",
                "confidence": 0.88,
                "probabilities": {
                    "relaxed_openeye": 0.06,
                    "concentration": 0.88,
                    "relaxed_closeeye": 0.06,
                },
            }

        app = create_app(
            config=ServerConfig(source_mode="synthetic"),
            model_provider=ModelTeamFunctionProvider(
                fake_predict_mental_state
            ),
            start_agent=True,
            write_line=lambda line: None,
        )

        with TestClient(app) as client:
            self.assertEqual(
                client.get("/health").json()["model_provider"],
                "MODEL TEAM - predict_mental_state",
            )
            with client.websocket_connect("/ws") as websocket:
                prediction = None
                for _ in range(20):
                    message = websocket.receive_json()
                    if message["type"] == "cognitive_prediction":
                        prediction = message
                        break

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction["data"]["state"], "concentration")
        self.assertEqual(
            prediction["data"]["probabilities"],
            {
                "relaxed_openeye": 0.06,
                "concentration": 0.88,
                "relaxed_closeeye": 0.06,
            },
        )

    def test_512_by_256_config_is_exposed_and_runs_synthetic_chunks(self) -> None:
        received_shapes = []

        def fake_predict_mental_state(raw_window):
            received_shapes.append(raw_window.shape)
            return {
                "state": "concentration",
                "confidence": 0.88,
                "probabilities": {
                    "relaxed_openeye": 0.06,
                    "concentration": 0.88,
                    "relaxed_closeeye": 0.06,
                },
            }

        app = create_app(
            config=ServerConfig(source_mode="synthetic"),
            inference_config=EEGInferenceConfig(
                window_samples=512,
                stride_samples=256,
            ),
            model_provider=ModelTeamFunctionProvider(
                fake_predict_mental_state,
                supported_window_samples=(512,),
            ),
            start_agent=True,
            write_line=lambda line: None,
        )

        with TestClient(app) as client:
            health = client.get("/health").json()
            with client.websocket_connect("/ws") as websocket:
                for _ in range(30):
                    if websocket.receive_json()["type"] == "cognitive_prediction":
                        break

        self.assertEqual(health["inference_window_samples"], 512)
        self.assertEqual(health["inference_window_sec"], 2.0)
        self.assertEqual(health["inference_stride_samples"], 256)
        self.assertEqual(health["inference_stride_sec"], 1.0)
        self.assertIn((512, 4), received_shapes)


if __name__ == "__main__":
    unittest.main()
