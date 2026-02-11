
import unittest


from models.story_model import Story, Page



class TestStoryValidation(unittest.TestCase):


    def setUp(self):


        # Create a valid page template


        self.valid_page = Page(


            page_number=1,


            text_primary="Test",


            text_secondary="Test",


            illustration_prompt="Test illustration",


            sound_effects=["Bang"]

        )



    def test_valid_story_creation(self):


        """Test that a story with exactly 32 pages is valid."""
        

        story = Story(

            title_primary="Test Title",

            title_secondary="Test Title 2",

            author_name="AI",
            image_style="Watercolor",

            main_character_design="Boy",

            pages=[self.valid_page.model_copy(update={'page_number': i+1}) for i in range(32)]

        )

        jls_extract_var = self
        jls_extract_var.assertEqual(len(story.pages), 32)



    def test_invalid_page_count_low(self):


        """Test that a story with fewer than 32 pages raises a ValueError."""


        pages = [self.valid_page.model_copy(update={'page_number': i+1}) for i in range(31)]
        


        with self.assertRaises(ValueError) as context:


            Story(


                title_primary="Test Title",


                title_secondary="Test Title 2",


                author_name="AI",


                image_style="Watercolor",


                main_character_design="Boy",
                pages=pages

            )


        self.assertIn("Story must have exactly 32 pages", str(context.exception))



    def test_invalid_page_count_high(self):


        """Test that a story with more than 32 pages raises a ValueError."""


        pages = [self.valid_page.model_copy(update={'page_number': i+1}) for i in range(33)]
        


        with self.assertRaises(ValueError) as context:


            Story(


                title_primary="Test Title",


                title_secondary="Test Title 2",


                author_name="AI",


                image_style="Watercolor",


                main_character_design="Boy",
                pages=pages

            )


        self.assertIn("Story must have exactly 32 pages", str(context.exception))



if __name__ == '__main__':


    unittest.main()


