import os
import tempfile
import unittest
from types import SimpleNamespace

from generators.illustration.illustration_generator import IllustrationGenerator


class _FakeIllustrationGenerator(IllustrationGenerator):
    def __init__(self):
        super().__init__(api_key="dummy", client=SimpleNamespace(models=None))
        self.seen_prompts: list[str] = []

    def _generate_image_bytes(self, prompt: str) -> tuple[bytes, str]:
        self.seen_prompts.append(prompt)
        return b"fake-image-bytes", "image/png"


class TestIllustrationPromptBuild(unittest.TestCase):
    def test_build_page_prompt_uses_scene_and_full_prompt(self):
        story = SimpleNamespace(
            illustration_prefix="Dreamy style, Main character",
            image_style="Dreamy style",
            main_character_design="Main character",
        )
        page = SimpleNamespace(
            page_number=1,
            illustration_prompt="Dreamy style, Main character, full prompt details",
            illustration_scene_prompt="page specific scene",
        )

        prompt, mode = IllustrationGenerator._build_page_prompt(story=story, page=page)

        self.assertEqual(mode, "scene_plus_full")
        self.assertIn("Dreamy style, Main character, page specific scene", prompt)
        self.assertIn("Reference details for consistency", prompt)
        self.assertIn("full prompt details", prompt)

    def test_build_page_prompt_falls_back_to_full_prompt(self):
        story = SimpleNamespace(
            illustration_prefix="",
            image_style="Dreamy style",
            main_character_design="Main character",
        )
        page = SimpleNamespace(
            page_number=2,
            illustration_prompt="fallback full prompt",
            illustration_scene_prompt="",
        )

        prompt, mode = IllustrationGenerator._build_page_prompt(story=story, page=page)

        self.assertEqual(mode, "full_only")
        self.assertEqual(prompt, "fallback full prompt")


class TestIllustrationGenerationPipeline(unittest.TestCase):
    def test_generate_from_story_creates_page_images_and_manifest(self):
        generator = _FakeIllustrationGenerator()
        story = SimpleNamespace(
            pages=[
                SimpleNamespace(
                    page_number=1,
                    illustration_prompt="full prompt 1",
                    illustration_scene_prompt="scene 1",
                ),
                SimpleNamespace(
                    page_number=2,
                    illustration_prompt="full prompt 2",
                    illustration_scene_prompt="scene 2",
                ),
            ],
            illustration_prefix="prefix",
            image_style="style",
            main_character_design="design",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = generator.generate_from_story(
                story=story,
                output_dir=tmp_dir,
                skip_existing=False,
            )

            self.assertEqual(result["generated"], 2)
            self.assertEqual(result["failed"], 0)
            self.assertTrue(
                os.path.exists(os.path.join(tmp_dir, "illustrations", "page_01.png"))
            )
            self.assertTrue(
                os.path.exists(os.path.join(tmp_dir, "illustrations", "page_02.png"))
            )
            self.assertTrue(
                os.path.exists(os.path.join(tmp_dir, "illustrations", "manifest.json"))
            )
            self.assertEqual(len(generator.seen_prompts), 2)

    def test_generate_from_story_skips_existing_page(self):
        generator = _FakeIllustrationGenerator()
        story = SimpleNamespace(
            pages=[
                SimpleNamespace(
                    page_number=1,
                    illustration_prompt="full prompt 1",
                    illustration_scene_prompt="scene 1",
                )
            ],
            illustration_prefix="prefix",
            image_style="style",
            main_character_design="design",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            existing_path = os.path.join(tmp_dir, "illustrations", "page_01.png")
            os.makedirs(os.path.dirname(existing_path), exist_ok=True)
            with open(existing_path, "wb") as file:
                file.write(b"existing")

            result = generator.generate_from_story(
                story=story,
                output_dir=tmp_dir,
                skip_existing=True,
            )

            self.assertEqual(result["generated"], 0)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(len(generator.seen_prompts), 0)


if __name__ == "__main__":
    unittest.main()
