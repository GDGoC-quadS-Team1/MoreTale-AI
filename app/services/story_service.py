from __future__ import annotations

from generators.story.story_generator import StoryGenerator
from generators.story.story_model import Story

from app.schemas.story import StoryCreateRequest


class StoryService:
    @staticmethod
    def generate_story(request: StoryCreateRequest) -> tuple[Story, str]:
        generator = StoryGenerator(
            model_name=request.generation.story_model,
            include_style_guide=request.include_style_guide,
        )
        story = generator.generate_story(
            child_name=request.child_name,
            child_age=request.child_age,
            primary_lang=request.primary_lang,
            secondary_lang=request.secondary_lang,
            theme=request.theme,
            extra_prompt=request.extra_prompt,
        )
        return story, generator.model_name

