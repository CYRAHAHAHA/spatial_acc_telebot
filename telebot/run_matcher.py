from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow importing io_wrapper from the sibling NLP directory.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR / "NLP"))

import io_wrapper  # type: ignore

#update_path = Path(__file__).resolve().parent / "update.txt"
#update_text = update_path.read_text(encoding="utf-8")
update_text = "pocket slider, L2, abc"
result = io_wrapper.run_sample_match(update_path=update_text)
print(json.dumps(result, ensure_ascii=True))

