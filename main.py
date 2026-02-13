from generators.story.story_generator import StoryGenerator
from generators.tts.tts_generator import TTSGenerator
from generators.illustration.illustration_pipeline import IllustrationGenerator
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
    parser.add_argument(
        "--enable_tts",
        action="store_true",
        help="Generate page-level audiobook WAV files (primary/secondary language split).",
    )
    parser.add_argument(
        "--tts_model",
        default="gemini-2.5-flash-preview-tts",
        help="Gemini TTS model name to use when --enable_tts is set.",
    )
    parser.add_argument(
        "--tts_voice",
        default="Achernar",
        help="Voice name for Gemini TTS when --enable_tts is set.",
    )
    parser.add_argument(
        "--tts_temperature",
        type=float,
        default=1.0,
        help="TTS temperature when --enable_tts is set.",
    )
    parser.add_argument(
        "--tts_request_interval_sec",
        type=float,
        default=10.0,
        help="Seconds between TTS requests to respect RPM limits.",
    )
    parser.add_argument(
        "--enable_illustration",
        action="store_true",
        help="Generate page-level illustrations from the generated story JSON.",
    )
    parser.add_argument(
        "--illustration_model",
        default="gemini-2.5-flash-image",
        help="Gemini image model name to use when --enable_illustration is set.",
    )
    parser.add_argument(
        "--illustration_aspect_ratio",
        default="16:9",
        help="Illustration aspect ratio when --enable_illustration is set (e.g. 16:9, 1:1, 3:4).",
    )
    parser.add_argument(
        "--illustration_request_interval_sec",
        type=float,
        default=1.0,
        help="Seconds between image requests when --enable_illustration is set.",
    )
    parser.add_argument(
        "--illustration_skip_existing",
        action="store_true",
        help="Skip pages if page_XX.* already exists when --enable_illustration is set.",
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

        if args.enable_tts:
            tts_api_key = os.getenv("GEMINI_TTS_API_KEY")
            if not tts_api_key:
                raise ValueError(
                    "GEMINI_TTS_API_KEY environment variable not set. "
                    "Story JSON was generated, but TTS requires this key."
                )

            print("Generating audiobook WAV files...")
            tts_generator = TTSGenerator(
                api_key=tts_api_key,
                model_name=args.tts_model,
                voice_name=args.tts_voice,
                temperature=args.tts_temperature,
                request_interval_sec=args.tts_request_interval_sec,
            )
            tts_result = tts_generator.generate_book_audio(
                story=story,
                output_dir=output_dir,
                primary_language=args.primary_lang,
                secondary_language=args.secondary_lang,
                skip_existing=True,
            )

            print(
                "TTS summary: "
                f"total={tts_result['total_tasks']} "
                f"generated={tts_result['generated']} "
                f"skipped={tts_result['skipped']} "
                f"failed={tts_result['failed']}"
            )

            if tts_result["failed"] > 0:
                failures = "\n".join(tts_result["failures"])
                raise RuntimeError(f"TTS generation failed.\n{failures}")

        if args.enable_illustration:
            illustration_api_key = os.getenv("NANO_BANANA_KEY")
            if not illustration_api_key:
                raise ValueError(
                    "NANO_BANANA_KEY environment variable not set. "
                    "Story JSON was generated, but illustration requires this key."
                )

            print("Generating page illustrations...")
            illustration_generator = IllustrationGenerator(
                api_key=illustration_api_key,
                model_name=args.illustration_model,
                aspect_ratio=args.illustration_aspect_ratio,
                request_interval_sec=args.illustration_request_interval_sec,
            )
            illustration_result = illustration_generator.generate_from_story(
                story=story,
                output_dir=output_dir,
                skip_existing=args.illustration_skip_existing,
            )

            print(
                "Illustration summary: "
                f"total={illustration_result['total_tasks']} "
                f"generated={illustration_result['generated']} "
                f"skipped={illustration_result['skipped']} "
                f"failed={illustration_result['failed']} "
                f"manifest={illustration_result['manifest_path']}"
            )

            if illustration_result["failed"] > 0:
                raise RuntimeError(
                    "Illustration generation failed. "
                    f"See manifest: {illustration_result['manifest_path']}"
                )
        
    except Exception as e:
        print(f"Pipeline failed: {e}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
