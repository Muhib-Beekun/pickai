from __future__ import annotations

import json

NL_PARSE_PROMPT_HEADER = (
    "Return JSON only with key `constraints` containing: equipment_mode, ladder_must_stay_in_aisle, "
    "start_position{aisle,level,x,y}.\n"
)


def build_nl_parse_prompt(instruction: str, wave_input: dict | None = None) -> str:
    summary = wave_input if wave_input is not None else {}
    return (
        f"{NL_PARSE_PROMPT_HEADER}"
        f"Instruction: {instruction}\n"
        f"Wave summary: {json.dumps(summary)}"
    )


def build_nl_parse_completion(constraints: dict) -> str:
    return json.dumps({"constraints": constraints})
