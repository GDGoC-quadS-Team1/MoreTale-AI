import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import main


class _FakeStory:
    title_primary = "Test Story"

    def model_dump_json(self, indent: int = 4) -> str:
        return '{"title_primary":"Test Story","pages":[]}'


class _FakeStoryGenerator:
    def __init__(self, model_name: str = "gemini-2.5-flash", include_style_guide: bool = False):
        self.model_name = model_name

    def generate_story(
        self,
        child_name: str,
        primary_lang: str,
        secondary_lang: str,
        theme: str,
        extra_prompt: str = "",
        child_age: int | None = None,
    ):
        return _FakeStory()


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
                with patch("main.StoryGenerator", _FakeStoryGenerator):
                    with patch.dict("main.os.environ", {}, clear=True):
                        with patch("main.datetime.datetime") as mocked_datetime:
                            mocked_datetime.now.return_value.strftime.return_value = "20260211_000000"
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

        fake_tts_instance = unittest.mock.Mock()
        fake_tts_instance.generate_book_audio.return_value = {
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
                with patch("main.StoryGenerator", _FakeStoryGenerator):
                    with patch.dict("main.os.environ", {"GEMINI_TTS_API_KEY": "dummy-key"}, clear=True):
                        with patch("main.datetime.datetime") as mocked_datetime:
                            mocked_datetime.now.return_value.strftime.return_value = "20260211_000000"
                            with patch("main.TTSGenerator", return_value=fake_tts_instance) as mocked_tts:
                                with patch.object(sys, "argv", args):
                                    main.main()

                mocked_tts.assert_called_once()
                self.assertEqual(mocked_tts.call_args.kwargs["request_interval_sec"], 10.0)
                fake_tts_instance.generate_book_audio.assert_called_once()
                self.assertEqual(
                    fake_tts_instance.generate_book_audio.call_args.kwargs["primary_language"],
                    "Spanish",
                )
                self.assertEqual(
                    fake_tts_instance.generate_book_audio.call_args.kwargs["secondary_language"],
                    "French",
                )
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
