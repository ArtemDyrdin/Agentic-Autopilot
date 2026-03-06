import json
import re
from pathlib import Path

PROMPTS_DIR = Path("prompts")

def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Промпт не найден: {path}")
    return path.read_text(encoding="utf-8")


def fill_prompt(name: str, **kwargs) -> str:
    """Загружает промпт и подставляет переменные через str.replace.
    В отличие от .format() не ломается на фигурных скобках внутри JSON-примеров."""
    text = load_prompt(name)
    for key, value in kwargs.items():
        text = text.replace("{" + key + "}", value)
    return text


def safe_json_parse(text: str) -> dict:
    """Надёжное извлечение JSON из ответа LLM."""
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Не удалось распарсить JSON:\n{text[:500]}")


def print_section(title: str, data: dict | list) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def ask_user(prompt: str, valid_options: list[str]) -> str:
    while True:
        print(f"\n{prompt}  [{' / '.join(valid_options)}]")
        answer = input("> ").strip().lower()
        if answer in valid_options:
            return answer
        print(f"  Введите один из: {valid_options}")