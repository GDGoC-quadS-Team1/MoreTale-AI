import unittest

from prompts.illustration_prompt_utils import (
    build_illustration_prefix,
    split_scene_prompt,
)


class TestIllustrationPromptUtils(unittest.TestCase):
    def test_split_scene_prompt_prefix_match(self):
        image_style = "Vibrant digital art with soft, glowing light effects"
        design = (
            "A 5-year-old Korean boy named Woojin with bright, curious brown eyes, "
            "short, neat black hair, and a warm smile. He wears a blue t-shirt."
        )
        prefix = build_illustration_prefix(image_style, design)
        full = f"{prefix} Woojin is sitting by a window at night, wide shot."

        scene, method = split_scene_prompt(prefix, design, full)

        self.assertEqual(method, "prefix")
        self.assertEqual(scene, "Woojin is sitting by a window at night, wide shot.")

    def test_split_scene_prompt_design_match_when_prefix_differs(self):
        image_style = "Vibrant digital art"
        design = "A 5-year-old Korean boy named Woojin with short black hair."
        prefix = build_illustration_prefix(image_style, design)
        full = f"Different style, {design} , close-up, Woojin smiles brightly."

        scene, method = split_scene_prompt(prefix, design, full)

        self.assertEqual(method, "design")
        self.assertEqual(scene, "close-up, Woojin smiles brightly.")

    def test_split_scene_prompt_fallback(self):
        scene, method = split_scene_prompt(
            illustration_prefix="Style, Design",
            main_character_design="Design",
            full_prompt="Just a standalone prompt with no known parts.",
        )

        self.assertEqual(method, "fallback")
        self.assertEqual(scene, "Just a standalone prompt with no known parts.")


if __name__ == "__main__":
    unittest.main()
