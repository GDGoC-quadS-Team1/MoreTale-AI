from google.genai import types


def stream_audio_bytes(
    client,
    model_name: str,
    contents: list[types.Content],
    config: types.GenerateContentConfig,
) -> tuple[bytes, str]:
    audio_chunks: list[bytes] = []
    mime_type: str | None = None
    for chunk in client.models.generate_content_stream(
        model=model_name,
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
