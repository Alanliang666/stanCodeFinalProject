"""FastAPI health/WebSocket integration tests without Muse hardware."""

import unittest

from fastapi.testclient import TestClient

from backend.app.server import ServerConfig, create_app


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


if __name__ == "__main__":
    unittest.main()
