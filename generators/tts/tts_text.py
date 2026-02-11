import re


def build_tts_prompt(language_name: str, text: str) -> str:
    stripped_text = text.strip()
    normalized_language = language_name.strip() or "the requested language"
    instruction = f"Read in natural {normalized_language} children's storytelling tone."
    return f"{instruction}\n{stripped_text}"


def slugify_language_name(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "language"
