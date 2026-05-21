"""Parse HL7 FHIR R4 StructureDefinition files."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_ADVERSE_EVENT_PROFILE = Path("data/adverseevent.profile.json")

SYSTEM_FIELDS = {
    "id",
    "meta",
    "implicitRules",
    "language",
    "text",
    "contained",
    "extension",
    "modifierExtension",
}


def extract_adverse_event_fields(profile_path: Path | str = DEFAULT_ADVERSE_EVENT_PROFILE) -> list[str]:
    """Return clean top-level AdverseEvent fields from an HL7 StructureDefinition."""
    path = Path(profile_path)
    with path.open(encoding="utf-8") as profile_file:
        profile = json.load(profile_file)

    elements = profile.get("snapshot", {}).get("element", [])
    fields: list[str] = []
    seen: set[str] = set()

    for element in elements:
        element_path = element.get("path", "")
        prefix = "AdverseEvent."
        if not element_path.startswith(prefix):
            continue

        relative_path = element_path.removeprefix(prefix)
        field_name = relative_path.split(".", maxsplit=1)[0]
        if field_name in SYSTEM_FIELDS or field_name in seen:
            continue

        fields.append(field_name)
        seen.add(field_name)

    return fields


def print_adverse_event_fields(profile_path: Path | str = DEFAULT_ADVERSE_EVENT_PROFILE) -> None:
    """Print extracted AdverseEvent fields in a human-readable format."""
    fields = extract_adverse_event_fields(profile_path)
    print("CLEAN HL7 FIELDS")
    for field in fields:
        print(f"- {field}")
    print(f"Total count: {len(fields)}")


if __name__ == "__main__":
    print_adverse_event_fields()
