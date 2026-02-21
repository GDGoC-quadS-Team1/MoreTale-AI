from __future__ import annotations

import os

from generators.illustration.illustration_pipeline import IllustrationGenerator
from generators.story.story_model import Story

from app.schemas.story import StoryCreateRequest
from app.services.storage import get_run_dir


class IllustrationService:
    @staticmethod
    def generate_illustrations(
        request: StoryCreateRequest, story_id: str, story: Story
    ) -> dict:
        api_key = (os.getenv("NANO_BANANA_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("NANO_BANANA_KEY environment variable not set.")

        generator = IllustrationGenerator(
            api_key=api_key,
            model_name=request.generation.illustration_model,
            aspect_ratio=request.generation.illustration_aspect_ratio,
            request_interval_sec=request.generation.illustration_request_interval_sec,
        )
        return generator.generate_from_story(
            story=story,
            output_dir=str(get_run_dir(story_id)),
            skip_existing=request.generation.illustration_skip_existing,
        )

