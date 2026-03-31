import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services.generation_pipeline import (
    StoryPipelineRequest,
    run_story_generation_pipeline,
)


def _build_request(**overrides) -> StoryPipelineRequest:
    payload = {
        "child_name": "Mina",
        "child_age": 5,
        "primary_lang": "Korean",
        "secondary_lang": "English",
        "theme": "Friendship",
        "extra_prompt": "Include a dragon",
        "include_style_guide": False,
        "story_model": "gemini-2.5-flash",
        "enable_tts": False,
        "tts_model": "gemini-2.5-flash-preview-tts",
        "tts_voice": "Achernar",
        "tts_temperature": 1.0,
        "tts_request_interval_sec": 10.0,
        "enable_illustration": False,
        "enable_cover_illustration": True,
        "illustration_model": "gemini-2.5-flash-image",
        "illustration_aspect_ratio": "1:1",
        "illustration_cover_aspect_ratio": "5:4",
        "illustration_request_interval_sec": 1.0,
        "illustration_skip_existing": True,
    }
    payload.update(overrides)
    return StoryPipelineRequest(**payload)


class TestGenerationPipeline(unittest.TestCase):
    def test_non_strict_pipeline_captures_tts_error_and_continues(self):
        request = _build_request(enable_tts=True, enable_illustration=True)
        fake_story = SimpleNamespace(
            title_primary="Test Story",
            model_dump_json=lambda indent=4: '{"title_primary":"Test Story","pages":[]}',
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "app.services.generation_pipeline.generate_story",
                return_value=(fake_story, "gemini-2.5-flash"),
            ):
                with patch(
                    "app.services.generation_pipeline.generate_tts",
                    side_effect=RuntimeError("tts unavailable"),
                ):
                    with patch(
                        "app.services.generation_pipeline.generate_illustrations",
                        return_value={"total_tasks": 1, "generated": 1, "skipped": 0, "failed": 0, "cover": {"status": "generated"}, "manifest_path": "manifest.json"},
                    ) as mocked_illustrations:
                        result = run_story_generation_pipeline(
                            request=request,
                            output_dir_factory=lambda story, model: Path(tmp_dir) / "run",
                            strict_assets=False,
                        )

        self.assertEqual(result.service_errors["tts"], "tts unavailable")
        self.assertIsNotNone(result.illustration_result)
        mocked_illustrations.assert_called_once()

    def test_strict_pipeline_raises_on_missing_tts_key(self):
        request = _build_request(enable_tts=True)
        fake_story = SimpleNamespace(
            title_primary="Test Story",
            model_dump_json=lambda indent=4: '{"title_primary":"Test Story","pages":[]}',
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "app.services.generation_pipeline.generate_story",
                return_value=(fake_story, "gemini-2.5-flash"),
            ):
                with patch.dict(os.environ, {}, clear=True):
                    with self.assertRaises(RuntimeError):
                        run_story_generation_pipeline(
                            request=request,
                            output_dir_factory=lambda story, model: Path(tmp_dir) / "run",
                            strict_assets=True,
                        )


if __name__ == "__main__":
    unittest.main()
