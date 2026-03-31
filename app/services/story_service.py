from __future__ import annotations

from generators.story.story_model import Story

from app.schemas.story import StoryCreateRequest
from app.services.generation_pipeline import (
    build_pipeline_request_from_story_request,
    generate_story,
)


class StoryService:
    @staticmethod
    def generate_story(request: StoryCreateRequest) -> tuple[Story, str]:
        return generate_story(build_pipeline_request_from_story_request(request))
