import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException

from app.schemas.story import StoryCreateRequest
from app.services.story_orchestrator import (
    enqueue_story_generation,
    job_store,
    load_story_result,
    run_story_generation_job_background,
    run_story_generation_job,
)
from generators.story.story_model import STORY_PAGE_COUNT, Page, Story, VocabularyEntry


def _build_fake_story() -> Story:
    pages = [
        Page(
            page_number=page_number,
            text_primary=f"Primary text {page_number}",
            text_secondary=f"Secondary text {page_number}",
            illustration_prompt=f"Illustration prompt {page_number}",
            illustration_scene_prompt=f"Scene prompt {page_number}",
            vocabulary=[
                VocabularyEntry(
                    entry_id=f"page-{page_number}-dragon",
                    primary_word="dragon",
                    secondary_word="용",
                    primary_definition="a large creature from stories",
                    secondary_definition="이야기 속 상상의 큰 동물",
                )
            ],
        )
        for page_number in range(1, STORY_PAGE_COUNT + 1)
    ]
    return Story(
        title_primary="Test Title Primary",
        title_secondary="Test Title Secondary",
        author_name="Test Author",
        primary_language="Korean",
        secondary_language="English",
        image_style="Soft watercolor",
        main_character_design="A child with short hair and green clothes",
        pages=pages,
    )


class TestStoryOrchestrator(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

        self.env_patcher = patch.dict(
            os.environ,
            {
                "MORETALE_API_KEY": "test-api-key",
                "MORETALE_OUTPUTS_DIR": self.tmp_dir.name,
                "MORETALE_RATE_LIMIT_POST_STORIES_PER_MIN": "100",
            },
            clear=False,
        )
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)

    @staticmethod
    def _build_create_payload() -> dict:
        return {
            "child_name": "Mina",
            "child_age": 5,
            "primary_lang": "Korean",
            "secondary_lang": "English",
            "theme": "Friendship",
            "extra_prompt": "Include a dragon",
            "include_style_guide": False,
            "generation": {
                "story_model": "gemini-2.5-flash",
                "enable_tts": False,
                "enable_illustration": False,
            },
        }

    def test_enqueue_story_generation_initializes_job_and_background_task(self) -> None:
        request = StoryCreateRequest.model_validate(self._build_create_payload())
        background_tasks = BackgroundTasks()

        with patch(
            "app.services.story_orchestrator.make_story_id",
            return_value="20260221_150001_story_mina",
        ):
            response = enqueue_story_generation(
                request=request,
                background_tasks=background_tasks,
                request_id="req-123",
            )

        self.assertEqual(response.id, "20260221_150001_story_mina")
        self.assertEqual(response.status, "queued")
        self.assertEqual(len(background_tasks.tasks), 1)
        self.assertEqual(background_tasks.tasks[0].func, run_story_generation_job_background)

        job = job_store.load_job("20260221_150001_story_mina")
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "queued")

    def test_run_story_generation_job_marks_completed_with_assets_summary(self) -> None:
        story_id = "20260221_150002_story_mina"
        payload = self._build_create_payload()
        job_store.initialize_job(story_id=story_id, request_payload=payload)

        with patch(
            "app.services.generation_pipeline.generate_story",
            return_value=(_build_fake_story(), "gemini-2.5-flash"),
        ):
            run_story_generation_job(story_id=story_id, request_payload=payload)

        job = job_store.load_job(story_id)
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "completed")
        self.assertFalse(job["result"]["assets"]["has_partial_failures"])

    def test_run_story_generation_job_writes_quiz_when_enabled(self) -> None:
        story_id = "20260221_150004_story_mina"
        payload = self._build_create_payload()
        payload["generation"]["enable_quiz"] = True
        job_store.initialize_job(story_id=story_id, request_payload=payload)
        fake_quiz = type(
            "FakeQuiz",
            (),
            {
                "model_dump_json": lambda self, indent=4: '{"story_id":"story","question_count":5,"questions":[]}',
                "model_dump": lambda self, mode="json": {"story_id": "story"},
            },
        )()

        with patch(
            "app.services.generation_pipeline.generate_story",
            return_value=(_build_fake_story(), "gemini-2.5-flash"),
        ):
            with patch(
                "app.services.generation_pipeline.generate_quiz",
                return_value=(fake_quiz, "gemini-2.5-flash"),
            ) as mocked_quiz:
                run_story_generation_job(story_id=story_id, request_payload=payload)

        job = job_store.load_job(story_id)
        self.assertIsNotNone(job)
        self.assertEqual(job["status"], "completed")
        self.assertTrue(job["result"]["quiz_json_url"].endswith("/quiz_gemini-2.5-flash.json"))
        self.assertIsNone(job["result"]["quiz"]["service_error"])
        mocked_quiz.assert_called_once()

    def test_load_story_result_rejects_queued_job(self) -> None:
        story_id = "20260221_150003_story_mina"
        job_store.initialize_job(story_id=story_id, request_payload=self._build_create_payload())

        with self.assertRaises(HTTPException) as context:
            load_story_result(story_id)

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.detail["error"]["code"], "STORY_NOT_READY")


if __name__ == "__main__":
    unittest.main()
