import tempfile
import unittest
from pathlib import Path

from prompts.story_prompts import StoryPrompt


class TestStoryPrompt(unittest.TestCase):
    def test_loads_and_formats_prompt(self):
        prompt = StoryPrompt()

        system_instruction = prompt.system_instruction
        user_prompt = prompt.generate_user_prompt(
            child_name="Mina",
            primary_lang="Korean",
            secondary_lang="English",
            theme="Friendship",
            extra_prompt="Include a dragon.",
        )

        self.assertIn("children's book author", system_instruction)
        self.assertIn("Mina", user_prompt)
        self.assertIn("Korean", user_prompt)
        self.assertIn("English", user_prompt)
        self.assertIn("Friendship", user_prompt)
        self.assertIn("Include a dragon.", user_prompt)

    def test_can_include_style_guide_in_system_instruction(self):
        prompt = StoryPrompt(include_style_guide=True)

        system_instruction = prompt.system_instruction

        self.assertIn("CHARACTER NAMING STRATEGY", system_instruction)

    def test_missing_system_instruction_file_raises(self):
        prompt = StoryPrompt(system_instruction_path="prompts/not_exists.txt")

        with self.assertRaises(FileNotFoundError) as context:
            _ = prompt.system_instruction

        self.assertIn("System instruction file not found", str(context.exception))

    def test_unknown_template_placeholder_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            template_path = Path(tmp_dir) / "user_prompt.txt"
            system_path = Path(tmp_dir) / "system_instruction.txt"
            template_path.write_text("Name: {child_name}, Bad: {unknown_key}", encoding="utf-8")
            system_path.write_text("system", encoding="utf-8")

            prompt = StoryPrompt(
                system_instruction_path=str(system_path),
                user_prompt_path=str(template_path),
            )

            with self.assertRaises(ValueError) as context:
                prompt.generate_user_prompt(
                    child_name="Mina",
                    primary_lang="Korean",
                    secondary_lang="English",
                    theme="Adventure",
                )

            self.assertIn("unknown placeholder", str(context.exception))


if __name__ == "__main__":
    unittest.main()
