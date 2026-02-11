import struct


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


def normalize_to_wav_bytes(audio_bytes: bytes, mime_type: str) -> bytes:
    normalized = (mime_type or "").lower()
    if "wav" in normalized:
        return audio_bytes
    if normalized.startswith("audio/l") or "pcm" in normalized or not normalized:
        return convert_to_wav(audio_bytes, mime_type or "audio/L16;rate=24000")
    raise ValueError(f"Unsupported audio mime type for WAV output: {mime_type}")
