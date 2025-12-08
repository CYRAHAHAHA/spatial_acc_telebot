# Lightweight BIM/IFC matching helpers.
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
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
]

SYSTEM_PROMPT = (
    "You map construction updates to BIM/IFC elements. Interpret messy model data, fuzzy context, and return strictly the "
    "JSON object {\"matched_guid\": \"\", \"confidence\": 0.0, \"action_required\": \"\", \"rationale\": \"\"}. "
    "Confidence is 0-1. action_required must be a concise verb/label that reflects the update text (e.g., status_completed, status_in_progress, status_delayed, issue_blocked, inspection_required). "
    "Only pick a GUID if the element data clearly refers to the update (e.g., matching keywords like door/railing/window/etc.). "
    "If unsure or keywords do not align, respond with manual_review and low confidence. Never guess."
)

STATUS_PROMPT = (
    "You classify the project status for a specific BIM/IFC element. "
    "Only choose a status from the provided list. "
    "Return strictly the JSON object {\"status\": \"\", \"rationale\": \"\"}. "
    "If none apply, respond with manual_review."
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

    def classify_status(self, update_text: str, guid: str, statuses: list[str]) -> dict[str, Any]:
        options = "\n".join(f"- {status}" for status in statuses)
        prompt_text = (
            f"GUID: {guid}\n"
            f"TELEGRAM_UPDATE:\n{update_text}\n\n"
            f"POSSIBLE_STATUSES:\n{options}\n"
            "Pick the single best status from POSSIBLE_STATUSES."
        )
        try:
            if hasattr(self._client, "responses"):
                response = self._client.responses.create(
                    model=settings.openai_model,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    input=[
                        {"role": "system", "content": [{"type": "text", "text": STATUS_PROMPT}]},
                        {"role": "user", "content": [{"type": "text", "text": prompt_text}]},
                    ],
                )
                content = response.output[0].content[0].text  # type: ignore[index]
            elif hasattr(self._client, "chat"):
                response = self._client.chat.completions.create(
                    model=settings.openai_model,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": STATUS_PROMPT},
                        {"role": "user", "content": prompt_text},
                    ],
                )
                content = response.choices[0].message.content
            else:  # pragma: no cover
                raise RuntimeError("OpenAI SDK missing responses/chat APIs")
        except APIError as exc:  # pragma: no cover - surfaced upstream
            raise RuntimeError(f"OpenAI API error: {exc}") from exc

        return json.loads(content)


@lru_cache(maxsize=1)
def load_guid_statuses() -> dict[str, list[str]]:
    """Load cached guid->status names mapping."""
    data_path = Path(__file__).resolve().parent.parent / "data" / "guid_status_names.json"
    try:
        payload = data_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("guid_status_names.json not found at %s", data_path)
        return {}
    try:
        parsed = _json_loads(payload)
    except JSON_ERRORS:
        logger.warning("Failed to parse guid_status_names.json at %s", data_path)
        return {}
    if not isinstance(parsed, dict):
        logger.warning("guid_status_names.json is not a mapping at %s", data_path)
        return {}
    cleaned: dict[str, list[str]] = {}
    for key, value in parsed.items():
        if isinstance(key, str) and isinstance(value, list):
            cleaned[key] = [str(item) for item in value if isinstance(item, (str, int, float))]
    return cleaned


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


