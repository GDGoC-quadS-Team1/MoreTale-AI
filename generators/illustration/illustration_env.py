import os

from dotenv import load_dotenv


load_dotenv()


def resolve_api_key() -> str:
    key = os.getenv("NANO_BANANA_KEY")
    if key:
        return key
    raise ValueError("NANO_BANANA_KEY environment variable not set.")

