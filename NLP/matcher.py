# Lightweight BIM/IFC matching helpers.
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import difflib
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
    max_results: int = int(os.getenv("MODEL_MAX_RESULTS", "8"))


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


def _normalize_typo(token: str) -> str:
    """Collapse excessive repeated characters to stabilize simple typos (e.g., dooor -> door)."""
    return re.sub(r"(.)\\1{2,}", r"\\1\\1", token)


def _augment_tokens(tokens: set[str]) -> set[str]:
    augmented = set(tokens)
    for token in list(tokens):
        normalized = _normalize_typo(token)
        if normalized != token and len(normalized) > 2:
            augmented.add(normalized)
    return augmented


STOP_TOKENS = {
    "the",
    "a",
    "an",
    "status",
    "is",
    "to",
    "of",
    "for",
    "in",
    "on",
    "at",
    "and",
    "complete",
    "completed",
    "done",
    "pending",
    "progress",
    "delayed",
    "blocked",
    "inspection",
    "manual",
    "review",
    "level",
    "lvl",
    "l",
    "building",
}

CONFLICT_TOKEN_RULES: list[tuple[str, str]] = [
    ("outside", "inside"),
    ("inside", "outside"),
    ("exterior", "interior"),
    ("interior", "exterior"),
    ("single", "double"),
    ("double", "single"),
]

TYPE_KEYWORDS = [
    "window",
    "door",
    "roof",
    "wall",
    "column",
    "beam",
    "slab",
    "stair",
    "railing",
    "pipe",
    "duct",
]


def _significant_tokens(tokens: set[str]) -> set[str]:
    return {token for token in tokens if token not in STOP_TOKENS and not token.isdigit()}


LEVEL_PATTERN = re.compile(r"\b(?:[a-z]?level|lvl|l)\s*([0-9]+)\b", re.IGNORECASE)
BUILDING_PATTERN = re.compile(r"\bbuilding\s*([A-Za-z0-9]+)\b", re.IGNORECASE)

WEAK_TOKENS = {
    # Generic/common words that should not by themselves justify a match.
    "basic",
    "generic",
    "common",
    "other",
    "case",
    "type",
}


@dataclass(slots=True)
class UpdateHints:
    tokens: set[str]
    significant_tokens: set[str]
    levels: set[str]
    buildings: set[str]


@dataclass(slots=True)
class ElementMetadata:
    tokens: set[str]
    levels: set[str]
    buildings: set[str]
    type_tokens: set[str]


_ELEMENT_META_CACHE: dict[str, ElementMetadata] = {}


def _normalize_level_label(value: str | None) -> str | None:
    if not value:
        return None
    match = LEVEL_PATTERN.search(value)
    if match:
        return f"level {match.group(1)}".lower()
    value_lower = value.lower().strip()
    if value_lower.startswith("level"):
        return value_lower
    return None


def _split_identifier_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    parts = re.split(r"[^A-Za-z0-9]+", value)
    for part in parts:
        if not part:
            continue
        tokens.add(part.lower())
        camel_parts = re.findall(r"[A-Z][a-z]+", part)
        tokens.update(part.lower() for part in camel_parts)
    return {token for token in tokens if token}


def _extract_update_hints(update_text: str) -> UpdateHints:
    tokens = _augment_tokens(_tokenize(update_text))
    significant_tokens = _significant_tokens(tokens)
    levels = {f"level {match}".lower() for match in LEVEL_PATTERN.findall(update_text)}
    buildings = {f"building {match.lower()}" for match in BUILDING_PATTERN.findall(update_text)}
    # Remove level/building tokens from significance to avoid drowning type cues.
    for level in levels:
        significant_tokens.discard(level.replace(" ", ""))
        significant_tokens.discard(level)
    for building in buildings:
        significant_tokens.discard(building.replace(" ", ""))
        significant_tokens.discard(building)
    return UpdateHints(tokens=tokens, significant_tokens=significant_tokens, levels=levels, buildings=buildings)


