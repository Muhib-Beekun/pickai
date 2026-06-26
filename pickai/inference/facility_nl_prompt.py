from __future__ import annotations

import json

FACILITY_NL_PROMPT_HEADER = (
    "Return JSON only with key `facility_patch` containing optional fields: "
    "aisles[{aisle_id,direction,blocked}], resources{pickers,putters}, "
    "picking_method, task_interleaving, cart_max_lines.\n"
)


def build_facility_nl_prompt(instruction: str, facility_input: dict | None = None) -> str:
    summary = facility_input if facility_input is not None else {}
    return f"{FACILITY_NL_PROMPT_HEADER}Instruction: {instruction}\nFacility summary: {json.dumps(summary)}"


def build_facility_nl_completion(patch: dict) -> str:
    return json.dumps({"facility_patch": patch})
