from __future__ import annotations

from generators.story.story_model import Story

from app.schemas.story import StoryCreateRequest
from app.services.generation_pipeline import (
    build_pipeline_request_from_story_request,
    generate_illustrations,
)
from app.services.output_paths import get_run_dir


class IllustrationService:
    @staticmethod
    def generate_illustrations(
        request: StoryCreateRequest, story_id: str, story: Story
    ) -> dict:
        return generate_illustrations(
            request=build_pipeline_request_from_story_request(request),
            story=story,
            output_dir=get_run_dir(story_id),
        )