def _element_metadata(element: ModelElement) -> ElementMetadata:
    cached = _ELEMENT_META_CACHE.get(element.guid)
    if cached:
        return cached

    tokens = _augment_tokens(_tokenize(element.serialize()))
    levels: set[str] = set()
    buildings: set[str] = set()
    type_tokens: set[str] = set()

    payload = element.payload
    ifc_attributes = payload.get("ifcAttributes") if isinstance(payload, dict) else {}
    spatial = None
    if isinstance(ifc_attributes, dict):
        spatial = ifc_attributes.get("IfcSpatialContainer")
        for key in ("IfcClass", "ObjectType"):
            value = ifc_attributes.get(key)
            if isinstance(value, str):
                tokens.update(_split_identifier_tokens(value))
                tokens.update(_tokenize(value))
                type_tokens.update(_split_identifier_tokens(value))
                type_tokens.update(_tokenize(value))
                normalized = _normalize_level_label(value)
                if normalized:
                    levels.add(normalized)
    if spatial and isinstance(spatial, str):
        normalized = _normalize_level_label(spatial)
        if normalized:
            levels.add(normalized)

    # Fallback for models that surface attributes at the top level instead of under ifcAttributes.
    if isinstance(payload, dict):
        for key in ("IfcClass", "ObjectType", "IfcContainedInHost"):
            value = payload.get(key)
            if isinstance(value, str):
                tokens.update(_split_identifier_tokens(value))
                tokens.update(_tokenize(value))
                if key != "IfcContainedInHost":
                    type_tokens.update(_split_identifier_tokens(value))
                    type_tokens.update(_tokenize(value))
                normalized = _normalize_level_label(value)
                if normalized:
                    levels.add(normalized)

    # Fallback: scan the serialized payload for level cues if none were captured.
    if not levels:
        for match in LEVEL_PATTERN.findall(element.serialize()):
            levels.add(f"level {match}".lower())

    classification_id = payload.get("classificationId") if isinstance(payload, dict) else None
    if isinstance(classification_id, str):
        tokens.update(_split_identifier_tokens(classification_id))
        tokens.update(_tokenize(classification_id))
        if "building" in classification_id.lower():
            buildings.add(classification_id.lower())
            buildings.update(_split_identifier_tokens(classification_id))

    # Capture building cues embedded in names or attributes.
    if isinstance(payload, dict):
        for key in ("name", "label", "title"):
            value = payload.get(key)
            if isinstance(value, str):
                tokens.update(_tokenize(value))
                tokens.update(_split_identifier_tokens(value))
                for match in BUILDING_PATTERN.findall(value):
                    buildings.add(f"building {match.lower()}")

    meta = ElementMetadata(tokens=tokens, levels=levels, buildings=buildings, type_tokens=type_tokens)
    _ELEMENT_META_CACHE[element.guid] = meta
    return meta


def _score_element(element: ModelElement, hints: UpdateHints) -> int:
    meta = _element_metadata(element)
    token_overlap = _token_overlap(meta.tokens, hints.tokens)
    significant_overlap = _token_overlap(meta.tokens, hints.significant_tokens)
    level_overlap = len(meta.levels & hints.levels)
    building_overlap = len(meta.buildings & hints.buildings)

    score = token_overlap + (significant_overlap * 3)
    score += level_overlap * 12
    score += building_overlap * 6
    if hints.levels:
        if meta.levels:
            if level_overlap == 0:
                score -= 6
        else:
            score -= 8  # strong penalty when update has a level but element lacks one
    if hints.buildings and not building_overlap:
        score -= 2

    return score
ACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bstatus\s*(?:is\s*)?(?:complete|completed|done)\b", re.IGNORECASE), "status_completed"),
    (re.compile(r"\bstatus\s*(?:is\s*)?in\s+progress\b", re.IGNORECASE), "status_in_progress"),
    (re.compile(r"\bstatus\s*(?:is\s*)?pending\b", re.IGNORECASE), "status_pending"),
    (re.compile(r"\bdelayed\b", re.IGNORECASE), "status_delayed"),
    (re.compile(r"\bblocked\b", re.IGNORECASE), "issue_blocked"),
    (re.compile(r"\binspection\b", re.IGNORECASE), "inspection_required"),
]

STATUS_CUE_TOKENS = {
    "delivered",
    "deliver",
    "delivery",
    "complete",
    "completed",
    "done",
    "progress",
    "delayed",
    "blocked",
    "inspection",
    "install",
    "installed",
    "specified",
    "order",
    "ordered",
    "acceptance",
    "accepted",
    "startup",
    "start",
    "pre",
    "post",
    "status",
}

