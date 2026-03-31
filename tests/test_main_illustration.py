import os
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    import main
except ModuleNotFoundError:  # pragma: no cover
    main = None


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


@unittest.skipIf(
    main is None,
    "CLI dependencies are not installed in this environment",
)
class TestMainIllustration(unittest.TestCase):
    def test_enable_illustration_requires_api_key(self):
        args = [
            "main.py",
            "--child_name",
            "Mina",
            "--primary_lang",
            "Korean",
            "--secondary_lang",
            "English",
            "--enable_illustration",
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

    def test_enable_illustration_uses_defaults(self):
        args = [
            "main.py",
            "--child_name",
            "Mina",
            "--primary_lang",
            "Spanish",
            "--secondary_lang",
            "French",
            "--enable_illustration",
        ]

        fake_illustration_instance = unittest.mock.Mock()
        fake_illustration_instance.generate_from_story.return_value = {
            "total_tasks": 25,
            "generated": 25,
            "skipped": 0,
            "failed": 0,
            "cover": {
                "enabled": True,
                "status": "generated",
                "error": None,
                "path": "outputs/illustrations/cover.png",
                "aspect_ratio": "5:4",
            },
            "manifest_path": "outputs/illustrations/manifest.json",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                with patch("main.StoryGenerator", _FakeStoryGenerator):
                    with patch.dict("main.os.environ", {"NANO_BANANA_KEY": "dummy-key"}, clear=True):
                        with patch("main.datetime.datetime") as mocked_datetime:
                            mocked_datetime.now.return_value.strftime.return_value = "20260211_000000"
                            with patch(
                                "main.IllustrationGenerator",
                                return_value=fake_illustration_instance,
                            ) as mocked_illustration:
                                with patch.object(sys, "argv", args):
                                    main.main()

                mocked_illustration.assert_called_once()
                self.assertEqual(
                    mocked_illustration.call_args.kwargs["model_name"],
                    "gemini-2.5-flash-image",
                )
                self.assertEqual(
                    mocked_illustration.call_args.kwargs["aspect_ratio"],
                    "1:1",
                )
                self.assertEqual(
                    mocked_illustration.call_args.kwargs["cover_aspect_ratio"],
                    "5:4",
                )
                self.assertEqual(
                    mocked_illustration.call_args.kwargs["request_interval_sec"],
                    1.0,
                )
                fake_illustration_instance.generate_from_story.assert_called_once()
                self.assertEqual(
                    fake_illustration_instance.generate_from_story.call_args.kwargs["skip_existing"],
                    False,
                )
                self.assertEqual(
                    fake_illustration_instance.generate_from_story.call_args.kwargs["generate_cover"],
                    True,
                )
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
