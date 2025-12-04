from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from NLP.matcher import run_matching

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "data" / "model.json"
UPDATE_PATH = BASE_DIR / "telebot" / "update.txt"


def run_sample_match(update_path: str | Path = UPDATE_PATH) -> dict[str, Any]:
    """
    Load the fixed model file and the provided update, run the matcher, and return the JSON result.

    update_path can be a path to a text file or a raw string containing the update text.
    Returns the full matcher payload: {"guid": "...", "status": "...", "Error": "..."}.
    """
    model_payload = MODEL_PATH.read_text(encoding="utf-8")
    update_payload: str

    if isinstance(update_path, (str, Path)):
        candidate = Path(update_path)
        if candidate.exists():
            update_payload = candidate.read_text(encoding="utf-8")
        else:
            update_payload = str(update_path)
    else:
        update_payload = str(update_path)

    return run_matching(model_payload, update_payload)


if __name__ == "__main__":
    match_result = run_sample_match()
    print(json.dumps(match_result, ensure_ascii=True))
