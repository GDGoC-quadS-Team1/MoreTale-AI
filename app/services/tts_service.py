from __future__ import annotations

import os

from generators.story.story_model import Story
from generators.tts.tts_generator import TTSGenerator

from app.schemas.story import StoryCreateRequest
from app.services.storage import get_run_dir


class TTSService:
    @staticmethod
    def generate_tts(request: StoryCreateRequest, story_id: str, story: Story) -> dict:
        api_key = (os.getenv("GEMINI_TTS_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_TTS_API_KEY environment variable not set.")

        generator = TTSGenerator(
            api_key=api_key,
            model_name=request.generation.tts_model,
            voice_name=request.generation.tts_voice,
            temperature=request.generation.tts_temperature,
            request_interval_sec=request.generation.tts_request_interval_sec,
        )
        return generator.generate_book_audio(
            story=story,
            output_dir=str(get_run_dir(story_id)),
            primary_language=request.primary_lang,
            secondary_language=request.secondary_lang,
            skip_existing=True,
        )

