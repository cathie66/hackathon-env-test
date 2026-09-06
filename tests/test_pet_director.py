import unittest
from unittest.mock import patch

from pet_director import get_companion_response, local_fallback


class PetDirectorFallbackTests(unittest.TestCase):
    def test_tired_cat_curls_up(self) -> None:
        response = local_fallback("今天真的好累", ["贪睡"], "趴在我附近")
        self.assertEqual(response.emotion, "tired")
        self.assertEqual(response.action, "curl_up")

    def test_kneading_trait_changes_tired_response(self) -> None:
        response = local_fallback("我有点撑不住了", ["爱踩奶"], "给我踩奶")
        self.assertEqual(response.action, "knead")

    def test_anxious_personality_changes_action(self) -> None:
        affectionate = local_fallback("明天的事情让我很焦虑", ["黏人"], "靠着我")
        aloof = local_fallback("明天的事情让我很焦虑", ["高冷"], "看我一眼然后走开")
        self.assertEqual(affectionate.action, "come_closer")
        self.assertEqual(aloof.action, "curl_up")

    def test_caption_is_never_over_22_characters(self) -> None:
        cases = [
            ("我很难过", ["黏人"], "靠着我"),
            ("今天好开心", ["爱撒娇"], "主动蹭我"),
            ("我快要崩溃了", ["高冷"], "看我一眼然后走开"),
            ("普通的一天", ["爱踩奶"], "给我踩奶"),
        ]
        for text, traits, behavior in cases:
            with self.subTest(text=text):
                response = local_fallback(text, traits, behavior)
                self.assertLessEqual(len(response.caption), 22)

    def test_neutral_response_avoids_previous_action(self) -> None:
        response = local_fallback("今天就这样", ["黏人"], "靠着我", "come_closer")
        self.assertNotEqual(response.action, "come_closer")

    def test_emotion_profile_overrides_traits(self) -> None:
        response = local_fallback(
            "今天真的好累",
            ["黏人"],
            "靠着我",
            emotion_response_profile={"tired": "grooming"},
            pet_name="胖胖",
        )
        self.assertEqual(response.action, "grooming")
        self.assertIn("你之前告诉我", response.explanation.about_my_pet)

    def test_same_emotion_differs_between_profiles(self) -> None:
        grooming = local_fallback(
            "今天真的好累",
            ["黏人"],
            "靠着我",
            emotion_response_profile={"tired": "grooming"},
        )
        approaching = local_fallback(
            "今天真的好累",
            ["高冷"],
            "趴在我附近",
            emotion_response_profile={"tired": "come_closer"},
        )
        self.assertEqual(grooming.action, "grooming")
        self.assertEqual(approaching.action, "come_closer")

    def test_behavior_memory_can_drive_and_explain_response(self) -> None:
        memory = [{
            "context": "被摸之后",
            "observed_behavior": "grooming",
            "general_meaning": "理毛可能与自我整理有关。",
            "pet_specific_pattern": "胖胖经常在被撸之后开始认真舔毛。",
            "confidence": "medium",
        }]
        response = local_fallback(
            "今天有点累，只想安静待一会",
            ["高冷"],
            "趴在我附近",
            pet_behavior_memory=memory,
            pet_name="胖胖",
        )
        self.assertEqual(response.action, "grooming")
        self.assertIn("胖胖经常", response.explanation.about_my_pet)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("pet_director._request_openai", side_effect=RuntimeError("offline"))
    def test_api_failure_uses_local_fallback(self, _mock_request) -> None:
        response, source = get_companion_response(
            "我今天很难过", "团子", ["黏人"], "靠着我", timeout_seconds=0.1
        )
        self.assertEqual(response.action, "come_closer")
        self.assertEqual(source, "fallback:RuntimeError")

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("pet_director._request_openai", side_effect=RuntimeError("offline"))
    def test_api_failure_still_respects_emotion_profile(self, _mock_request) -> None:
        response, source = get_companion_response(
            "我今天好累",
            "胖胖",
            ["黏人"],
            "靠着我",
            timeout_seconds=0.1,
            emotion_response_profile={"tired": "grooming"},
        )
        self.assertEqual(response.action, "grooming")
        self.assertEqual(source, "fallback:RuntimeError")


if __name__ == "__main__":
    unittest.main()