def _has_status_cue(update_tokens: set[str], cue_tokens: set[str]) -> bool:
    """Detect status cues with fuzzy matching to handle typos (e.g., delivr, accpt)."""
    if update_tokens & cue_tokens:
        return True
    for token in update_tokens:
        token_base = token[:-1] if token.endswith("s") and len(token) > 3 else token
        if len(token_base) < 3:
            continue
        for cue in cue_tokens:
            cue_base = cue[:-1] if cue.endswith("s") and len(cue) > 3 else cue
            if len(cue_base) < 3:
                continue
            if token_base in cue_base or cue_base in token_base:
                return True
            score = difflib.SequenceMatcher(None, token_base, cue_base).ratio()
            if score >= 0.68:
                return True
    return False


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
    hints = _extract_update_hints(update_text)
    if not hints.tokens:
        return elements[:limit]

    scored = sorted(
        elements,
        key=lambda element: _score_element(element, hints),
        reverse=True,
    )
    return scored[:limit]


def _token_overlap(a_tokens: set[str], b_tokens: set[str]) -> int:
    return len(a_tokens & b_tokens)


def _fuzzy_token_overlap(a_tokens: set[str], b_tokens: set[str]) -> int:
    """Count loose overlaps (singular/plural or substring matches) to avoid brittle drops."""
    score = 0
    for a in a_tokens:
        a_base = a[:-1] if a.endswith("s") and len(a) > 3 else a
        for b in b_tokens:
            b_base = b[:-1] if b.endswith("s") and len(b) > 3 else b
            if a_base == b_base:
                score += 1
            elif len(a_base) >= 4 and a_base in b_base:
                score += 1
            elif len(b_base) >= 4 and b_base in a_base:
                score += 1
    return score


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


def _detect_preferred_type(tokens: set[str], significant_tokens: set[str]) -> str | None:
    """Pick a preferred element type keyword using plural-insensitive matching."""
    all_tokens = tokens | significant_tokens
    for keyword in TYPE_KEYWORDS:
        if keyword in all_tokens:
            return keyword
        plural = f"{keyword}s"
        if plural in all_tokens:
            return keyword
        for token in all_tokens:
            token_base = token[:-1] if token.endswith("s") and len(token) > 3 else token
            if token_base == keyword:
                return keyword
    return None


def _normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _select_allowed_status(candidate: str | None, allowed: list[str]) -> str | None:
    """
    Map a potentially noisy status value (typo/spacing) to the closest allowed label.
    Falls back to None if no reasonable similarity is found.
    """
    if not candidate:
        return None
    cand_norm = _normalize_label(candidate)
    if not cand_norm:
        return None

    best = None
    best_score = 0.0
    for option in allowed:
        option_norm = _normalize_label(option)
        if cand_norm == option_norm:
            return option
        # Base similarity plus a boost when one contains the other.
        score = difflib.SequenceMatcher(None, cand_norm, option_norm).ratio()
        if cand_norm in option_norm or option_norm in cand_norm:
            score += 0.15
        if score > best_score:
            best_score = score
            best = option
    if best_score >= 0.72:
        return best
    return None


