import time

from google.genai import types


def _safe_chunk_text(chunk) -> str:
    text = getattr(chunk, "text", "")
    return text if isinstance(text, str) else ""


class ImageGenerationClient:
    def __init__(
        self,
        client,
        model_name: str,
        aspect_ratio: str,
        request_interval_sec: float,
    ):
        self.client = client
        self.model_name = model_name
        self.aspect_ratio = aspect_ratio
        self.request_interval_sec = max(0.0, request_interval_sec)
        self._last_request_time: float | None = None

    def _build_config(self) -> types.GenerateContentConfig:
        image_config = types.ImageConfig(aspect_ratio=self.aspect_ratio)
        return types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=image_config,
        )

    def _enforce_rate_limit(self) -> None:
        if self._last_request_time is None:
            return
        elapsed = time.monotonic() - self._last_request_time
        wait_sec = self.request_interval_sec - elapsed
        if wait_sec > 0:
            time.sleep(wait_sec)

    def generate_image_bytes(self, prompt: str) -> tuple[bytes, str]:
        self._enforce_rate_limit()
        self._last_request_time = time.monotonic()

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
        ]
        config = self._build_config()
        images: list[tuple[bytes, str]] = []
        text_messages: list[str] = []

        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config,
        ):
            if not chunk.parts:
                chunk_text = _safe_chunk_text(chunk).strip()
                if chunk_text:
                    text_messages.append(chunk_text)
                continue

            for part in chunk.parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and inline_data.data:
                    mime_type = inline_data.mime_type or "image/png"
                    images.append((inline_data.data, mime_type))
                    continue

                chunk_text = _safe_chunk_text(chunk).strip()
                if chunk_text:
                    text_messages.append(chunk_text)

        if not images:
            reason = " | ".join(msg for msg in text_messages if msg) or "no image parts found"
            raise ValueError(f"No image data returned from image model: {reason}")

        return images[0]

