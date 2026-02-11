def build_illustration_prefix(image_style: str, main_character_design: str) -> str:
    image_style_clean = (image_style or "").strip().rstrip(",")
    main_character_design_clean = (main_character_design or "").strip()

    if not image_style_clean:
        return main_character_design_clean
    if not main_character_design_clean:
        return image_style_clean
    return f"{image_style_clean}, {main_character_design_clean}"


def _strip_leading_separators(text: str) -> str:
    return (text or "").lstrip(" \t\r\n,;:.-—–")


def split_scene_prompt(
    illustration_prefix: str, main_character_design: str, full_prompt: str
) -> tuple[str, str]:
    """
    Splits a full illustration prompt into a page-specific scene prompt by removing:
    1) the exact illustration_prefix at the beginning, or
    2) the main_character_design substring (taking everything after it).

    Returns: (scene_prompt, method) where method is one of: "prefix", "design", "fallback", "empty".
    """
    if not full_prompt or not full_prompt.strip():
        return "", "empty"

    full = full_prompt.strip()
    prefix = (illustration_prefix or "").strip()
    design = (main_character_design or "").strip()

    if prefix and full.startswith(prefix):
        scene = _strip_leading_separators(full[len(prefix) :])
        return scene, "prefix"

    if design:
        design_index = full.find(design)
        if design_index != -1:
            scene = _strip_leading_separators(full[design_index + len(design) :])
            return scene, "design"

    return full, "fallback"

