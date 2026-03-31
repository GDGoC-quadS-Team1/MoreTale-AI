import re

from generators.story.story_model import Story

from .illustration_prompt_utils import build_illustration_prefix


def _normalize_scene_snippet(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "")).strip()
    if not normalized:
        return ""

    first_sentence = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)[0].strip()
    if len(first_sentence) <= 180:
        return first_sentence

    return first_sentence[:177].rstrip(" ,.;:") + "..."


def build_cover_prompt(story: Story) -> str:
    illustration_prefix = (
        (story.illustration_prefix or "").strip()
        or build_illustration_prefix(story.image_style, story.main_character_design)
    )

    motif_indexes = [0, len(story.pages) // 2, len(story.pages) - 1]
    motif_snippets: list[str] = []
    for index in motif_indexes:
        if index < 0 or index >= len(story.pages):
            continue
        page = story.pages[index]
        snippet = _normalize_scene_snippet(
            (page.illustration_scene_prompt or "").strip()
            or (page.illustration_prompt or "").strip()
        )
        if snippet and snippet not in motif_snippets:
            motif_snippets.append(snippet)

    prompt_sections = [
        f"{illustration_prefix}, front cover illustration for a bilingual children's fairy tale".strip(
            ", "
        ),
        "Create a warm, inviting cover scene that captures the story's world and tone.",
        (
            "Show the main character clearly in the foreground with a confident, "
            "welcoming pose and expressive face."
        ),
        (
            "Use a clean, iconic composition with strong focal hierarchy, magical "
            "atmosphere, and rich environmental storytelling."
        ),
        (
            "Do not render any visible text, title, letters, Hangul, English words, "
            "logo, caption, typography, or writing on the cover."
        ),
    ]

    if motif_snippets:
        prompt_sections.append(
            "Blend in visual motifs from the story: " + " | ".join(motif_snippets) + "."
        )

    return " ".join(section.strip() for section in prompt_sections if section.strip())
