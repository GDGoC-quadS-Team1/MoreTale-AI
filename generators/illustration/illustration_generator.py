import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generators.illustration.illustration_cli import main, parse_args
from generators.illustration.illustration_env import resolve_api_key
from generators.illustration.illustration_pipeline import IllustrationGenerator


def _resolve_api_key() -> str:
    return resolve_api_key()


if __name__ == "__main__":
    main()
