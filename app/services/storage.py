from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.story import AssetStatus

STORY_GLOB = "story_*.json"
PAGE_ASSET_PATTERN = re.compile(r"^page_(\d+)\.[^.]+$")
VALID_ASSET_STATUSES: set[str] = {
    "not_requested",
    "generated",
    "skipped_exists",
    "skipped_empty_text",
    "failed",
    "missing",
}


def ensure_outputs_dir() -> Path:
    outputs_dir = get_settings().outputs_dir
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def slugify_language_name(text: str) -> str:
    slug = slugify(text)
    return slug or "language"


def make_story_id(child_name: str, theme: str = "") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source = "-".join(part for part in [child_name.strip(), theme.strip()] if part)
    slug = slugify(source) or "story"
    base_story_id = f"{timestamp}_story_{slug}"

    outputs_dir = ensure_outputs_dir()
    story_id = base_story_id
    suffix = 1
    while (outputs_dir / story_id).exists():
        story_id = f"{base_story_id}-{suffix:02d}"
        suffix += 1
    return story_id


def get_run_dir(story_id: str) -> Path:
    return ensure_outputs_dir() / story_id


def write_story_json(story_id: str, story: Any, story_model: str) -> Path:
    run_dir = get_run_dir(story_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    story_json_path = run_dir / f"story_{story_model}.json"
    with story_json_path.open("w", encoding="utf-8") as file:
        file.write(story.model_dump_json(indent=4))
    return story_json_path


def find_story_json_path(story_id: str) -> Path | None:
    run_dir = get_run_dir(story_id)
    if not run_dir.is_dir():
        return None

    story_files = sorted(run_dir.glob(STORY_GLOB))
    if not story_files:
        return None
    return story_files[0]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def to_static_outputs_url(path: Path) -> str | None:
    outputs_dir = ensure_outputs_dir().resolve()
    try:
        rel_path = path.resolve().relative_to(outputs_dir)
    except Exception:
        return None
    prefix = get_settings().static_outputs_prefix
    return f"{prefix}/{rel_path.as_posix()}"


def resolve_manifest_asset_path(run_dir: Path, raw_path: str) -> Path | None:
    normalized = (raw_path or "").strip().replace("\\", "/")
    if not normalized:
        return None

    candidate = Path(normalized)
    outputs_dir = ensure_outputs_dir()
    candidates: list[Path] = []

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.append(run_dir / candidate)
        candidates.append(outputs_dir / candidate)
        if candidate.parts and candidate.parts[0] == outputs_dir.name:
            candidates.append(outputs_dir.parent / candidate)

    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def _normalize_asset_status(raw_status: Any) -> AssetStatus:
    status = str(raw_status or "").strip()
    if status in VALID_ASSET_STATUSES:
        return status  # type: ignore[return-value]
    return "missing"


def _extract_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _default_asset_summary(enabled: bool, total_tasks: int) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "total_tasks": total_tasks if enabled else 0,
        "generated": 0,
        "skipped": 0,
        "failed": 0,
        "manifest_url": None,
        "service_error": None,
    }


def _derive_asset_summary_from_statuses(
    statuses: list[AssetStatus],
    enabled: bool,
    manifest_url: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        return _default_asset_summary(enabled=False, total_tasks=0)

    generated = 0
    skipped = 0
    failed = 0
    for status in statuses:
        if status == "generated":
            generated += 1
        elif status in {"skipped_exists", "skipped_empty_text"}:
            skipped += 1
        elif status in {"failed", "missing"}:
            failed += 1

    return {
        "enabled": True,
        "total_tasks": len(statuses),
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "manifest_url": manifest_url,
        "service_error": None,
    }


def _load_audio_manifest(
    run_dir: Path,
) -> tuple[dict[tuple[int, str], dict[str, Any]], dict[str, Any] | None, str | None]:
    manifest_path = run_dir / "audio" / "manifest.json"
    if not manifest_path.is_file():
        return {}, None, None

    try:
        manifest = load_json(manifest_path)
    except Exception:
        return {}, None, to_static_outputs_url(manifest_path)

    entry_map: dict[tuple[int, str], dict[str, Any]] = {}
    entries = manifest.get("entries")
    if isinstance(entries, list):
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            page_number = _extract_int(raw_entry.get("page_number"), default=-1)
            role = str(raw_entry.get("role", "")).strip().lower()
            if page_number < 1 or role not in {"primary", "secondary"}:
                continue
            entry_map[(page_number, role)] = {
                "status": _normalize_asset_status(raw_entry.get("status")),
                "error": str(raw_entry.get("error", "")).strip() or None,
            }

    manifest_summary = {
        "total_tasks": _extract_int(manifest.get("total_tasks"), default=0),
        "generated": _extract_int(manifest.get("generated"), default=0),
        "skipped": _extract_int(manifest.get("skipped"), default=0),
        "failed": _extract_int(manifest.get("failed"), default=0),
    }
    return entry_map, manifest_summary, to_static_outputs_url(manifest_path)


def _load_illustration_manifest(
    run_dir: Path,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any] | None, str | None]:
    manifest_path = run_dir / "illustrations" / "manifest.json"
    if not manifest_path.is_file():
        return {}, None, None

    try:
        manifest = load_json(manifest_path)
    except Exception:
        return {}, None, to_static_outputs_url(manifest_path)

    entry_map: dict[int, dict[str, Any]] = {}
    entries = manifest.get("entries")
    if isinstance(entries, list):
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            page_number = _extract_int(raw_entry.get("page_number"), default=-1)
            if page_number < 1:
                continue
            entry_map[page_number] = {
                "status": _normalize_asset_status(raw_entry.get("status")),
                "error": str(raw_entry.get("error", "")).strip() or None,
                "path": str(raw_entry.get("path", "")).strip() or None,
            }

    manifest_summary = {
        "total_tasks": _extract_int(manifest.get("total_tasks"), default=0),
        "generated": _extract_int(manifest.get("generated"), default=0),
        "skipped": _extract_int(manifest.get("skipped"), default=0),
        "failed": _extract_int(manifest.get("failed"), default=0),
    }
    return entry_map, manifest_summary, to_static_outputs_url(manifest_path)


