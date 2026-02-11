import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from generators.tts_generator import TTSGenerator, convert_to_wav, parse_audio_mime_type


def _make_chunk(data: bytes, mime_type: str):
    inline_data = SimpleNamespace(data=data, mime_type=mime_type)
    part = SimpleNamespace(inline_data=inline_data)
    return SimpleNamespace(parts=[part])


def _make_story(pages):
    return SimpleNamespace(
        primary_language="Korean",
        secondary_language="English",
        pages=pages,
    )


class TestTTSHelpers(unittest.TestCase):
    def test_parse_audio_mime_type(self):
        parsed = parse_audio_mime_type("audio/L16;rate=24000")
        self.assertEqual(parsed["bits_per_sample"], 16)
        self.assertEqual(parsed["rate"], 24000)

    def test_convert_to_wav_adds_header(self):
        raw_audio = b"\x00\x01" * 100
        wav_audio = convert_to_wav(raw_audio, "audio/L16;rate=24000")
        self.assertTrue(wav_audio.startswith(b"RIFF"))
        self.assertGreater(len(wav_audio), len(raw_audio))


class TestTTSGenerator(unittest.TestCase):
    def test_stream_audio_bytes_merges_multiple_chunks(self):
        chunks = [
            _make_chunk(b"hello", "audio/L16;rate=24000"),
            _make_chunk(b"world", "audio/L16;rate=24000"),
        ]
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=Mock(return_value=chunks))
        )
        generator = TTSGenerator(api_key="dummy", client=client)

        audio_bytes, mime_type = generator._stream_audio_bytes(contents=[], config=None)

        self.assertEqual(audio_bytes, b"helloworld")
        self.assertEqual(mime_type, "audio/L16;rate=24000")

    def test_skip_existing_file(self):
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=Mock(return_value=[]))
        )
        generator = TTSGenerator(api_key="dummy", client=client)

        pages = [
            SimpleNamespace(page_number=1, text_primary="첫 문장", text_secondary="First line"),
            SimpleNamespace(page_number=2, text_primary="둘째 문장", text_secondary="Second line"),
        ]
        story = _make_story(pages)

        with tempfile.TemporaryDirectory() as tmp_dir:
            existing_path = os.path.join(
                tmp_dir,
                "audio",
                "01_korean",
                "page_01_primary.wav",
            )
            os.makedirs(os.path.dirname(existing_path), exist_ok=True)
            with open(existing_path, "wb") as file:
                file.write(b"already-done")

            with patch.object(
                generator,
                "_stream_audio_bytes",
                return_value=(b"\x00\x01" * 100, "audio/L16;rate=24000"),
            ):
                with patch("generators.tts_generator.time.sleep"):
                    result = generator.generate_book_audio(
                        story=story,
                        output_dir=tmp_dir,
                        skip_existing=True,
                    )

            self.assertEqual(result["total_tasks"], 4)
            self.assertEqual(result["generated"], 3)
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["failed"], 0)
            self.assertTrue(os.path.exists(result["manifest_path"]))

    def test_enforce_rate_limit_waits_remaining_time(self):
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=Mock(return_value=[]))
        )
        generator = TTSGenerator(api_key="dummy", request_interval_sec=10.0, client=client)
        generator._last_request_time = 10.0

        with patch("generators.tts_generator.time.monotonic", return_value=13.0):
            with patch("generators.tts_generator.time.sleep") as mocked_sleep:
                generator._enforce_rate_limit()

        mocked_sleep.assert_called_once_with(7.0)

    def test_retry_then_successful_generation(self):
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=Mock(return_value=[]))
        )
        generator = TTSGenerator(api_key="dummy", client=client)
        story = _make_story(
            [SimpleNamespace(page_number=1, text_primary="한글", text_secondary="English")]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(
                generator,
                "_stream_audio_bytes",
                side_effect=[
                    RuntimeError("temporary failure"),
                    (b"\x00\x01" * 100, "audio/L16;rate=24000"),
                    (b"\x00\x01" * 100, "audio/L16;rate=24000"),
                ],
            ) as mocked_stream:
                with patch("generators.tts_generator.time.sleep"):
                    result = generator.generate_book_audio(
                        story=story,
                        output_dir=tmp_dir,
                        skip_existing=True,
                    )

            self.assertEqual(result["generated"], 2)
            self.assertEqual(result["failed"], 0)
            self.assertEqual(mocked_stream.call_count, 3)
            self.assertTrue(
                os.path.exists(
                    os.path.join(tmp_dir, "audio", "01_korean", "page_01_primary.wav")
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(tmp_dir, "audio", "02_english", "page_01_secondary.wav")
                )
            )

    def test_dynamic_language_directories(self):
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content_stream=Mock(return_value=[]))
        )
        generator = TTSGenerator(api_key="dummy", client=client)
        story = SimpleNamespace(
            primary_language="Spanish",
            secondary_language="French",
            pages=[
                SimpleNamespace(
                    page_number=1,
                    text_primary="Hola",
                    text_secondary="Bonjour",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(
                generator,
                "_stream_audio_bytes",
                return_value=(b"\x00\x01" * 100, "audio/L16;rate=24000"),
            ):
                with patch("generators.tts_generator.time.sleep"):
                    result = generator.generate_book_audio(
                        story=story,
                        output_dir=tmp_dir,
                        skip_existing=True,
                    )

            self.assertEqual(result["generated"], 2)
            self.assertTrue(
                os.path.exists(
                    os.path.join(tmp_dir, "audio", "01_spanish", "page_01_primary.wav")
                )
            )
            self.assertTrue(
                os.path.exists(
                    os.path.join(tmp_dir, "audio", "02_french", "page_01_secondary.wav")
                )
            )


if __name__ == "__main__":
    unittest.main()
