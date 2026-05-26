"""Build a FHIR resource support catalog from cached pipeline outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

try:
    from pipeline.comparator import FieldSupport, compare_fields, load_epic_fields
    from pipeline.hl7_parser import SYSTEM_FIELDS, extract_adverse_event_fields
except ModuleNotFoundError:
    from comparator import FieldSupport, compare_fields, load_epic_fields
    from hl7_parser import SYSTEM_FIELDS, extract_adverse_event_fields


DEFAULT_RESOURCES_PATH = Path("resources.txt")
DEFAULT_DATA_DIR = Path("data")
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_DIR / "catalog.json"


class CatalogField(TypedDict):
    """Catalog metadata for one FHIR field."""

    cardinality: str
    status: str


class CatalogResource(TypedDict):
    """Structured catalog entry for one FHIR resource."""

    operations: list[str]
    fields: dict[str, CatalogField]
    search_parameters: list[str]

HL7_FALLBACK_FIELDS = {
    "AdverseEvent": [
        "actuality",
        "category",
        "event",
        "subject",
        "date",
        "recordedDate",
    ],
    "AllergyIntolerance": [
        "clinicalStatus",
        "verificationStatus",
        "category",
        "criticality",
        "code",
        "patient",
    ],
    "CarePlan": [
        "status",
        "intent",
        "category",
        "subject",
        "period",
        "activity",
    ],
    "CareTeam": [
        "status",
        "category",
        "subject",
        "participant",
        "managingOrganization",
    ],
    "Condition": [
        "clinicalStatus",
        "verificationStatus",
        "category",
        "severity",
        "code",
        "subject",
        "onsetDateTime",
    ],
    "Device": [
        "identifier",
        "status",
        "manufacturer",
        "deviceName",
        "type",
        "patient",
    ],
    "DiagnosticReport": [
        "status",
        "category",
        "code",
        "subject",
        "effectiveDateTime",
        "result",
    ],
    "Encounter": [
        "status",
        "class",
        "type",
        "subject",
        "period",
        "participant",
    ],
    "Goal": [
        "lifecycleStatus",
        "category",
        "priority",
        "description",
        "subject",
    ],
    "Immunization": [
        "status",
        "vaccineCode",
        "patient",
        "occurrenceDateTime",
        "manufacturer",
    ],
    "Medication": [
        "code",
        "status",
        "manufacturer",
        "form",
        "amount",
    ],
    "MedicationRequest": [
        "status",
        "intent",
        "medicationCodeableConcept",
        "subject",
        "requester",
    ],
    "Observation": [
        "status",
        "category",
        "code",
        "subject",
        "effectiveDateTime",
        "value",
    ],
    "Organization": [
        "identifier",
        "active",
        "type",
        "name",
        "telecom",
        "address",
    ],
    "Patient": [
        "identifier",
        "active",
        "name",
        "telecom",
        "gender",
        "birthDate",
        "address",
    ],
    "Practitioner": [
        "identifier",
        "active",
        "name",
        "telecom",
        "qualification",
    ],
    "Procedure": [
        "status",
        "category",
        "code",
        "subject",
        "performedDateTime",
    ],
    "ServiceRequest": [
        "status",
        "intent",
        "category",
        "code",
        "subject",
        "requester",
    ],
}


def load_r4_resources(resources_path: Path | str = DEFAULT_RESOURCES_PATH) -> list[str]:
    """Load unique Epic R4 resource names from resources.txt."""
    return sorted(load_r4_operations(resources_path))


def load_r4_operations(resources_path: Path | str = DEFAULT_RESOURCES_PATH) -> dict[str, list[str]]:
    """Load Epic R4 operations grouped by resource name."""
    path = Path(resources_path)
    operations_by_resource: dict[str, list[str]] = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if "(R4)" not in entry or "." not in entry:
            continue

        resource, operation_text = entry.split(".", maxsplit=1)
        operation = operation_text.split(" ", maxsplit=1)[0].strip()
        resource = resource.strip()
        if not resource or not operation:
            continue

        operations = operations_by_resource.setdefault(resource, [])
        if operation not in operations:
            operations.append(operation)

    return dict(sorted(operations_by_resource.items()))


def build_catalog(
    resources_path: Path | str = DEFAULT_RESOURCES_PATH,
    data_dir: Path | str = DEFAULT_DATA_DIR,
    output_path: Path | str = DEFAULT_OUTPUT_PATH,
) -> dict[str, CatalogResource]:
    """Build and save a catalog for every R4 resource listed in resources.txt."""
    operations_by_resource = load_r4_operations(resources_path)
    resources = sorted(operations_by_resource)
    data_path = Path(data_dir)
    catalog: dict[str, CatalogResource] = {}
    skipped: list[str] = []

    for resource in resources:
        try:
            hl7_fields = load_hl7_fields(resource, data_path)
            cardinalities = load_hl7_cardinalities(resource, data_path)
            epic_fields = load_cached_epic_fields(resource, data_path)
            support = compare_fields(hl7_fields, epic_fields)
            catalog[resource] = build_resource_catalog(
                operations_by_resource[resource],
                hl7_fields,
                cardinalities,
                support,
            )
        except (OSError, json.JSONDecodeError) as error:
            skipped.append(f"{resource}: {error}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    print(f"Total R4 resources found: {len(resources)}")
    print(f"Processed successfully: {len(catalog)}")
    print(f"Skipped resources: {len(skipped)}")
    for skipped_resource in skipped:
        print(f"- {skipped_resource}")

    return catalog


def build_resource_catalog(
    operations: list[str],
    hl7_fields: list[str],
    cardinalities: dict[str, str],
    support: FieldSupport,
) -> CatalogResource:
    """Convert support lists into the structured catalog resource shape."""
    status_by_field = {
        field: "supported" for field in support["supported"]
    }
    status_by_field.update({field: "unknown" for field in support["unknown"]})
    status_by_field.update({field: "not_supported" for field in support["not_supported"]})

    fields = {
        field: {
            "cardinality": cardinalities.get(field, "unknown"),
            "status": status_by_field.get(field, "unknown"),
        }
        for field in hl7_fields
    }

    return {
        "operations": operations,
        "fields": fields,
        "search_parameters": [],
    }


def load_hl7_fields(resource: str, data_dir: Path | str = DEFAULT_DATA_DIR) -> list[str]:
    """Load HL7 fields for a resource, using known fallbacks if unavailable."""
    data_path = Path(data_dir)
    profile_path = data_path / f"{resource.lower()}.profile.json"
    if not profile_path.exists():
        return HL7_FALLBACK_FIELDS.get(resource, [])

    if resource == "AdverseEvent":
        fields = extract_adverse_event_fields(profile_path)
    else:
        fields = _extract_resource_fields(profile_path, resource)

    return fields or HL7_FALLBACK_FIELDS.get(resource, [])


def load_hl7_cardinalities(
    resource: str,
    data_dir: Path | str = DEFAULT_DATA_DIR,
) -> dict[str, str]:
    """Load HL7 field cardinalities, falling back to unknown cardinalities."""
    data_path = Path(data_dir)
    profile_path = data_path / f"{resource.lower()}.profile.json"
    if profile_path.exists():
        cardinalities = _extract_resource_cardinalities(profile_path, resource)
        if cardinalities:
            return cardinalities

    return {field: "unknown" for field in HL7_FALLBACK_FIELDS.get(resource, [])}


def load_cached_epic_fields(resource: str, data_dir: Path | str = DEFAULT_DATA_DIR) -> list[str]:
    """Load cached Epic AI fields for a resource, or return an empty list."""
    data_path = Path(data_dir)
    cache_paths = [
        data_path / f"{resource.lower()}_ai.json",
        data_path / f"{resource}_ai.json",
    ]

    for cache_path in cache_paths:
        if cache_path.exists():
            return load_epic_fields(cache_path)

    return []


def _extract_resource_fields(profile_path: Path, resource: str) -> list[str]:
    """Extract top-level field names from a generic HL7 StructureDefinition."""
    return list(_extract_resource_cardinalities(profile_path, resource))


def _extract_resource_cardinalities(profile_path: Path, resource: str) -> dict[str, str]:
    """Extract top-level field cardinalities from a generic HL7 StructureDefinition."""
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    elements = profile.get("snapshot", {}).get("element", [])
    cardinalities: dict[str, str] = {}

    for element in elements:
        element_path = element.get("path", "")
        prefix = f"{resource}."
        if not element_path.startswith(prefix):
            continue

        field_name = element_path.removeprefix(prefix).split(".", maxsplit=1)[0]
        if field_name in SYSTEM_FIELDS or field_name in cardinalities:
            continue

        minimum = element.get("min", "unknown")
        maximum = element.get("max", "unknown")
        cardinalities[field_name] = f"{minimum}..{maximum}"

    return cardinalities


if __name__ == "__main__":
    try:
        build_catalog()
    except FileNotFoundError as error:
        print(f"Could not build catalog: {error.filename} was not found.")