def _find_illustration_url_from_entry(run_dir: Path, entry: dict[str, Any]) -> str | None:
    raw_path = entry.get("path")
    if raw_path is None:
        return None
    resolved_path = resolve_manifest_asset_path(run_dir=run_dir, raw_path=str(raw_path))
    if resolved_path is None:
        return None
    return to_static_outputs_url(resolved_path)


def _first_existing_illustration_url(run_dir: Path, page_number: int) -> str | None:
    illustrations_dir = run_dir / "illustrations"
    if not illustrations_dir.is_dir():
        return None
    for file_path in sorted(illustrations_dir.glob(f"page_{page_number:02d}.*")):
        if file_path.is_file() and file_path.stat().st_size > 0:
            return to_static_outputs_url(file_path)
    return None


def build_story_result_payload(
    story_id: str,
    include_tts: bool,
    include_illustration: bool,
    job_status: str,
    service_errors: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    run_dir = get_run_dir(story_id)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run not found: {story_id}")

    story_json_path = find_story_json_path(story_id)
    if story_json_path is None:
        raise FileNotFoundError(f"story json not found for run: {story_id}")

    story_json_url = to_static_outputs_url(story_json_path)
    story = load_json(story_json_path)
    pages = story.get("pages")
    if not isinstance(pages, list):
        raise ValueError("story json is missing a valid 'pages' list")

    outputs_dir = ensure_outputs_dir()
    static_prefix = get_settings().static_outputs_prefix
    primary_language = str(story.get("primary_language", ""))
    secondary_language = str(story.get("secondary_language", ""))
    primary_slug = slugify_language_name(primary_language)
    secondary_slug = slugify_language_name(secondary_language)

    audio_entry_map, audio_manifest_summary, audio_manifest_url = _load_audio_manifest(run_dir)
    illustration_entry_map, illustration_manifest_summary, illustration_manifest_url = (
        _load_illustration_manifest(run_dir)
    )

    tts_statuses: list[AssetStatus] = []
    illustration_statuses: list[AssetStatus] = []

    payload_pages: list[dict[str, Any]] = []
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue

        raw_page_number = page.get("page_number", index + 1)
        try:
            page_number = int(raw_page_number)
        except (TypeError, ValueError):
            page_number = index + 1

        primary_rel = (
            Path(story_id) / "audio" / f"01_{primary_slug}" / f"page_{page_number:02d}_primary.wav"
        )
        secondary_rel = (
            Path(story_id) / "audio" / f"02_{secondary_slug}" / f"page_{page_number:02d}_secondary.wav"
        )
        primary_file = outputs_dir / primary_rel
        secondary_file = outputs_dir / secondary_rel

        has_primary_audio = primary_file.exists() and primary_file.is_file()
        has_secondary_audio = secondary_file.exists() and secondary_file.is_file()

        primary_manifest_entry = audio_entry_map.get((page_number, "primary"))
        secondary_manifest_entry = audio_entry_map.get((page_number, "secondary"))

        if not include_tts:
            primary_status: AssetStatus = "not_requested"
            secondary_status: AssetStatus = "not_requested"
            primary_error: str | None = None
            secondary_error: str | None = None
        else:
            if primary_manifest_entry is not None:
                primary_status = primary_manifest_entry["status"]
                primary_error = primary_manifest_entry.get("error")
            elif has_primary_audio:
                primary_status = "generated"
                primary_error = None
            else:
                primary_status = "missing"
                primary_error = None

            if secondary_manifest_entry is not None:
                secondary_status = secondary_manifest_entry["status"]
                secondary_error = secondary_manifest_entry.get("error")
            elif has_secondary_audio:
                secondary_status = "generated"
                secondary_error = None
            else:
                secondary_status = "missing"
                secondary_error = None

        tts_statuses.extend([primary_status, secondary_status])

        illustration_entry = illustration_entry_map.get(page_number)
        if not include_illustration:
            illustration_status: AssetStatus = "not_requested"
            illustration_error: str | None = None
            illustration_url = None
        else:
            illustration_url = None
            if illustration_entry is not None:
                illustration_status = illustration_entry["status"]
                illustration_error = illustration_entry.get("error")
                illustration_url = _find_illustration_url_from_entry(run_dir, illustration_entry)
            else:
                illustration_url = _first_existing_illustration_url(run_dir, page_number)
                if illustration_url:
                    illustration_status = "generated"
                    illustration_error = None
                else:
                    illustration_status = "missing"
                    illustration_error = None

        illustration_statuses.append(illustration_status)

        payload_pages.append(
            {
                "page_number": page_number,
                "text_primary": str(page.get("text_primary", "")),
                "text_secondary": str(page.get("text_secondary", "")),
                "audio_primary_url": (
                    f"{static_prefix}/{primary_rel.as_posix()}" if has_primary_audio else None
                ),
                "audio_secondary_url": (
                    f"{static_prefix}/{secondary_rel.as_posix()}" if has_secondary_audio else None
                ),
                "illustration_url": illustration_url,
                "audio_primary_status": primary_status,
                "audio_primary_error": primary_error,
                "audio_secondary_status": secondary_status,
                "audio_secondary_error": secondary_error,
                "illustration_status": illustration_status,
                "illustration_error": illustration_error,
                "has_primary_audio": has_primary_audio,
                "has_secondary_audio": has_secondary_audio,
                "has_illustration": bool(illustration_url),
                "illustration_prompt": str(page.get("illustration_prompt", "")),
                "illustration_scene_prompt": str(page.get("illustration_scene_prompt", "")),
            }
        )

    tts_summary = _default_asset_summary(enabled=include_tts, total_tasks=len(tts_statuses))
    if include_tts:
        if audio_manifest_summary is not None:
            tts_summary.update(audio_manifest_summary)
            tts_summary["enabled"] = True
            tts_summary["manifest_url"] = audio_manifest_url
            missing_tts_count = sum(1 for status in tts_statuses if status == "missing")
            if missing_tts_count > 0:
                tts_summary["failed"] = int(tts_summary["failed"]) + missing_tts_count
                if int(tts_summary["total_tasks"]) < len(tts_statuses):
                    tts_summary["total_tasks"] = len(tts_statuses)
        else:
            tts_summary = _derive_asset_summary_from_statuses(
                statuses=tts_statuses,
                enabled=True,
                manifest_url=audio_manifest_url,
            )

    illustration_summary = _default_asset_summary(
        enabled=include_illustration,
        total_tasks=len(illustration_statuses),
    )
    if include_illustration:
        if illustration_manifest_summary is not None:
            illustration_summary.update(illustration_manifest_summary)
            illustration_summary["enabled"] = True
            illustration_summary["manifest_url"] = illustration_manifest_url
            missing_illustration_count = sum(
                1 for status in illustration_statuses if status == "missing"
            )
            if missing_illustration_count > 0:
                illustration_summary["failed"] = (
                    int(illustration_summary["failed"]) + missing_illustration_count
                )
                if int(illustration_summary["total_tasks"]) < len(illustration_statuses):
                    illustration_summary["total_tasks"] = len(illustration_statuses)
        else:
            illustration_summary = _derive_asset_summary_from_statuses(
                statuses=illustration_statuses,
                enabled=True,
                manifest_url=illustration_manifest_url,
            )

    tts_service_error = (service_errors or {}).get("tts")
    illustration_service_error = (service_errors or {}).get("illustrations")
    tts_summary["service_error"] = tts_service_error
    illustration_summary["service_error"] = illustration_service_error

    has_partial_failures = bool(
        (include_tts and (tts_summary["failed"] > 0 or tts_service_error))
        or (
            include_illustration
            and (illustration_summary["failed"] > 0 or illustration_service_error)
        )
    )

    return {
        "id": story_id,
        "status": job_status,
        "story_json_url": story_json_url,
        "assets": {
            "tts": tts_summary,
            "illustrations": illustration_summary,
            "has_partial_failures": has_partial_failures,
        },
        "meta": {
            "title_primary": str(story.get("title_primary", "")),
            "title_secondary": str(story.get("title_secondary", "")),
            "primary_language": primary_language,
            "secondary_language": secondary_language,
            "page_count": len(payload_pages),
        },
        "pages": payload_pages,
    }
