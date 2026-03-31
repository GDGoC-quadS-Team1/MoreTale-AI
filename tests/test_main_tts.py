import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main


def _fake_pipeline_result(tts_result: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        story=SimpleNamespace(title_primary="Test Story"),
        story_json_path=Path("outputs/story_gemini-2.5-flash.json"),
        tts_result=tts_result,
        illustration_result=None,
    )


class TestMainTTS(unittest.TestCase):
    def test_enable_tts_requires_tts_api_key(self):
        args = [
            "main.py",
            "--child_name",
            "Mina",
            "--primary_lang",
            "Korean",
            "--secondary_lang",
            "English",
            "--enable_tts",
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with patch(
                    "main.run_story_generation_pipeline",
                    side_effect=RuntimeError("GEMINI_TTS_API_KEY environment variable not set."),
                ):
                    with patch.object(sys, "argv", args):
                        with self.assertRaises(SystemExit) as context:
                            main.main()
                self.assertEqual(context.exception.code, 1)
            finally:
                os.chdir(original_cwd)

    def test_enable_tts_uses_10_seconds_default_interval(self):
        args = [
            "main.py",
            "--child_name",
            "Mina",
            "--primary_lang",
            "Spanish",
            "--secondary_lang",
            "French",
            "--enable_tts",
        ]

        tts_result = {
            "total_tasks": 48,
            "generated": 48,
            "skipped": 0,
            "failed": 0,
            "failures": [],
            "manifest_path": "outputs/manifest.json",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with patch("main.datetime.datetime") as mocked_datetime:
                    mocked_datetime.now.return_value.strftime.return_value = "20260211_000000"
                    with patch(
                        "main.run_story_generation_pipeline",
                        return_value=_fake_pipeline_result(tts_result=tts_result),
                    ) as mocked_pipeline:
                        with patch.object(sys, "argv", args):
                            main.main()

                pipeline_request = mocked_pipeline.call_args.kwargs["request"]
                self.assertTrue(pipeline_request.enable_tts)
                self.assertEqual(pipeline_request.tts_request_interval_sec, 10.0)
                self.assertEqual(pipeline_request.primary_lang, "Spanish")
                self.assertEqual(pipeline_request.secondary_lang, "French")
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
