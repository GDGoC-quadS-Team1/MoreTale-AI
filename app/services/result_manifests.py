from __future__ import annotations

from pathlib import Path
from typing import Any

from app.schemas.story import AssetStatus
from app.services.output_paths import (
    load_json,
    resolve_manifest_asset_path,
    slugify,
    to_outputs_url,
)

VALID_ASSET_STATUSES: set[str] = {
    "not_requested",
    "generated",
    "skipped_exists",
    "skipped_empty_text",
    "failed",
    "missing",
}


def normalize_asset_status(raw_status: Any) -> AssetStatus:
    status = str(raw_status or "").strip()
    if status in VALID_ASSET_STATUSES:
        return status  # type: ignore[return-value]
    return "missing"


def extract_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_audio_manifest(
    run_dir: Path,
    static_prefix: str | None = None,
) -> tuple[dict[tuple[int, str], dict[str, Any]], dict[str, Any] | None, str | None]:
    manifest_path = run_dir / "audio" / "manifest.json"
    if not manifest_path.is_file():
        return {}, None, None

    try:
        manifest = load_json(manifest_path)
    except Exception:
        return {}, None, to_outputs_url(manifest_path, prefix=static_prefix)

    entry_map: dict[tuple[int, str], dict[str, Any]] = {}
    entries = manifest.get("entries")
    if isinstance(entries, list):
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            page_number = extract_int(raw_entry.get("page_number"), default=-1)
            role = str(raw_entry.get("role", "")).strip().lower()
            if page_number < 1 or role not in {"primary", "secondary"}:
                continue
            entry_map[(page_number, role)] = {
                "status": normalize_asset_status(raw_entry.get("status")),
                "error": str(raw_entry.get("error", "")).strip() or None,
            }

    manifest_summary = {
        "total_tasks": extract_int(manifest.get("total_tasks"), default=0),
        "generated": extract_int(manifest.get("generated"), default=0),
        "skipped": extract_int(manifest.get("skipped"), default=0),
        "failed": extract_int(manifest.get("failed"), default=0),
    }
    return entry_map, manifest_summary, to_outputs_url(manifest_path, prefix=static_prefix)


def load_illustration_manifest(
    run_dir: Path,
    static_prefix: str | None = None,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None, str | None]:
    manifest_path = run_dir / "illustrations" / "manifest.json"
    if not manifest_path.is_file():
        return {}, None, None, None

    try:
        manifest = load_json(manifest_path)
    except Exception:
        return {}, None, None, to_outputs_url(manifest_path, prefix=static_prefix)

    entry_map: dict[int, dict[str, Any]] = {}
    cover_entry: dict[str, Any] | None = None
    entries = manifest.get("entries")
    if isinstance(entries, list):
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            status = normalize_asset_status(raw_entry.get("status"))
            error = str(raw_entry.get("error", "")).strip() or None
            path = str(raw_entry.get("path", "")).strip() or None
            asset_type = str(raw_entry.get("asset_type", "")).strip().lower()
            page_number = extract_int(raw_entry.get("page_number"), default=-1)

            if asset_type == "cover" or (
                page_number < 1 and path and Path(path).stem.lower() == "cover"
            ):
                cover_entry = {
                    "status": status,
                    "error": error,
                    "path": path,
                }
                continue

            if page_number < 1:
                continue
            entry_map[page_number] = {
                "status": status,
                "error": error,
                "path": path,
            }

    manifest_summary = {
        "total_tasks": extract_int(manifest.get("total_tasks"), default=0),
        "generated": extract_int(manifest.get("generated"), default=0),
        "skipped": extract_int(manifest.get("skipped"), default=0),
        "failed": extract_int(manifest.get("failed"), default=0),
    }
    return entry_map, cover_entry, manifest_summary, to_outputs_url(
        manifest_path, prefix=static_prefix
    )


def load_vocabulary_manifest(
    run_dir: Path,
) -> tuple[dict[tuple[int, str, str], dict[str, Any]], bool]:
    manifest_path = run_dir / "vocabulary" / "manifest.json"
    if not manifest_path.is_file():
        return {}, False

    try:
        manifest = load_json(manifest_path)
    except Exception:
        return {}, True

    entry_map: dict[tuple[int, str, str], dict[str, Any]] = {}
    entries = manifest.get("entries")
    if isinstance(entries, list):
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            page_number = extract_int(raw_entry.get("page_number"), default=-1)
            entry_id = slugify(str(raw_entry.get("entry_id", "")).strip())
            role = str(raw_entry.get("role", raw_entry.get("language", ""))).strip().lower()
            if page_number < 1 or not entry_id or role not in {"primary", "secondary"}:
                continue
            entry_map[(page_number, entry_id, role)] = {
                "status": normalize_asset_status(raw_entry.get("status")),
                "error": str(raw_entry.get("error", "")).strip() or None,
                "path": str(raw_entry.get("path", "")).strip() or None,
            }

    return entry_map, True


def find_manifest_asset_url(
    run_dir: Path,
    entry: dict[str, Any],
    static_prefix: str | None = None,
) -> str | None:
    raw_path = entry.get("path")
    if raw_path is None:
        return None
    resolved_path = resolve_manifest_asset_path(run_dir=run_dir, raw_path=str(raw_path))
    if resolved_path is None:
        return None
    return to_outputs_url(resolved_path, prefix=static_prefix)
