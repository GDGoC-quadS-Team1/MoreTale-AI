import argparse
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.story_model import Story
from prompts.illustration_prompt_utils import build_illustration_prefix


load_dotenv()


def _resolve_api_key() -> str:
    for env_name in (
        "GEMINI_ILLUSTRATION_API_KEY",
        "GEMINI_IMAGE_API_KEY",
        "GEMINI_STORY_API_KEY",
        "GEMINI_API_KEY",
    ):
        key = os.getenv(env_name)
        if key:
            return key
    raise ValueError(
        "No Gemini API key found. Set one of: "
        "GEMINI_ILLUSTRATION_API_KEY, GEMINI_IMAGE_API_KEY, GEMINI_STORY_API_KEY, GEMINI_API_KEY."
    )


def _pick_image_extension(mime_type: str | None) -> str:
    guessed = mimetypes.guess_extension(mime_type or "")
    if guessed:
        return guessed
    return ".png"


def _safe_chunk_text(chunk) -> str:
    text = getattr(chunk, "text", "")
    return text if isinstance(text, str) else ""


class IllustrationGenerator:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-flash-image",
        aspect_ratio: str = "16:9",
        request_interval_sec: float = 1.0,
        client: genai.Client | None = None,
    ):
        self.client = client or genai.Client(api_key=api_key or _resolve_api_key())
        self.model_name = model_name
        self.aspect_ratio = aspect_ratio
        self.request_interval_sec = max(0.0, request_interval_sec)
        self._last_request_time: float | None = None

    @staticmethod
    def load_story(story_json_path: str) -> Story:
        with open(story_json_path, "r", encoding="utf-8") as file:
            return Story.model_validate_json(file.read())

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

    @staticmethod
    def _build_page_prompt(story: Story, page) -> tuple[str, str]:
        illustration_prefix = (
            (story.illustration_prefix or "").strip()
            or build_illustration_prefix(story.image_style, story.main_character_design)
        )
        full_prompt = (page.illustration_prompt or "").strip()
        scene_prompt = (page.illustration_scene_prompt or "").strip()

        if scene_prompt:
            scene_focused_prompt = ", ".join(
                part for part in (illustration_prefix, scene_prompt) if part
            )
            if full_prompt:
                combined_prompt = (
                    f"{scene_focused_prompt}\n\n"
                    f"Reference details for consistency: {full_prompt}"
                )
            else:
                combined_prompt = scene_focused_prompt
            return combined_prompt, "scene_plus_full"

        if full_prompt:
            return full_prompt, "full_only"

        if illustration_prefix:
            return illustration_prefix, "prefix_only"

        raise ValueError(f"page={page.page_number} has no illustration prompt text.")

    def _generate_image_bytes(self, prompt: str) -> tuple[bytes, str]:
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

    def generate_from_story(
        self,
        story: Story,
        output_dir: str,
        skip_existing: bool = True,
    ) -> dict[str, int | list[dict[str, str | int]] | str]:
        illustration_dir = Path(output_dir) / "illustrations"
        illustration_dir.mkdir(parents=True, exist_ok=True)

        generated = 0
        skipped = 0
        failed = 0
        entries: list[dict[str, str | int]] = []

        for page in story.pages:
            page_number = page.page_number
            page_glob = list(illustration_dir.glob(f"page_{page_number:02d}.*"))
            if skip_existing and any(path.exists() and path.stat().st_size > 0 for path in page_glob):
                skipped += 1
                existing_path = str(page_glob[0])
                print(f"SKIP page={page_number} reason=exists path={existing_path}")
                entries.append(
                    {
                        "page_number": page_number,
                        "status": "skipped_exists",
                        "path": existing_path,
                    }
                )
                continue

            try:
                prompt, prompt_mode = self._build_page_prompt(story=story, page=page)
                image_bytes, mime_type = self._generate_image_bytes(prompt=prompt)
                extension = _pick_image_extension(mime_type)
                image_path = illustration_dir / f"page_{page_number:02d}{extension}"

                with open(image_path, "wb") as file:
                    file.write(image_bytes)

                generated += 1
                print(f"OK page={page_number} path={image_path} mode={prompt_mode}")
                entries.append(
                    {
                        "page_number": page_number,
                        "status": "generated",
                        "path": str(image_path),
                        "prompt_mode": prompt_mode,
                    }
                )
            except Exception as error:
                failed += 1
                print(f"FAIL page={page_number} error={error}")
                entries.append(
                    {
                        "page_number": page_number,
                        "status": "failed",
                        "error": str(error),
                    }
                )

        manifest_path = illustration_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "model_name": self.model_name,
                    "aspect_ratio": self.aspect_ratio,
                    "total_tasks": len(story.pages),
                    "generated": generated,
                    "skipped": skipped,
                    "failed": failed,
                    "entries": entries,
                },
                file,
                indent=2,
                ensure_ascii=False,
            )

        return {
            "total_tasks": len(story.pages),
            "generated": generated,
            "skipped": skipped,
            "failed": failed,
            "manifest_path": str(manifest_path),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate page illustrations from a story JSON using "
            "illustration_prompt + illustration_scene_prompt."
        )
    )
    parser.add_argument(
        "--story_json",
        required=True,
        help="Path to story JSON file generated by this project.",
    )
    parser.add_argument(
        "--output_dir",
        default="",
        help="Output root directory. If omitted, uses the story JSON's parent directory.",
    )
    parser.add_argument(
        "--model_name",
        default="gemini-2.5-flash-image",
        help="Gemini image model name.",
    )
    parser.add_argument(
        "--aspect_ratio",
        default="16:9",
        help="Image aspect ratio (e.g. 16:9, 1:1, 3:4).",
    )
    parser.add_argument(
        "--request_interval_sec",
        type=float,
        default=1.0,
        help="Seconds between image requests.",
    )
    parser.add_argument(
        "--skip_existing",
        action="store_true",
        help="Skip pages if page_XX.* already exists in output illustrations directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    story_path = Path(args.story_json)
    if not story_path.exists():
        raise FileNotFoundError(f"Story JSON not found: {story_path}")

    output_dir = args.output_dir.strip() or str(story_path.parent)
    generator = IllustrationGenerator(
        model_name=args.model_name,
        aspect_ratio=args.aspect_ratio,
        request_interval_sec=args.request_interval_sec,
    )
    story = generator.load_story(str(story_path))
    result = generator.generate_from_story(
        story=story,
        output_dir=output_dir,
        skip_existing=args.skip_existing,
    )
    print(
        "Illustration summary: "
        f"total={result['total_tasks']} "
        f"generated={result['generated']} "
        f"skipped={result['skipped']} "
        f"failed={result['failed']} "
        f"manifest={result['manifest_path']}"
    )


if __name__ == "__main__":
    main()


