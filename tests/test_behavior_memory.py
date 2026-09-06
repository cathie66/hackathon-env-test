import os
import unittest
from unittest.mock import patch

from behavior_memory import (
    analyze_behavior,
    build_memory_entry,
    demo_grooming_analysis,
    local_behavior_analysis,
)


class BehaviorMemoryTests(unittest.TestCase):
    def test_text_analysis_keeps_grooming_probabilistic(self) -> None:
        analysis = local_behavior_analysis(
            "我刚撸完胖胖，它就开始疯狂舔毛。",
            "胖胖",
        )
        self.assertEqual(analysis.observed_behavior, "grooming")
        self.assertIn("有时", analysis.general_meaning)
        self.assertIn("可能", analysis.pet_specific_pattern)

    def test_memory_is_saved_only_after_explicit_build(self) -> None:
        analysis = demo_grooming_analysis("胖胖")
        entry = build_memory_entry("被摸之后", analysis)
        self.assertEqual(entry["context"], "被摸之后")
        self.assertEqual(entry["observed_behavior"], "grooming")
        self.assertIn("胖胖在被撸之后经常", entry["pet_specific_pattern"])

    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_vision_path_has_text_fallback_without_key(self) -> None:
        analysis, source = analyze_behavior(
            b"not-used-without-key",
            "胖胖正在舔毛",
            "胖胖",
        )
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.observed_behavior, "grooming")
        self.assertEqual(source, "fallback:text:no_api_key")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_invalid_image_fails_cleanly(self) -> None:
        analysis, source = analyze_behavior(
            b"not-an-image",
            "胖胖正在舔毛",
            "胖胖",
        )
        self.assertIsNone(analysis)
        self.assertEqual(source, "failed:invalid_image")


if __name__ == "__main__":
    unittest.main()
