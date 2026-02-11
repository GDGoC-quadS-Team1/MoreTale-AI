import time
from typing import Callable

from google import genai
from google.genai import types

from generators.tts_audio import (
    convert_to_wav,
    normalize_to_wav_bytes,
    parse_audio_mime_type,
)
from generators.tts_pipeline import generate_book_audio_pipeline
from generators.tts_runtime import TTSRuntime
from generators.tts_stream import stream_audio_bytes
from generators.tts_text import build_tts_prompt


class TTSGenerator:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash-preview-tts",
        voice_name: str = "Achernar",
        temperature: float = 1.0,
        request_interval_sec: float = 10.0,
        client: genai.Client | None = None,
    ):
        if not api_key:
            raise ValueError("GEMINI_TTS_API_KEY environment variable not set.")

        self.client = client or genai.Client(api_key=api_key)
        self.model_name = model_name
        self.voice_name = voice_name
        self.temperature = temperature
        self.runtime = TTSRuntime(request_interval_sec=request_interval_sec)

    @property
    def _last_request_time(self) -> float | None:
        return self.runtime.last_request_time

    @_last_request_time.setter
    def _last_request_time(self, value: float | None) -> None:
        self.runtime.last_request_time = value

    def _build_prompt(self, language_name: str, text: str) -> str:
        return build_tts_prompt(language_name=language_name, text=text)

    def _build_contents(self, prompt: str) -> list[types.Content]:
        return [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]

    def _build_config(self) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=self.temperature,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
        )

    def _enforce_rate_limit(self) -> None:
        self.runtime.enforce_rate_limit(
            monotonic_fn=time.monotonic,
            sleep_fn=time.sleep,
        )

    def _retry_with_backoff(
        self,
        func: Callable[[], None],
        attempts: int = 3,
        backoff: list[float] | None = None,
        context: str = "",
    ) -> None:
        self.runtime.run_with_retry(
            func=func,
            attempts=attempts,
            backoff=backoff,
            context=context,
            sleep_fn=time.sleep,
        )

    def _stream_audio_bytes(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> tuple[bytes, str]:
        self._enforce_rate_limit()
        self.runtime.mark_request_time(monotonic_fn=time.monotonic)
        return stream_audio_bytes(
            client=self.client,
            model_name=self.model_name,
            contents=contents,
            config=config,
        )

    def _save_audio_file(self, file_path: str, audio_bytes: bytes, mime_type: str) -> None:
        wav_bytes = normalize_to_wav_bytes(audio_bytes=audio_bytes, mime_type=mime_type)
        with open(file_path, "wb") as file:
            file.write(wav_bytes)

    def generate_book_audio(
        self,
        story,
        output_dir: str,
        primary_language: str | None = None,
        secondary_language: str | None = None,
        skip_existing: bool = True,
    ) -> dict[str, int | list[str] | str]:
        chosen_primary_language = (
            primary_language or getattr(story, "primary_language", "") or "Primary"
        ).strip()
        chosen_secondary_language = (
            secondary_language or getattr(story, "secondary_language", "") or "Secondary"
        ).strip()
        config = self._build_config()

        def stream_with_config(contents: list[types.Content]) -> tuple[bytes, str]:
            return self._stream_audio_bytes(contents=contents, config=config)

        return generate_book_audio_pipeline(
            story=story,
            output_dir=output_dir,
            primary_language=chosen_primary_language,
            secondary_language=chosen_secondary_language,
            skip_existing=skip_existing,
            build_prompt_fn=self._build_prompt,
            build_contents_fn=self._build_contents,
            stream_audio_fn=stream_with_config,
            save_audio_fn=self._save_audio_file,
            retry_with_backoff_fn=self._retry_with_backoff,
        )
