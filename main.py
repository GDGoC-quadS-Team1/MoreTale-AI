from generators.story_generator import StoryGenerator
from models.story_model import Story
import sys
import os
import datetime
import re

def slugify(text):
    """Converts text to a safe filename slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

import argparse

def main():
    parser = argparse.ArgumentParser(description="Generate a bilingual fairy tale.")
    parser.add_argument("--child_name", required=True, help="Name of the child")
    parser.add_argument(
        "--child_age",
        type=int,
        default=None,
        help="Child age (optional, recommended for age-appropriate complexity)",
    )
    parser.add_argument("--primary_lang", required=True, help="Primary language (Child's context)")
    parser.add_argument("--secondary_lang", required=True, help="Secondary language (Parent's heritage)")
    parser.add_argument(
        "--theme",
        default="",
        help="Theme of the story (optional). If omitted, the model will auto-generate a theme.",
    )
    parser.add_argument("--extra_prompt", default="", help="Additional request or details")
    parser.add_argument("--model_name", default="gemini-2.5-flash", help="Gemini model name to use")
    parser.add_argument(
        "--include_style_guide",
        action="store_true",
        help="Include prompts/style_guide.txt in the system instruction (more detailed but longer prompt).",
    )
    
    args = parser.parse_args()

    print("Generating bilingual fairy tale...")
    
    generator = StoryGenerator(
        model_name=args.model_name,
        include_style_guide=args.include_style_guide,
    ) 
    
    try:
        story = generator.generate_story(
            child_name=args.child_name,
            child_age=args.child_age,
            primary_lang=args.primary_lang,
            secondary_lang=args.secondary_lang,
            theme=args.theme,
            extra_prompt=args.extra_prompt
        )
        
        print(f"Generated story: {story.title_primary}")
        
        # Create output directory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = slugify(story.title_primary)
        # Including generator info in directory name as requested
        output_dir = os.path.join("outputs", f"{timestamp}_story_{safe_title}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save story JSON
        filename = f"story_{generator.model_name}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(story.model_dump_json(indent=4))
            
        print(f"Story saved to: {filepath}")
        
    except Exception as e:
        print(f"Failed to generate story: {e}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
