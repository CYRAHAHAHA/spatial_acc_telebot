# Lightweight BIM/IFC matching helpers.
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv
from openai import APIError, OpenAI

try:  # Prefer the much faster orjson if available.
    import orjson as _orjson
except ImportError:  # pragma: no cover - optional optimization
    _orjson = None

load_dotenv()

# Known keys that might contain GUIDs / unique identifiers.
IDENT_KEYS = [
    "guid",
    "Guid",
    "GlobalId",
    "globalId",
    "externalId",
    "decodedExternalId",
    "id",
]

SYSTEM_PROMPT = (
    "You map construction updates to BIM/IFC elements. Interpret messy model data, fuzzy context, and return strictly the "
    "JSON object {\"matched_guid\": \"\", \"confidence\": 0.0, \"action_required\": \"\", \"rationale\": \"\"}. "
    "Confidence is 0-1. action_required must be a concise verb/label that reflects the update text (e.g., status_completed, status_in_progress, status_delayed, issue_blocked, inspection_required). "
    "If unsure, respond with manual_review and low confidence."
)


# Settings pulled from environment so everything is configurable without edits.
@dataclass(slots=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini-2024-07-18")
    max_chunk_chars: int = int(os.getenv("MODEL_MAX_CHUNK_CHARS", "12000"))
    max_elements: int = int(os.getenv("MODEL_MAX_ELEMENTS", "400"))
    max_openai_chunks: int = int(os.getenv("MODEL_MAX_OPENAI_CHUNKS", "3"))


settings = Settings()
logger = logging.getLogger(__name__)


if _orjson is not None:  # pragma: no branch
    ORJSON_OPTIONS = getattr(_orjson, "OPT_ESCAPE_UNICODE", 0)
else:
    ORJSON_OPTIONS = 0


def _json_dumps(value: Any) -> str:
    if _orjson is not None:
        return _orjson.dumps(value, option=ORJSON_OPTIONS).decode("utf-8")
    return json.dumps(value, ensure_ascii=True)


def _json_loads(value: str) -> Any:
    if _orjson is not None:
        return _orjson.loads(value)
    return json.loads(value)


JSON_ERRORS = (json.JSONDecodeError,)
if _orjson is not None:  # pragma: no branch - simple tuple creation
    JSON_ERRORS = (json.JSONDecodeError, _orjson.JSONDecodeError)


# Thin container around raw model elements so we can serialize consistently.
@dataclass(slots=True)
class ModelElement:
    guid: str
    payload: dict[str, Any]
    _serialized: str | None = None

    def serialize(self) -> str:
        if self._serialized is None:
            compact = {k: v for k, v in self.payload.items() if v not in (None, "")}
            self._serialized = _json_dumps(compact)
        return self._serialized


class OpenAIClient:
    # Wrapper that supports both responses+chat APIs depending on SDK version.

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self._http = httpx.Client(timeout=None)
        self._client = OpenAI(api_key=settings.openai_api_key, http_client=self._http)

    def structured_match(self, chunk: str, update_text: str) -> dict[str, Any]:
        prompt_text = f"MODEL_DATA:\n{chunk}\n\nTELEGRAM_UPDATE:\n{update_text}"
        try:
            if hasattr(self._client, "responses"):
                response = self._client.responses.create(
                    model=settings.openai_model,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    input=[
                        {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                        {"role": "user", "content": [{"type": "text", "text": prompt_text}]},
                    ],
                )
                content = response.output[0].content[0].text  # type: ignore[index]
            elif hasattr(self._client, "chat"):
                response = self._client.chat.completions.create(
                    model=settings.openai_model,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt_text},
                    ],
                )
                content = response.choices[0].message.content
            else:  # pragma: no cover
                raise RuntimeError("OpenAI SDK missing responses/chat APIs")
        except APIError as exc:  # pragma: no cover - surfaced upstream
            raise RuntimeError(f"OpenAI API error: {exc}") from exc

        return json.loads(content)


def _find_guid(node: dict[str, Any]) -> str | None:
    for key in IDENT_KEYS:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _collect_elements(node: Any) -> list[ModelElement]:
    elements: list[ModelElement] = []
    seen: set[str] = set()

    stack: deque[Any] = deque([node])
    append = stack.append
    extend = stack.extend

    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            guid = _find_guid(value)
            if guid and guid not in seen:
                seen.add(guid)
                elements.append(ModelElement(guid=guid, payload=value))
            extend(value.values())
        elif isinstance(value, list):
            extend(value)

    return elements


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)}


ACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bstatus\s*(?:is\s*)?(?:complete|completed|done)\b", re.IGNORECASE), "status_completed"),
    (re.compile(r"\bstatus\s*(?:is\s*)?in\s+progress\b", re.IGNORECASE), "status_in_progress"),
    (re.compile(r"\bstatus\s*(?:is\s*)?pending\b", re.IGNORECASE), "status_pending"),
    (re.compile(r"\bdelayed\b", re.IGNORECASE), "status_delayed"),
    (re.compile(r"\bblocked\b", re.IGNORECASE), "issue_blocked"),
    (re.compile(r"\binspection\b", re.IGNORECASE), "inspection_required"),
]


def infer_action_from_update(update_text: str) -> str | None:
    text = update_text.strip()
    if not text:
        return None
    for pattern, action in ACTION_PATTERNS:
        if pattern.search(text):
            return action
    return None


def prioritize_elements(elements: list[ModelElement], update_text: str, limit: int) -> list[ModelElement]:
    if limit <= 0 or len(elements) <= limit:
        return elements
    tokens = _tokenize(update_text)
    if not tokens:
        return elements[:limit]

    guid_tokens = {token for token in tokens if len(token) > 3}

    def score(element: ModelElement) -> int:
        serialized = element.serialize().lower()
        rank = 0
        for token in tokens:
            if token in serialized:
                rank += 1
        guid_lower = element.guid.lower()
        for token in guid_tokens:
            if token in guid_lower:
                rank += 3
        return rank

    scored = sorted(elements, key=score, reverse=True)
    return scored[:limit]


def parse_model_data(raw_model: Any) -> tuple[list[ModelElement], str]:
    if isinstance(raw_model, str):
        try:
            parsed = _json_loads(raw_model)
        except JSON_ERRORS:
            return [], raw_model
        return parse_model_data(parsed)

    elements: list[ModelElement] = []
    fallback_blob = ""
    if isinstance(raw_model, (dict, list)):
        elements = _collect_elements(raw_model)
        fallback_blob = _json_dumps(raw_model)
    else:
        fallback_blob = str(raw_model)
    return elements, fallback_blob


def normalize_update(raw_update: Any) -> str:
    if isinstance(raw_update, str):
        return raw_update
    try:
        return _json_dumps(raw_update)
    except TypeError:
        return str(raw_update)


def chunk_elements(elements: list[ModelElement], max_chars: int) -> list[str]:
    if not elements:
        return []

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for element in elements:
        serialized = f"GUID: {element.guid}\nDATA: {element.serialize()}\n"
        if size + len(serialized) > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            size = 0
        current.append(serialized)
        size += len(serialized)
    if current:
        chunks.append("\n".join(current))
    return chunks


# Failsafe response when no confident match exists.
DEFAULT_RESPONSE = {
    "matched_guid": "",
    "confidence": 0.0,
    "action_required": "manual_review",
    "rationale": "No confident match",
}


def run_matching(raw_model: Any, raw_update: Any) -> dict[str, Any]:
    """Match a Telegram-style update to a BIM element and classify the action."""
    update_text = normalize_update(raw_update)
    elements, fallback_blob = parse_model_data(raw_model)
    client = OpenAIClient()

    ranked_elements = prioritize_elements(elements, update_text, settings.max_elements)
    chunks = chunk_elements(ranked_elements, settings.max_chunk_chars)
    if not chunks:
        fallback = fallback_blob or update_text
        chunks = [fallback[: settings.max_chunk_chars]]

    if settings.max_openai_chunks > 0:
        chunks = chunks[: settings.max_openai_chunks]

    best = DEFAULT_RESPONSE.copy()
    for chunk in chunks:
        try:
            response = client.structured_match(chunk, update_text)
        except Exception as exc:
            logger.warning("OpenAI matching failed for chunk: %s", exc)
            continue

        try:
            confidence = float(response.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        if confidence >= best["confidence"]:
            best = {
                "matched_guid": response.get("matched_guid", ""),
                "confidence": confidence,
                "action_required": response.get("action_required", "manual_review"),
                "rationale": response.get("rationale", ""),
            }

        if best["confidence"] >= 0.95:
            break

    inferred_action = infer_action_from_update(update_text)
    if best["matched_guid"] and inferred_action:
        if not best["action_required"] or best["action_required"] == "manual_review":
            best["action_required"] = inferred_action

    return best


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Match a tele update to a BIM element.")
    parser.add_argument("--model", default="sample_data/model.json", help="Path to the BIM/ACC model JSON.")
    parser.add_argument(
        "--update",
        default="sample_data/update.txt",
        help="Path to the tele/field update text (plain text or JSON).",
    )
    args = parser.parse_args()

    model_payload = _read_file(args.model)
    update_payload = _read_file(args.update)
    result = run_matching(model_payload, update_payload)
    print(_json_dumps(result))


if __name__ == "__main__":
    _cli()
