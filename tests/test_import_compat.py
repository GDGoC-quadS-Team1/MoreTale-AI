import unittest
from importlib import import_module

from generators.illustration.illustration_prompt_utils import (
    build_illustration_prefix as canonical_build_illustration_prefix,
    split_scene_prompt as canonical_split_scene_prompt,
)
from generators.story.story_prompts import StoryPrompt as canonical_story_prompt_class


class TestImportCompatibility(unittest.TestCase):
    def test_canonical_story_prompt_import(self):
        module = import_module("generators.story.story_prompts")
        self.assertIs(module.StoryPrompt, canonical_story_prompt_class)

    def test_canonical_illustration_utils_import(self):
        module = import_module("generators.illustration.illustration_prompt_utils")
        self.assertIs(module.build_illustration_prefix, canonical_build_illustration_prefix)
        self.assertIs(module.split_scene_prompt, canonical_split_scene_prompt)

    def test_legacy_prompt_module_imports_removed(self):
        with self.assertRaises(ModuleNotFoundError):
            import_module("prompts.story_prompts")
        with self.assertRaises(ModuleNotFoundError):
            import_module("prompts.illustration_prompt_utils")


if __name__ == "__main__":
    unittest.main()
