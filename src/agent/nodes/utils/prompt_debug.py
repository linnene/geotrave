"""Debug utility: writes LLM prompts to a dedicated log file for inspection."""

from pathlib import Path
from datetime import datetime

_PROMPT_LOG_PATH = Path(__file__).resolve().parents.parents.parents.parents.parent / "logs" / "prompt_debug.log"


def log_prompt(node_name: str, prompt_text: str, extra_tag: str = "") -> None:
    """Append a prompt to the debug log file with timestamp and node tag."""
    _PROMPT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tag = f" [{extra_tag}]" if extra_tag else ""
    header = f"{'='*80}\n{datetime.now().isoformat()}  {node_name}{tag}\n{'='*80}"
    with open(_PROMPT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n{header}\n{prompt_text}\n")
