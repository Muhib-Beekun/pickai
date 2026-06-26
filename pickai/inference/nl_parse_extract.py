from __future__ import annotations

import json
import re


def extract_constraints_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict) and "constraints" in parsed:
        inner = parsed.get("constraints", {})
        return inner if isinstance(inner, dict) else {}
    return parsed if isinstance(parsed, dict) else {}
