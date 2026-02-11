import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from models.story_model import Story
from prompts.story_prompts import StoryPrompt

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

class StoryGenerator:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_name = model_name
        self.prompts = StoryPrompt()

    def generate_story(self, child_name: str, primary_lang: str, secondary_lang: str, theme: str, extra_prompt: str = "") -> Story:
        """
        Generates a bilingual fairy tale using the Gemini API.
        """
        user_prompt = self.prompts.generate_user_prompt(child_name, primary_lang, secondary_lang, theme, extra_prompt)
        
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
                return response.parsed
            else:
                return Story.model_validate_json(response.text)

        except Exception as e:
            print(f"Error generating story: {e}")
            raise
