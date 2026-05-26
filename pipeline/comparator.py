"""Compare official HL7 fields with Epic-extracted fields."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

try:
    from pipeline.hl7_parser import DEFAULT_ADVERSE_EVENT_PROFILE, extract_adverse_event_fields
except ModuleNotFoundError:
    from hl7_parser import DEFAULT_ADVERSE_EVENT_PROFILE, extract_adverse_event_fields


DEFAULT_EPIC_AI_PATH = Path("data/adverseevent_ai.json")


class FieldSupport(TypedDict):
    """Support classification for HL7 baseline fields."""

    supported: list[str]
    not_supported: list[str]
    unknown: list[str]


def load_epic_fields(ai_json_path: Path | str = DEFAULT_EPIC_AI_PATH) -> list[str]:
    """Load Epic field names from an AI extraction JSON file."""
    path = Path(ai_json_path)
    extraction = json.loads(path.read_text(encoding="utf-8"))
    return [str(field) for field in extraction.get("fields", [])]


def compare_fields(hl7_fields: list[str], epic_fields: list[str]) -> FieldSupport:
    """Classify HL7 fields by whether Epic documentation mentions support."""
    epic_set = set(epic_fields)

    return {
        "supported": [field for field in hl7_fields if field in epic_set],
        "not_supported": [],
        "unknown": [field for field in hl7_fields if field not in epic_set],
    }


def compare_adverseevent_fields(
    hl7_profile_path: Path | str = DEFAULT_ADVERSE_EVENT_PROFILE,
    epic_ai_path: Path | str = DEFAULT_EPIC_AI_PATH,
) -> FieldSupport:
    """Classify AdverseEvent HL7 fields using Epic AI extraction files."""
    hl7_fields = extract_adverse_event_fields(hl7_profile_path)
    epic_fields = load_epic_fields(epic_ai_path)
    return compare_fields(hl7_fields, epic_fields)


if __name__ == "__main__":
    comparison = compare_adverseevent_fields()
    print(json.dumps(comparison, indent=2))
