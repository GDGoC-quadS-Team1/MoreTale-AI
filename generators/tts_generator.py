import os
import json
import re
import struct
import time
from typing import Callable

from google import genai
from google.genai import types


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    bits_per_sample = 16
    rate = 24000

    parts = [part.strip() for part in (mime_type or "").split(";") if part.strip()]
    main_type = parts[0].lower() if parts else ""
    if main_type.startswith("audio/l"):
        try:
            bits_per_sample = int(main_type.split("l", 1)[1])
        except (ValueError, IndexError):
            pass

    for param in parts[1:]:
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


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
        if request_interval_sec <= 0:
            raise ValueError("request_interval_sec must be greater than 0.")

        self.client = client or genai.Client(api_key=api_key)
        self.model_name = model_name
        self.voice_name = voice_name
        self.temperature = temperature
        self.request_interval_sec = request_interval_sec
        self._last_request_time: float | None = None

    def _build_prompt(self, language_name: str, text: str) -> str:
        stripped_text = text.strip()
        normalized_language = language_name.strip() or "the requested language"
        instruction = (
            f"Read in natural {normalized_language} children's storytelling tone."
        )
        return f"{instruction}\n{stripped_text}"

    @staticmethod
    def _slugify_language_name(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return slug or "language"

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
        if self._last_request_time is None:
            return
        elapsed = time.monotonic() - self._last_request_time
        remaining = self.request_interval_sec - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _retry_with_backoff(
        self,
        func: Callable[[], None],
        attempts: int = 3,
        backoff: list[float] | None = None,
        context: str = "",
    ) -> None:
        waits = backoff or [2.0, 4.0, 8.0]
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                func()
                return
            except Exception as error:
                last_error = error
                if attempt == attempts:
                    break
                wait = waits[min(attempt - 1, len(waits) - 1)]
                print(
                    f"RETRY {context} attempt={attempt}/{attempts} "
                    f"error={error} wait={wait:.1f}s"
                )
                time.sleep(wait)
        if last_error is not None:
            raise last_error

    def _stream_audio_bytes(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> tuple[bytes, str]:
        self._enforce_rate_limit()
        self._last_request_time = time.monotonic()

        audio_chunks: list[bytes] = []
        mime_type: str | None = None
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config,
        ):
            if not chunk.parts:
                continue
            for part in chunk.parts:
                inline_data = getattr(part, "inline_data", None)
                if not inline_data or not inline_data.data:
                    continue
                current_mime_type = inline_data.mime_type or ""
                if mime_type is None:
                    mime_type = current_mime_type
                elif current_mime_type and current_mime_type != mime_type:
                    raise ValueError(
                        f"Inconsistent mime type in stream: {mime_type} vs {current_mime_type}"
                    )
                audio_chunks.append(inline_data.data)

        if not audio_chunks:
            raise ValueError("No audio data returned from TTS API.")

        return b"".join(audio_chunks), mime_type or "audio/L16;rate=24000"

    def _save_audio_file(self, file_path: str, audio_bytes: bytes, mime_type: str) -> None:
        normalized = (mime_type or "").lower()
        if "wav" in normalized:
            wav_bytes = audio_bytes
        elif normalized.startswith("audio/l") or "pcm" in normalized or not normalized:
            wav_bytes = convert_to_wav(audio_bytes, mime_type or "audio/L16;rate=24000")
        else:
            raise ValueError(
                f"Unsupported audio mime type for WAV output: {mime_type}"
            )

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
        audio_root = os.path.join(output_dir, "audio")
        chosen_primary_language = (
            primary_language or getattr(story, "primary_language", "") or "Primary"
        ).strip()
        chosen_secondary_language = (
            secondary_language or getattr(story, "secondary_language", "") or "Secondary"
        ).strip()
        primary_dir = os.path.join(
            audio_root,
            f"01_{self._slugify_language_name(chosen_primary_language)}",
        )
        secondary_dir = os.path.join(
            audio_root,
            f"02_{self._slugify_language_name(chosen_secondary_language)}",
        )
        os.makedirs(primary_dir, exist_ok=True)
        os.makedirs(secondary_dir, exist_ok=True)

        language_specs = (
            ("primary", "text_primary", chosen_primary_language, primary_dir),
            ("secondary", "text_secondary", chosen_secondary_language, secondary_dir),
        )

        generated = 0
        skipped = 0
        total_tasks = 0
        failures: list[str] = []
        manifest_entries: list[dict[str, str | int]] = []
        config = self._build_config()

        for page in story.pages:
            page_number = page.page_number
            for role_label, text_attr, language_name, lang_dir in language_specs:
                total_tasks += 1
                text = getattr(page, text_attr, "")
                label = f"page={page_number} lang={language_name} role={role_label}"
                file_path = os.path.join(
                    lang_dir, f"page_{page_number:02d}_{role_label}.wav"
                )

                if not text or not text.strip():
                    skipped += 1
                    print(f"SKIP {label} reason=empty_text")
                    manifest_entries.append(
                        {
                            "page_number": page_number,
                            "language": language_name,
                            "role": role_label,
                            "path": file_path,
                            "status": "skipped_empty_text",
                        }
                    )
                    continue

                if skip_existing and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    skipped += 1
                    print(f"SKIP {label} reason=exists path={file_path}")
                    manifest_entries.append(
                        {
                            "page_number": page_number,
                            "language": language_name,
                            "role": role_label,
                            "path": file_path,
                            "status": "skipped_exists",
                        }
                    )
                    continue

                prompt = self._build_prompt(language_name, text)
                contents = [
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)],
                    ),
                ]

                def run_single_request() -> None:
                    audio_bytes, mime_type = self._stream_audio_bytes(
                        contents=contents,
                        config=config,
                    )
                    self._save_audio_file(
                        file_path=file_path,
                        audio_bytes=audio_bytes,
                        mime_type=mime_type,
                    )

                try:
                    self._retry_with_backoff(
                        run_single_request,
                        attempts=3,
                        backoff=[2.0, 4.0, 8.0],
                        context=label,
                    )
                    generated += 1
                    print(f"OK {label} path={file_path}")
                    manifest_entries.append(
                        {
                            "page_number": page_number,
                            "language": language_name,
                            "role": role_label,
                            "path": file_path,
                            "status": "generated",
                        }
                    )
                except Exception as error:
                    failures.append(f"{label}: {error}")
                    print(f"FAIL {label} error={error}")
                    manifest_entries.append(
                        {
                            "page_number": page_number,
                            "language": language_name,
                            "role": role_label,
                            "path": file_path,
                            "status": "failed",
                            "error": str(error),
                        }
                    )

        manifest_path = os.path.join(audio_root, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "primary_language": chosen_primary_language,
                    "secondary_language": chosen_secondary_language,
                    "total_tasks": total_tasks,
                    "generated": generated,
                    "skipped": skipped,
                    "failed": len(failures),
                    "entries": manifest_entries,
                },
                file,
                indent=2,
                ensure_ascii=False,
            )

        return {
            "total_tasks": total_tasks,
            "generated": generated,
            "skipped": skipped,
            "failed": len(failures),
            "failures": failures,
            "manifest_path": manifest_path,
        }