def chunk_elements(elements: list[ModelElement], max_chars: int) -> list[str]:
    if not elements:
        return []

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for element in elements:
        meta = _element_metadata(element)
        summary_bits: list[str] = []
        if meta.levels:
            summary_bits.append(f"level={','.join(sorted(meta.levels))}")
        if meta.buildings:
            summary_bits.append(f"building={','.join(sorted(meta.buildings))}")
        summary = "; ".join(summary_bits)
        serialized = f"GUID: {element.guid}\nSUMMARY: {summary or 'n/a'}\nDATA: {element.serialize()}\n"
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
    """Match a Telegram-style update to BIM elements and classify a single action."""
    _ELEMENT_META_CACHE.clear()  # Avoid stale metadata across runs or code changes.
    update_text = normalize_update(raw_update)
    update_tokens = _tokenize(update_text)
    update_hints = _extract_update_hints(update_text)
    significant_tokens = update_hints.significant_tokens

    # Prefer matching element type to the most specific type keyword present in the update.
    preferred_type = _detect_preferred_type(update_tokens, significant_tokens)

    elements, fallback_blob = parse_model_data(raw_model)
    guid_status_map = load_guid_statuses()
    status_cue_tokens: set[str] = set()
    for statuses in guid_status_map.values():
        for status_value in statuses:
            status_cue_tokens |= _tokenize(str(status_value))

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

    def _token_matches_any(token: str, candidates: set[str]) -> bool:
        token_base = token[:-1] if token.endswith("s") and len(token) > 3 else token
        for candidate in candidates:
            cand_base = candidate[:-1] if candidate.endswith("s") and len(candidate) > 3 else candidate
            if token == candidate or token_base == cand_base:
                return True
            if len(token_base) >= 4 and token_base in cand_base:
                return True
            if len(cand_base) >= 4 and cand_base in token_base:
                return True
        return False

    def _significant_match_ok(sig_tokens: set[str], candidates: set[str]) -> tuple[bool, int, int, int, int]:
        """
        Require partial coverage of significant tokens but also enforce at least one
        non-generic (non-weak) match so generic terms like "basic" don't pass alone.
        """
        if not sig_tokens:
            return True, 0, 0, 0, 0
        matches = 0
        strong_matches = 0
        strong_tokens = 0
        for token in sig_tokens:
            if token not in WEAK_TOKENS:
                strong_tokens += 1
            if _token_matches_any(token, candidates):
                matches += 1
                if token not in WEAK_TOKENS:
                    strong_matches += 1
        required = 1 if len(sig_tokens) <= 2 else max(2, len(sig_tokens) // 2)
        strong_required = 1 if strong_tokens else 0
        ok = matches >= required and strong_matches >= strong_required
        return ok, matches, required, strong_matches, strong_required

    def _has_conflict(update_tokens: set[str], element_tokens: set[str]) -> bool:
        """Return True when update tokens imply a mutually exclusive condition with element tokens."""
        for required, conflicting in CONFLICT_TOKEN_RULES:
            if required in update_tokens and conflicting in element_tokens and required not in element_tokens:
                return True
        return False

    def _type_conflicts(element_type_tokens: set[str]) -> bool:
        """Reject elements advertising a different primary type than the requested one."""
        if not preferred_type:
            return False
        for type_key in TYPE_KEYWORDS:
            if type_key == preferred_type:
                continue
            if type_key in element_type_tokens:
                return True
        return False

    def _element_matches_update(element: ModelElement) -> bool:
        meta = _element_metadata(element)
        if update_hints.levels:
            if not meta.levels or not update_hints.levels.issubset(meta.levels):
                return False
        if update_hints.buildings:
            if not meta.buildings or not update_hints.buildings.issubset(meta.buildings):
                return False
        if _has_conflict(update_tokens, meta.tokens):
            return False
        if preferred_type and not any(preferred_type in token for token in meta.type_tokens):
            return False
        if _type_conflicts(meta.type_tokens):
            return False
        if significant_tokens:
            sig_ok, _, _, _, _ = _significant_match_ok(significant_tokens, meta.tokens)
            if not sig_ok:
                return False
        else:
            basic_overlap = _token_overlap(update_tokens, meta.tokens)
            if basic_overlap == 0:
                return False
        return True

    matched_elements: list[ModelElement] = []
    seen_guids: set[str] = set()
    for element in ranked_elements:
        if element.guid in seen_guids:
            continue
        if _element_matches_update(element):
            matched_elements.append(element)
            seen_guids.add(element.guid)

    inferred_action = infer_action_from_update(update_text)
    status_cues = bool(inferred_action) or _has_status_cue(update_tokens, STATUS_CUE_TOKENS | status_cue_tokens)
    status = inferred_action or ""
    status_source = "inferred_action" if inferred_action else "unspecified"

    matched_guids = [element.guid for element in matched_elements]

    if matched_guids:
        # Use the first guid with a status mapping to keep a single status for the batch.
        for guid in matched_guids:
            guid_statuses = guid_status_map.get(guid)
            if not guid_statuses:
                continue
            if not status_cues:
                reason_notes.append("Skipped status classification because update had no clear status cues.")
                continue
            try:
                status_response = client.classify_status(update_text, guid, guid_statuses)
                suggested_status = status_response.get("status")
                mapped = _select_allowed_status(suggested_status if isinstance(suggested_status, str) else "", guid_statuses)
                if mapped:
                    status = mapped
                    status_source = "status_classifier"
                    break
            except Exception as exc:  # pragma: no cover - logging only
                logger.warning("Status classification failed: %s", exc)
                reason_notes.append("Status classifier failed; kept previous status choice.")

        reason_parts = [
            f"Matched {len(matched_guids)} element(s) via token/level filters.",
        ]
        if update_hints.levels:
            reason_parts.append(f"Level filter applied: {', '.join(sorted(update_hints.levels))}.")
        if update_hints.buildings:
            reason_parts.append(f"Building filter applied: {', '.join(sorted(update_hints.buildings))}.")
        if status_source == "inferred_action":
            reason_parts.append(f"Status inferred from update text patterns: {status}.")
        elif status_source == "status_classifier":
            reason_parts.append("Status refined using allowed statuses.")
        reason_parts.extend(reason_notes)
        reason_text = " ".join(reason_parts).strip()
        return {"guid": matched_guids, "status": status, "error": reason_text}

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
            meta = _element_metadata(element)
            level_overlap = len(meta.levels & update_hints.levels)
            building_overlap = len(meta.buildings & update_hints.buildings)
            significant_overlap = _token_overlap(meta.tokens, significant_tokens)
            fuzzy_significant = _fuzzy_token_overlap(meta.tokens, significant_tokens) if significant_tokens else 0
            basic_overlap = _token_overlap(update_tokens, element_tokens)
            sig_ok, sig_matches, sig_required, sig_strong, sig_strong_required = _significant_match_ok(
                significant_tokens, meta.tokens
            )
            if update_hints.levels and (not meta.levels or not update_hints.levels.issubset(meta.levels)):
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = "Dropped match because level cues did not align."
            elif update_hints.levels and not meta.levels:
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = "Dropped match because element lacked a spatial container for level."
            elif update_hints.buildings and (not meta.buildings or not update_hints.buildings.issubset(meta.buildings)):
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = "Dropped match because building cues did not align."
            elif _has_conflict(update_tokens, meta.tokens):
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = "Dropped match because element tokens conflict with update intent."
            elif _type_conflicts(meta.type_tokens):
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = "Dropped match because element type conflicts with requested type."
            elif significant_tokens and not sig_ok:
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = (
                    "Dropped match because only "
                    f"{sig_matches}/{len(significant_tokens)} significant tokens aligned (need {sig_required}) "
                    f"and strong matches {sig_strong}/{sig_strong_required}."
                )
            elif preferred_type and not any(preferred_type in token for token in meta.type_tokens):
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = f"Dropped match because element type lacks '{preferred_type}' tokens."
            elif basic_overlap == 0:
                matched_guid = ""
                status = inferred_action or ""
                status_source = "guardrail_reset"
                guardrail_reason = "Dropped OpenAI match because it shared no tokens with the update text."
        else:
            matched_guid = ""
            status = inferred_action or ""
            status_source = "guardrail_reset"
            guardrail_reason = "Dropped OpenAI match because element payload was missing."

    # Heuristic fallback: pick the element with the strongest token overlap if the model returned nothing.
    if not matched_guid and update_tokens:
        best_overlap = 0
        best_guid = ""
        search_tokens = significant_tokens or update_tokens
        fuzzy_best = 0
        for element in elements:
            meta = _element_metadata(element)
            if update_hints.levels:
                if not meta.levels:
                    continue  # require spatial level when update provides one
                if not update_hints.levels.issubset(meta.levels):
                    continue
            if update_hints.buildings:
                if not meta.buildings:
                    continue
                if not update_hints.buildings.issubset(meta.buildings):
                    continue
            if _has_conflict(update_tokens, meta.tokens):
                continue
            if preferred_type:
                if not any(preferred_type in token for token in meta.type_tokens):
                    continue
                if _type_conflicts(meta.type_tokens):
                    continue
            if significant_tokens:
                sig_ok, _, _, _, _ = _significant_match_ok(significant_tokens, meta.tokens)
                if not sig_ok:
                    continue
            overlap = _token_overlap(meta.tokens, search_tokens)
            fuzzy_overlap = _fuzzy_token_overlap(meta.tokens, search_tokens) if search_tokens else 0
            total_overlap = overlap + fuzzy_overlap
            if total_overlap > best_overlap or (total_overlap == best_overlap and fuzzy_overlap > fuzzy_best):
                fuzzy_best = fuzzy_overlap
                best_overlap = overlap
                best_guid = element.guid
        required = 1 if len(search_tokens) <= 2 else 2
        if best_overlap + fuzzy_best >= required:
            matched_guid = best_guid
            status = inferred_action or status or ""
            status_source = "token_overlap"
            reason_notes.append(f"Selected GUID via token-overlap heuristic (shared tokens: {best_overlap}).")

    if matched_guid:
        guid_statuses = load_guid_statuses().get(matched_guid)
        if guid_statuses and status_cues:
            try:
                status_response = client.classify_status(update_text, matched_guid, guid_statuses)
                suggested_status = status_response.get("status")
                mapped = _select_allowed_status(suggested_status if isinstance(suggested_status, str) else "", guid_statuses)
                if mapped:
                    status = mapped
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

    return {"guid": [matched_guid] if matched_guid else [], "status": status, "error": reason_text}


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
