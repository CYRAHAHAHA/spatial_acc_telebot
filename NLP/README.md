# BIM/IFC NLP Matcher (Backend Only)

This repository now contains a single reusable Python module (`matcher.py`) that can be imported into any backend service. It accepts a Telegram-style update string and raw BIM/ACC model JSON (already parsed or as a string), calls the OpenAI Responses/Chat API, and returns the structured result:

```json
{
  "matched_guid": "...",
  "confidence": 0.0,
  "action_required": "...",
  "rationale": "..."
}
```

All preprocessing, chunking, and heuristic boosts happen locally; the only external dependency is the OpenAI API.

## Install
```bash
python -m venv .venv
source .venv/bin/activate          # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env               # add OPENAI_API_KEY and optional overrides
```

## Usage
```python
import json
from matcher import run_matching

with open("model.json", "r", encoding="utf-8") as fh:
    model_data = json.load(fh)

tele_message = "North stair core concrete pour completed today."

result = run_matching(model_data, tele_message)
print(result)
```

Both `model_data` and `tele_message` can be raw strings or already parsed objects (`dict` / `list`). The helper normalizes inputs, ranks the model elements, chunks them for the OpenAI call, and merges the highest-confidence response with a local action inference heuristic.

### Simple I/O Wrapper
For a zero-configuration demo that just reads the sample files and prints the result, run:
```bash
python io_wrapper.py
```
`io_wrapper.run_sample_match()` is also importable if you want a one-call helper that deals with the sample data paths.

## Environment Variables
- `OPENAI_API_KEY` – required
- `OPENAI_MODEL` – defaults to `gpt-4o-mini-2024-07-18`
- `MODEL_MAX_CHUNK_CHARS` – max serialized characters per chunk (default `12000`)
- `MODEL_MAX_ELEMENTS` – number of ranked elements to send to OpenAI (default `400`)
- `MODEL_MAX_OPENAI_CHUNKS` – cap the number of OpenAI requests per match (default `3`)

Set these directly in the environment or via `.env` (auto-loaded with `python-dotenv`).

## Notes
- The module keeps HTTPX/OpenAI clients internal; long-running systems may want to wrap `run_matching` and cache the client.
- Add your own logging/retries at the call site if you need higher resiliency.
- Sample `model.json` and `update.txt` files are included for quick experiments.
