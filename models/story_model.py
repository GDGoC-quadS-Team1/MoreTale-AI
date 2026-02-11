from pydantic import BaseModel, Field, field_validator
from typing import List

class Page(BaseModel):
    page_number: int = Field(..., description="Page number from 1 to 32")
    text_primary: str = Field(..., description="Story text in the primary language (Child's context)")
    text_secondary: str = Field(..., description="Story text in the secondary language (Parent's context)")
    illustration_prompt: str = Field(..., description="Detailed description for an AI image generator. MUST include the character's visual features defined in the Story class.")
    sound_effects: List[str] = Field(..., description="List of onomatopoeia words used in this page")

class Story(BaseModel):
    title_primary: str = Field(..., description="Title in primary language")
    title_secondary: str = Field(..., description="Title in secondary language")
    author_name: str = Field(..., description="Name of the author (AI or Child's name)")
    
    # New fields for Image Consistency
    image_style: str = Field(..., description="The consistent art style for the entire book (e.g., 'Soft watercolor', 'Vibrant digital art').")
    main_character_design: str = Field(..., description="Physical description of the main character (e.g., 'A 5-year-old Korean boy with short black hair, wearing a red t-shirt'). This MUST be used in every page's illustration prompt.")
    
    pages: List[Page] = Field(..., description="List of exactly 32 pages")

    @field_validator("pages")
    def check_page_count(cls, v):
        if len(v) != 32:
            raise ValueError(f"Story must have exactly 32 pages, but got {len(v)}")
        return v
