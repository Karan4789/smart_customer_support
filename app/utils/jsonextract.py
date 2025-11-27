import json
import re
import ast
from typing import Any, List, Optional, Union


JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _try_parse_json_strict(s: str) -> Any:
    """Strict JSON parse."""
    return json.loads(s)


def _try_parse_json_lenient(s: str) -> Any:
    """
    Lenient parser for slightly-broken JSON often seen in LLM/agent outputs.
    - Tries json.loads first
    - Falls back to ast.literal_eval for Python-like dicts
    """
    s = s.strip()

    # First attempt: strict JSON
    try:
        return json.loads(s)
    except Exception:
        pass

    # Heuristic: if it looks like a Python dict/list (single quotes etc.), try literal_eval
    try:
        obj = ast.literal_eval(s)
        # Ensure it's JSON-serializable
        json.dumps(obj, default=str)
        return obj
    except Exception:
        pass

    raise ValueError("Could not parse as JSON (even leniently).")


def extract_json_object(
    text: str,
    *,
    strict: bool = False,
    return_all: bool = False
) -> Optional[Union[Any, List[Any]]]:
    """
    Extract and parse JSON from arbitrary LangChain / agent text output.

    - Prefers ```json ... ``` fenced blocks
    - Falls back to scanning {...} or [...] blocks
    - Can parse leniently (default) for slightly broken JSON
    - If return_all=True, returns list of all parsed JSON objects

    Args:
        text: Raw string from agent / logs.
        strict: If True, only accept valid JSON (no lenient repair).
        return_all: If True, return list of all valid JSONs; else first one.

    Returns:
        Parsed JSON (dict/list/etc), a list of them, or None if nothing valid.
    """
    if not text:
        return None

    parser = _try_parse_json_strict if strict else _try_parse_json_lenient
    results: List[Any] = []

    # 1) Prefer ```json fenced blocks
    fenced = JSON_FENCE_RE.findall(text)
    for block in fenced:
        candidate = block.strip()
        if not candidate:
            continue
        try:
            results.append(parser(candidate))
        except Exception:
            continue

    # 2) If no fenced JSON found, scan for {...} or [...] blocks
    if not results:
        # Simple brace/ bracket scanner for objects and arrays
        opens = ['{', '[']
        closes = {'{': '}', '[': ']'}
        stack = []
        start_idx = None

        for i, ch in enumerate(text):
            if ch in opens:
                if not stack:
                    # potential JSON start
                    start_idx = i
                stack.append(ch)
            elif ch in closes.values() and stack:
                if closes[stack[-1]] == ch:
                    stack.pop()
                    if not stack and start_idx is not None:
                        candidate = text[start_idx:i+1].strip()
                        start_idx = None
                        try:
                            results.append(parser(candidate))
                        except Exception:
                            continue

    if not results:
        return None

    return results if return_all else results[0]
