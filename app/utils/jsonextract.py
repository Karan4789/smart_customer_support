# --- JSON Extractor Utility ---

import json , re


def extract_json_object(raw: str) -> dict | None:
    if not raw:
        return None
    # Prefer fenced ``````
    m = re.search(r"``````", raw, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Fallback: first {...} block
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw[start:end + 1]
        candidate = candidate.replace("```", "")  # remove any errant fences
        try:
            return json.loads(candidate)
        except Exception:
            return None
    return None
