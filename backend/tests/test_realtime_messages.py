"""Tests for fixed realtime JSON message contracts."""

import json
import unittest

from backend.app.model.contracts import CognitivePrediction
from backend.app.realtime.messages import (
    create_cognitive_prediction_message,
    create_device_status_message,
    create_eeg_chunk_message,
)
from backend.tests.helpers import make_chunk


class RealtimeMessageTests(unittest.TestCase):
    def test_device_status_contract(self) -> None:
        message = create_device_status_message(True)

        self.assertEqual(message["type"], "device_status")
        self.assertTrue(message["data"]["connected"])
        self.assertEqual(message["data"]["device"], "Muse 2")
        self.assertEqual(message["data"]["sampling_rate_hz"], 256)
        self.assertEqual(
            message["data"]["channel_order"],
            ["TP9", "AF7", "AF8", "TP10"],
        )

    def test_eeg_chunk_is_json_compatible_and_preserves_n_by_4_semantics(self) -> None:
        message = create_eeg_chunk_message(make_chunk(12))

        self.assertEqual(message["type"], "eeg_chunk")
        self.assertEqual(message["data"]["sampling_rate_hz"], 256)
        self.assertEqual(
            message["data"]["channel_order"],
            ["TP9", "AF7", "AF8", "TP10"],
        )
        self.assertEqual(len(message["data"]["timestamps"]), 12)
        self.assertEqual(len(message["data"]["samples"]), 12)
        self.assertTrue(
            all(len(sample) == 4 for sample in message["data"]["samples"])
        )
        json.dumps(message)

    def test_cognitive_prediction_contract(self) -> None:
        prediction = CognitivePrediction.from_raw_result(
            {
                "state": "concentration",
                "confidence": 0.88,
                "probabilities": {
                    "relaxed_openeye": 0.06,
                    "concentration": 0.88,
                    "relaxed_closeeye": 0.06,
                },
            }
        )

        message = create_cognitive_prediction_message(
            prediction,
            timestamp=1234567890.123,
        )

        self.assertEqual(message["type"], "cognitive_prediction")
        self.assertEqual(message["data"]["timestamp"], 1234567890.123)
        self.assertEqual(message["data"]["state"], "concentration")
        self.assertEqual(message["data"]["confidence"], 0.88)
        self.assertEqual(
            message["data"]["probabilities"],
            {
                "relaxed_openeye": 0.06,
                "concentration": 0.88,
                "relaxed_closeeye": 0.06,
            },
        )
        json.dumps(message)

    def test_illegal_prediction_cannot_bypass_model_contract(self) -> None:
        with self.assertRaisesRegex(ValueError, "state must be"):
            CognitivePrediction(
                state="focused",
                confidence=0.7,
                probabilities={
                    "relaxed_openeye": 0.7,
                    "concentration": 0.2,
                    "relaxed_closeeye": 0.1,
                },
            )

        with self.assertRaisesRegex(ValueError, "state must be"):
            CognitivePrediction(
                state="relaxed",
                confidence=0.7,
                probabilities={
                    "relaxed_openeye": 0.7,
                    "concentration": 0.2,
                    "relaxed_closeeye": 0.1,
                },
            )

        with self.assertRaisesRegex(TypeError, "validated CognitivePrediction"):
            create_cognitive_prediction_message(
                {
                    "state": "concentration",
                    "confidence": 0.7,
                    "probabilities": {},
                }
            )


if __name__ == "__main__":
    unittest.main()
