import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from models.story_model import Story
from prompts.illustration_prompt_utils import (
    build_illustration_prefix,
    split_scene_prompt,
)
from prompts.story_prompts import StoryPrompt
from typing import Optional

load_dotenv()
gemini_api_key = os.getenv("GEMINI_STORY_API_KEY")

class StoryGenerator:
    def __init__(self, model_name: str = "gemini-2.5-flash", include_style_guide: bool = False):
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_name = model_name
        self.prompts = StoryPrompt(include_style_guide=include_style_guide)

    def generate_story(
        self,
        child_name: str,
        primary_lang: str,
        secondary_lang: str,
        theme: str,
        extra_prompt: str = "",
        child_age: Optional[int] = None,
    ) -> Story:
        """
        Generates a bilingual fairy tale using the Gemini API.
        """
        user_prompt = self.prompts.generate_user_prompt(
            child_name=child_name,
            child_age=child_age,
            primary_lang=primary_lang,
            secondary_lang=secondary_lang,
            theme=theme,
            extra_prompt=extra_prompt,
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.prompts.system_instruction,
                    temperature=1.0, # High creativity
                    response_mime_type="application/json",
                    response_schema=Story,
                ),
            )
            
            if response.parsed:
                story = response.parsed
            else:
                story = Story.model_validate_json(response.text)

            self._populate_illustration_fields(story)
            return story

        except Exception as e:
            print(f"Error generating story: {e}")
            raise

    @staticmethod
    def _populate_illustration_fields(story: Story) -> None:
        illustration_prefix = build_illustration_prefix(
            story.image_style, story.main_character_design
        )
        story.illustration_prefix = illustration_prefix

        for page in story.pages:
            scene, method = split_scene_prompt(
                illustration_prefix=illustration_prefix,
                main_character_design=story.main_character_design,
                full_prompt=page.illustration_prompt,
            )
            page.illustration_scene_prompt = scene

            if method == "fallback":
                print(
                    "[warn] Could not split illustration_prompt into scene prompt; "
                    f"page={page.page_number} method={method}"
                )
