import os
import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest


class AppSmokeTests(unittest.TestCase):
    @staticmethod
    def sample_image() -> bytes:
        buffer = BytesIO()
        Image.new("RGB", (80, 80), "#69705a").save(buffer, format="PNG")
        return buffer.getvalue()

    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_room_submission_reaches_settled_with_fallback(self) -> None:
        app = AppTest.from_file("app.py")
        app.session_state["page"] = "room"
        app.session_state["phase"] = "IDLE"
        app.session_state["pet_profile"] = {
            "name": "团子",
            "image": self.sample_image(),
            "image_mime": "image/png",
            "traits": ["高冷"],
            "usual_companion_behavior": "看我一眼然后走开",
            "emotion_response_profile": {"anxious": "curl_up"},
            "pet_behavior_memory": [],
        }
        app.session_state["last_action"] = None
        app.session_state["last_response"] = None
        app.session_state["last_response_source"] = None

        app.run(timeout=10)
        self.assertEqual(len(app.exception), 0)
        app.chat_input[0].set_value("明天的事情让我很焦虑")
        app.run(timeout=10)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["phase"], "SETTLED")
        self.assertEqual(app.session_state["last_action"], "curl_up")
        self.assertEqual(app.session_state["last_response_source"], "fallback:no_api_key")
        self.assertIn(
            "explanation",
            app.session_state["last_response"],
        )

        app.chat_input[0].set_value("今天真的很累")
        app.run(timeout=10)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["phase"], "SETTLED")


if __name__ == "__main__":
    unittest.main()
