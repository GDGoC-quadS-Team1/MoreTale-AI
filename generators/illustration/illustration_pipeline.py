from pathlib import Path

from google import genai

from generators.story.story_model import Story

from .illustration_env import resolve_api_key
from .illustration_image_client import ImageGenerationClient
from .illustration_prompt_builder import build_page_prompt
from .illustration_storage import (
    find_existing_page_asset,
    pick_image_extension,
    write_manifest,
)


class IllustrationGenerator:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-flash-image",
        aspect_ratio: str = "16:9",
        request_interval_sec: float = 1.0,
        client: genai.Client | None = None,
    ):
        self.client = client or genai.Client(api_key=api_key or resolve_api_key())
        self.model_name = model_name
        self.aspect_ratio = aspect_ratio
        self.request_interval_sec = max(0.0, request_interval_sec)
        self.image_client = ImageGenerationClient(
            client=self.client,
            model_name=self.model_name,
            aspect_ratio=self.aspect_ratio,
            request_interval_sec=self.request_interval_sec,
        )

    @staticmethod
    def load_story(story_json_path: str) -> Story:
        with open(story_json_path, "r", encoding="utf-8") as file:
            return Story.model_validate_json(file.read())

    @staticmethod
    def _build_page_prompt(story: Story, page) -> tuple[str, str]:
        return build_page_prompt(story=story, page=page)

    def _generate_image_bytes(self, prompt: str) -> tuple[bytes, str]:
        return self.image_client.generate_image_bytes(prompt=prompt)

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
            if skip_existing:
                existing_path = find_existing_page_asset(
                    illustration_dir=illustration_dir,
                    page_number=page_number,
                )
                if existing_path:
                    skipped += 1
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
                extension = pick_image_extension(mime_type)
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
        write_manifest(
            manifest_path=manifest_path,
            model_name=self.model_name,
            aspect_ratio=self.aspect_ratio,
            total_tasks=len(story.pages),
            generated=generated,
            skipped=skipped,
            failed=failed,
            entries=entries,
        )

        return {
            "total_tasks": len(story.pages),
            "generated": generated,
            "skipped": skipped,
            "failed": failed,
            "manifest_path": str(manifest_path),
        }
