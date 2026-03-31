from .story_model import Page, Story, VocabularyEntry
from .story_prompts import StoryPrompt

__all__ = ["Page", "Story", "StoryPrompt", "StoryGenerator", "VocabularyEntry"]

try:
    from .story_generator import StoryGenerator
except ModuleNotFoundError:
    # Allow importing schema/prompt modules without runtime generator deps.
    StoryGenerator = None  # type: ignore[assignment]
