import os
from typing import Callable

from generators.tts_manifest import build_manifest_entry, write_tts_manifest
from generators.tts_text import slugify_language_name


def _build_language_specs(
    audio_root: str,
    primary_language: str,
    secondary_language: str,
) -> tuple[tuple[str, str, str, str], tuple[str, str, str, str]]:
    primary_dir = os.path.join(audio_root, f"01_{slugify_language_name(primary_language)}")
    secondary_dir = os.path.join(
        audio_root, f"02_{slugify_language_name(secondary_language)}"
    )
    os.makedirs(primary_dir, exist_ok=True)
    os.makedirs(secondary_dir, exist_ok=True)
    return (
        ("primary", "text_primary", primary_language, primary_dir),
        ("secondary", "text_secondary", secondary_language, secondary_dir),
    )


def generate_book_audio_pipeline(
    story,
    output_dir: str,
    primary_language: str,
    secondary_language: str,
    skip_existing: bool,
    build_prompt_fn: Callable[[str, str], str],
    build_contents_fn: Callable[[str], object],
    stream_audio_fn: Callable[[object], tuple[bytes, str]],
    save_audio_fn: Callable[[str, bytes, str], None],
    retry_with_backoff_fn: Callable[[Callable[[], None], int, list[float], str], None],
) -> dict[str, int | list[str] | str]:
    audio_root = os.path.join(output_dir, "audio")
    language_specs = _build_language_specs(
        audio_root=audio_root,
        primary_language=primary_language,
        secondary_language=secondary_language,
    )

    generated = 0
    skipped = 0
    total_tasks = 0
    failures: list[str] = []
    manifest_entries: list[dict[str, str | int]] = []

    for page in story.pages:
        page_number = page.page_number
        for role_label, text_attr, language_name, lang_dir in language_specs:
            total_tasks += 1
            text = getattr(page, text_attr, "")
            label = f"page={page_number} lang={language_name} role={role_label}"
            file_path = os.path.join(lang_dir, f"page_{page_number:02d}_{role_label}.wav")

            if not text or not text.strip():
                skipped += 1
                print(f"SKIP {label} reason=empty_text")
                manifest_entries.append(
                    build_manifest_entry(
                        page_number=page_number,
                        language=language_name,
                        role=role_label,
                        path=file_path,
                        status="skipped_empty_text",
                    )
                )
                continue

            if skip_existing and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                skipped += 1
                print(f"SKIP {label} reason=exists path={file_path}")
                manifest_entries.append(
                    build_manifest_entry(
                        page_number=page_number,
                        language=language_name,
                        role=role_label,
                        path=file_path,
                        status="skipped_exists",
                    )
                )
                continue

            prompt = build_prompt_fn(language_name, text)
            contents = build_contents_fn(prompt)

            def run_single_request() -> None:
                audio_bytes, mime_type = stream_audio_fn(contents)
                save_audio_fn(file_path, audio_bytes, mime_type)

            try:
                retry_with_backoff_fn(run_single_request, 3, [2.0, 4.0, 8.0], label)
                generated += 1
                print(f"OK {label} path={file_path}")
                manifest_entries.append(
                    build_manifest_entry(
                        page_number=page_number,
                        language=language_name,
                        role=role_label,
                        path=file_path,
                        status="generated",
                    )
                )
            except Exception as error:
                failures.append(f"{label}: {error}")
                print(f"FAIL {label} error={error}")
                manifest_entries.append(
                    build_manifest_entry(
                        page_number=page_number,
                        language=language_name,
                        role=role_label,
                        path=file_path,
                        status="failed",
                        error=str(error),
                    )
                )

    manifest_path = write_tts_manifest(
        audio_root=audio_root,
        primary_language=primary_language,
        secondary_language=secondary_language,
        total_tasks=total_tasks,
        generated=generated,
        skipped=skipped,
        failed=len(failures),
        entries=manifest_entries,
    )

    return {
        "total_tasks": total_tasks,
        "generated": generated,
        "skipped": skipped,
        "failed": len(failures),
        "failures": failures,
        "manifest_path": manifest_path,
    }
