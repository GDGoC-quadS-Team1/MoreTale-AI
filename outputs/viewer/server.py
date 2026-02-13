#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


VIEWER_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = VIEWER_DIR.parent
RUN_GLOB = "*_story_*"
STORY_GLOB = "story_*.json"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
PAGE_ASSET_PATTERN = re.compile(r"^page_(\d+)\.[^.]+$")


def slugify_language_name(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "language"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def to_outputs_url(path: Path) -> str | None:
    try:
        rel_path = path.resolve().relative_to(OUTPUTS_DIR.resolve())
    except Exception:
        return None
    return f"/{rel_path.as_posix()}"


def resolve_manifest_asset_path(run_dir: Path, raw_path: str) -> Path | None:
    normalized = (raw_path or "").strip().replace("\\", "/")
    if not normalized:
        return None

    candidate = Path(normalized)
    candidates: list[Path] = []

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.append(run_dir / candidate)
        candidates.append(OUTPUTS_DIR / candidate)
        if candidate.parts and candidate.parts[0] == OUTPUTS_DIR.name:
            candidates.append(OUTPUTS_DIR.parent / candidate)

    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def load_illustration_url_map(run_dir: Path) -> dict[int, str]:
    illustrations_dir = run_dir / "illustrations"
    if not illustrations_dir.is_dir():
        return {}

    url_map: dict[int, str] = {}
    manifest_path = illustrations_dir / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = load_json(manifest_path)
            entries = manifest.get("entries")
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue

                    raw_page_number = entry.get("page_number")
                    raw_path = entry.get("path")
                    if raw_page_number is None or raw_path is None:
                        continue

                    try:
                        page_number = int(raw_page_number)
                    except (TypeError, ValueError):
                        continue

                    resolved_path = resolve_manifest_asset_path(
                        run_dir=run_dir,
                        raw_path=str(raw_path),
                    )
                    if resolved_path is None:
                        continue

                    illustration_url = to_outputs_url(resolved_path)
                    if illustration_url:
                        url_map[page_number] = illustration_url
        except Exception:
            # Fall back to file scan if manifest parsing fails.
            pass

    for file_path in sorted(illustrations_dir.glob("page_*.*")):
        if not file_path.is_file() or file_path.stat().st_size <= 0:
            continue

        match = PAGE_ASSET_PATTERN.fullmatch(file_path.name)
        if not match:
            continue

        page_number = int(match.group(1))
        if page_number in url_map:
            continue

        illustration_url = to_outputs_url(file_path)
        if illustration_url:
            url_map[page_number] = illustration_url

    return url_map


def iter_runs() -> list[dict]:
    runs: list[dict] = []
    for run_dir in sorted(
        [p for p in OUTPUTS_DIR.glob(RUN_GLOB) if p.is_dir()],
        key=lambda p: p.name,
        reverse=True,
    ):
        story_files = sorted(run_dir.glob(STORY_GLOB))
        if not story_files:
            continue

        story_path = story_files[0]
        title_primary = ""
        title_secondary = ""
        page_count = 0

        try:
            story = load_json(story_path)
            title_primary = str(story.get("title_primary", ""))
            title_secondary = str(story.get("title_secondary", ""))
            pages = story.get("pages") or []
            page_count = len(pages) if isinstance(pages, list) else 0
        except Exception:
            # Keep run discoverable even if metadata parsing fails.
            pass

        audio_root = run_dir / "audio"
        has_any_audio = audio_root.exists() and any(audio_root.rglob("*.wav"))
        illustration_root = run_dir / "illustrations"
        has_any_illustration = illustration_root.exists() and any(
            illustration_root.glob("page_*.*")
        )
        updated_at = datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(
            timespec="seconds"
        )

        runs.append(
            {
                "id": run_dir.name,
                "story_json": story_path.name,
                "title_primary": title_primary,
                "title_secondary": title_secondary,
                "page_count": page_count,
                "has_any_audio": has_any_audio,
                "has_any_illustration": has_any_illustration,
                "updated_at": updated_at,
            }
        )
    return runs


def find_run_dir(run_id: str) -> Path | None:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        return None

    if "_story_" not in run_id:
        return None

    run_dir = OUTPUTS_DIR / run_id
    if not run_dir.is_dir():
        return None

    if not list(run_dir.glob(STORY_GLOB)):
        return None

    return run_dir


def build_book_payload(run_id: str) -> dict:
    run_dir = find_run_dir(run_id)
    if run_dir is None:
        raise FileNotFoundError(f"run not found: {run_id}")

    story_files = sorted(run_dir.glob(STORY_GLOB))
    if not story_files:
        raise FileNotFoundError(f"story json not found for run: {run_id}")

    story = load_json(story_files[0])
    pages = story.get("pages")
    if not isinstance(pages, list):
        raise ValueError("story json is missing a valid 'pages' list")

    primary_language = str(story.get("primary_language", ""))
    secondary_language = str(story.get("secondary_language", ""))
    primary_slug = slugify_language_name(primary_language)
    secondary_slug = slugify_language_name(secondary_language)
    illustration_urls = load_illustration_url_map(run_dir=run_dir)

    payload_pages: list[dict] = []
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue

        raw_page_number = page.get("page_number", index + 1)
        try:
            page_number = int(raw_page_number)
        except (TypeError, ValueError):
            page_number = index + 1

        primary_rel = (
            f"{run_id}/audio/01_{primary_slug}/page_{page_number:02d}_primary.wav"
        )
        secondary_rel = (
            f"{run_id}/audio/02_{secondary_slug}/page_{page_number:02d}_secondary.wav"
        )

        primary_file = OUTPUTS_DIR / primary_rel
        secondary_file = OUTPUTS_DIR / secondary_rel

        has_primary_audio = primary_file.exists() and primary_file.is_file()
        has_secondary_audio = secondary_file.exists() and secondary_file.is_file()
        illustration_url = illustration_urls.get(page_number)

        payload_pages.append(
            {
                "page_number": page_number,
                "text_primary": str(page.get("text_primary", "")),
                "text_secondary": str(page.get("text_secondary", "")),
                "illustration_url": illustration_url,
                "has_illustration": bool(illustration_url),
                "illustration_prompt": str(page.get("illustration_prompt", "")),
                "illustration_scene_prompt": str(
                    page.get("illustration_scene_prompt", "")
                ),
                "audio_primary_url": f"/{primary_rel}" if has_primary_audio else None,
                "audio_secondary_url": (
                    f"/{secondary_rel}" if has_secondary_audio else None
                ),
                "has_primary_audio": has_primary_audio,
                "has_secondary_audio": has_secondary_audio,
            }
        )

    return {
        "run_id": run_id,
        "meta": {
            "title_primary": str(story.get("title_primary", "")),
            "title_secondary": str(story.get("title_secondary", "")),
            "primary_language": primary_language,
            "secondary_language": secondary_language,
            "page_count": len(payload_pages),
        },
        "pages": payload_pages,
    }


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUTS_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_response(302)
            self.send_header("Location", "/viewer/")
            self.end_headers()
            return

        if parsed.path == "/api/runs":
            self._send_json(200, {"runs": iter_runs()})
            return

        if parsed.path == "/api/book":
            params = parse_qs(parsed.query)
            run_id = (params.get("run") or [""])[0].strip()
            if not run_id:
                self._send_json(400, {"error": "query parameter 'run' is required"})
                return

            try:
                payload = build_book_payload(run_id)
            except FileNotFoundError as error:
                self._send_json(404, {"error": str(error)})
                return
            except Exception as error:
                self._send_json(500, {"error": str(error)})
                return

            self._send_json(200, payload)
            return

        super().do_GET()

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MoreTale outputs viewer server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=8787, type=int, help="Port to bind")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ViewerHandler)
    print(f"Serving viewer at http://{args.host}:{args.port}/viewer/")
    print(f"Serving outputs from {OUTPUTS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
