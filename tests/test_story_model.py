import unittest

from generators.story.story_model import Page, Story


class TestStoryValidation(unittest.TestCase):
    def setUp(self):
        self.valid_page = Page(
            page_number=1,
            text_primary="Test primary",
            text_secondary="Test secondary",
            illustration_prompt="Test illustration",
        )

    def test_valid_story_creation(self):
        story = Story(
            title_primary="Test Title",
            title_secondary="Test Title 2",
            author_name="AI",
            primary_language="Korean",
            secondary_language="English",
            image_style="Watercolor",
            main_character_design="Boy",
            pages=[self.valid_page.model_copy(update={"page_number": i + 1}) for i in range(24)],
        )
        self.assertEqual(len(story.pages), 24)

    def test_invalid_page_count_low(self):
        pages = [self.valid_page.model_copy(update={"page_number": i + 1}) for i in range(23)]

        with self.assertRaises(ValueError) as context:
            Story(
                title_primary="Test Title",
                title_secondary="Test Title 2",
                author_name="AI",
                primary_language="Korean",
                secondary_language="English",
                image_style="Watercolor",
                main_character_design="Boy",
                pages=pages,
            )

        self.assertIn("Story must have exactly 24 pages", str(context.exception))

    def test_invalid_page_count_high(self):
        pages = [self.valid_page.model_copy(update={"page_number": i + 1}) for i in range(25)]

        with self.assertRaises(ValueError) as context:
            Story(
                title_primary="Test Title",
                title_secondary="Test Title 2",
                author_name="AI",
                primary_language="Korean",
                secondary_language="English",
                image_style="Watercolor",
                main_character_design="Boy",
                pages=pages,
            )

        self.assertIn("Story must have exactly 24 pages", str(context.exception))


if __name__ == "__main__":
    unittest.main()
