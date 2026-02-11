from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class StoryPrompt:
    system_instruction_path: str = field(
        default_factory=lambda: str(Path(__file__).resolve().parent / "system_instruction.txt")
    )
    user_prompt_path: str = field(
        default_factory=lambda: str(Path(__file__).resolve().parent / "user_prompt.txt")
    )

    _system_instruction: Optional[str] = field(init=False, repr=False, default=None)
    _user_prompt_template: Optional[str] = field(init=False, repr=False, default=None)

    @staticmethod
    def _read_text(path: str, label: str) -> str:
        file_path = Path(path)
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"{label} file not found at {file_path}") from exc

    @property
    def system_instruction(self) -> str:
        if self._system_instruction is None:
            self._system_instruction = self._read_text(
                self.system_instruction_path, "System instruction"
            )
        return self._system_instruction

    def generate_user_prompt(
        self,
        child_name: str,
        primary_lang: str,
        secondary_lang: str,
        theme: str,
        extra_prompt: str = "",
    ) -> str:
        if self._user_prompt_template is None:
            self._user_prompt_template = self._read_text(
                self.user_prompt_path, "User prompt"
            )

        try:
            return self._user_prompt_template.format(
                child_name=child_name,
                primary_lang=primary_lang,
                secondary_lang=secondary_lang,
                theme=theme,
                extra_prompt=extra_prompt,
            )
        except KeyError as exc:
            raise ValueError(
                f"User prompt template has an unknown placeholder: {exc.args[0]}"
            ) from exc
