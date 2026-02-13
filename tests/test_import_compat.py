import unittest

from generators.illustration.illustration_prompt_utils import (
    build_illustration_prefix as canonical_build_illustration_prefix,
    split_scene_prompt as canonical_split_scene_prompt,
)
from generators.story.story_model import Story as canonical_story_class
from generators.story.story_prompts import StoryPrompt as canonical_story_prompt_class
from models.story_model import Story as legacy_story_class
from prompts.illustration_prompt_utils import (
    build_illustration_prefix as legacy_build_illustration_prefix,
    split_scene_prompt as legacy_split_scene_prompt,
)
from prompts.story_prompts import StoryPrompt as legacy_story_prompt_class


class TestImportCompatibility(unittest.TestCase):
    def test_story_model_identity(self):
        self.assertIs(legacy_story_class, canonical_story_class)

    def test_story_prompt_identity(self):
        self.assertIs(legacy_story_prompt_class, canonical_story_prompt_class)

    def test_illustration_utils_identity(self):
        self.assertIs(
            legacy_build_illustration_prefix, canonical_build_illustration_prefix
        )
        self.assertIs(legacy_split_scene_prompt, canonical_split_scene_prompt)


if __name__ == "__main__":
    unittest.main()
