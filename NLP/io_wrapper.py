from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from matcher import run_matching

MODEL_PATH = Path("sample_data/model.json")
UPDATE_PATH = Path("sample_data/update.txt")


def run_sample_match(model_path: str | Path = MODEL_PATH, update_path: str | Path = UPDATE_PATH) -> dict[str, Any]:
    """Load sample files, run the matcher, and return the JSON result."""
    model_payload = Path(model_path).read_text(encoding="utf-8")
    update_payload = Path(update_path).read_text(encoding="utf-8")
    return run_matching(model_payload, update_payload)


if __name__ == "__main__":
    match_result = run_sample_match()
    print(json.dumps(match_result, ensure_ascii=True))