def _token_overlap(a_tokens: set[str], b_tokens: set[str]) -> int:
    return len(a_tokens & b_tokens)


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
    update_tokens = _tokenize(update_text)
    elements, fallback_blob = parse_model_data(raw_model)
    client = OpenAIClient()
    element_index = {element.guid: element for element in elements}
    reason_notes: list[str] = []
    if not elements:
        reason_notes.append("No GUID-bearing elements were found in the model; using fallback blob.")

    ranked_elements = prioritize_elements(elements, update_text, settings.max_elements)
    chunks = chunk_elements(ranked_elements, settings.max_chunk_chars)
    if not chunks:
        fallback = fallback_blob or update_text
        chunks = [fallback[: settings.max_chunk_chars]]

    if settings.max_openai_chunks > 0:
        chunks = chunks[: settings.max_openai_chunks]

    best = DEFAULT_RESPONSE.copy()
    best_confidence = 0.0
    best_rationale = DEFAULT_RESPONSE["rationale"]
    match_source = ""
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

        if confidence >= best_confidence:
            best_confidence = confidence
            best_rationale = str(response.get("rationale", "") or "").strip() or best_rationale
            best = {
                "matched_guid": response.get("matched_guid", ""),
                "confidence": confidence,
                "action_required": response.get("action_required", "manual_review"),
                "rationale": response.get("rationale", ""),
            }
            match_source = "openai"

        if best["confidence"] >= 0.95:
            break

    inferred_action = infer_action_from_update(update_text)
    status_source = "openai"
    if best["matched_guid"] and inferred_action:
        if not best["action_required"] or best["action_required"] == "manual_review":
            best["action_required"] = inferred_action
            status_source = "inferred_action"
    status = best.get("action_required", "manual_review")
    matched_guid = best.get("matched_guid", "")

    # Guardrail: ensure the selected element shares tokens with the update to avoid spurious matches.
    guardrail_reason = None
    if matched_guid:
        element = element_index.get(matched_guid)
        if element:
            element_tokens = _tokenize(element.serialize())
            if _token_overlap(update_tokens, element_tokens) == 0:
                matched_guid = ""
                status = inferred_action or "manual_review"
                status_source = "guardrail_reset"
                guardrail_reason = "Dropped OpenAI match because it shared no tokens with the update text."
        else:
            matched_guid = ""
            status = inferred_action or "manual_review"
            status_source = "guardrail_reset"
            guardrail_reason = "Dropped OpenAI match because element payload was missing."

    # Heuristic fallback: pick the element with the strongest token overlap if the model returned nothing.
    if not matched_guid and update_tokens:
        best_overlap = 0
        best_guid = ""
        for element in elements:
            element_tokens = _tokenize(element.serialize())
            overlap = _token_overlap(update_tokens, element_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
                best_guid = element.guid
        if best_overlap >= 2:  # require at least a couple of shared tokens to avoid noise
            matched_guid = best_guid
            status = inferred_action or status
            status_source = "token_overlap"
            reason_notes.append(f"Selected GUID via token-overlap heuristic (shared tokens: {best_overlap}).")

    if matched_guid:
        guid_statuses = load_guid_statuses().get(matched_guid)
        if guid_statuses:
            try:
                status_response = client.classify_status(update_text, matched_guid, guid_statuses)
                suggested_status = status_response.get("status")
                if isinstance(suggested_status, str) and suggested_status.strip():
                    status = suggested_status.strip()
                    status_source = "status_classifier"
            except Exception as exc:  # pragma: no cover - logging only
                logger.warning("Status classification failed: %s", exc)
                reason_notes.append("Status classifier failed; kept previous status choice.")

    # Build a short reasoning string for downstream logging.
    reason_parts: list[str] = []
    if matched_guid:
        source_label = {
            "openai": "OpenAI structured match",
            "token_overlap": "token-overlap heuristic",
        }.get(match_source or status_source, "matcher")
        reason_parts.append(f"Matched GUID {matched_guid} via {source_label} (confidence {best_confidence:.2f}).")
    else:
        if guardrail_reason:
            reason_parts.append(guardrail_reason)
        elif not elements:
            reason_parts.append("No GUID-bearing elements were available to match.")
        elif not update_tokens:
            reason_parts.append("Update text contained no tokens to match against the model.")
        else:
            reason_parts.append("No confident GUID match; leaving status as manual review.")

    if best_rationale:
        reason_parts.append(f"Model rationale: {best_rationale}")
    reason_parts.extend(reason_notes)

    if status_source == "inferred_action":
        reason_parts.append(f"Status inferred from update text patterns: {status}.")
    elif status_source == "status_classifier":
        reason_parts.append(f"Status refined using allowed statuses for GUID {matched_guid}.")
    elif status == "manual_review" and matched_guid:
        reason_parts.append("Status defaults to manual_review for this match.")

    reason_text = " ".join(reason_parts).strip()

    return {"guid": matched_guid, "status": status, "error": reason_text}


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Match a tele update to a BIM element.")
    parser.add_argument("--model", default="data/model.json", help="Path to the BIM/ACC model JSON.")
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
