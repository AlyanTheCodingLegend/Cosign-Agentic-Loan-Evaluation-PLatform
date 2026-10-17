from pathlib import Path

from app.agent.reasoner import SYSTEM_PROMPT

PROMPT_FILE = Path(__file__).resolve().parents[2] / "ml" / "model-server" / "system_prompt.txt"


def test_model_server_warmup_prompt_matches_the_app() -> None:
    """If this fails, regenerate ml/model-server/system_prompt.txt from SYSTEM_PROMPT."""
    assert PROMPT_FILE.read_text(encoding="utf-8") == SYSTEM_PROMPT
