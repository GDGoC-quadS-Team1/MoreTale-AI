import json
import mimetypes
from pathlib import Path


def pick_image_extension(mime_type: str | None) -> str:
    guessed = mimetypes.guess_extension(mime_type or "")
    if guessed:
        return guessed
    return ".png"


def find_existing_page_asset(illustration_dir: Path, page_number: int) -> str | None:
    page_glob = list(illustration_dir.glob(f"page_{page_number:02d}.*"))
    for path in page_glob:
        if path.exists() and path.stat().st_size > 0:
            return str(path)
    return None


def write_manifest(
    manifest_path: Path,
    model_name: str,
    aspect_ratio: str,
    total_tasks: int,
    generated: int,
    skipped: int,
    failed: int,
    entries: list[dict[str, str | int]],
) -> None:
    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "model_name": model_name,
                "aspect_ratio": aspect_ratio,
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

