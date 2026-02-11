import json
import os


def build_manifest_entry(
    page_number: int,
    language: str,
    role: str,
    path: str,
    status: str,
    error: str | None = None,
) -> dict[str, str | int]:
    entry: dict[str, str | int] = {
        "page_number": page_number,
        "language": language,
        "role": role,
        "path": path,
        "status": status,
    }
    if error is not None:
        entry["error"] = error
    return entry


def write_tts_manifest(
    audio_root: str,
    primary_language: str,
    secondary_language: str,
    total_tasks: int,
    generated: int,
    skipped: int,
    failed: int,
    entries: list[dict[str, str | int]],
) -> str:
    manifest_path = os.path.join(audio_root, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "primary_language": primary_language,
                "secondary_language": secondary_language,
                "total_tasks": total_tasks,
                "generated": generated,
                "skipped": skipped,
                "failed": failed,
                "entries": entries,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )
    return manifest_path
