import json

from pipeline.catalog_builder import (
    HL7_FALLBACK_FIELDS,
    build_catalog,
    load_hl7_fields,
    load_r4_operations,
    load_r4_resources,
)


def test_load_r4_resources_filters_deduplicates_and_sorts(tmp_path):
    resources_path = tmp_path / "resources.txt"
    resources_path.write_text(
        "\n".join(
            [
                "Observation.Search (R4)",
                "AdverseEvent.Read (R4)",
                "Observation.Read (R4)",
                "Patient.Read (STU3)",
                "Condition.Search (DSTU2)",
            ]
        ),
        encoding="utf-8",
    )

    assert load_r4_resources(resources_path) == ["AdverseEvent", "Observation"]


def test_load_r4_operations_groups_operations_by_resource(tmp_path):
    resources_path = tmp_path / "resources.txt"
    resources_path.write_text(
        "\n".join(
            [
                "Patient.Read (R4)",
                "Patient.Search (R4)",
                "Patient.Read (R4)",
                "Patient.Read (STU3)",
                "Observation.Search (R4)",
            ]
        ),
        encoding="utf-8",
    )

    assert load_r4_operations(resources_path) == {
        "Observation": ["Search"],
        "Patient": ["Read", "Search"],
    }


def test_build_catalog_uses_cached_ai_and_marks_missing_epic_as_unknown(tmp_path):
    resources_path = tmp_path / "resources.txt"
    data_dir = tmp_path / "data"
    output_path = data_dir / "catalog.json"
    data_dir.mkdir()
    resources_path.write_text(
        "\n".join(
            [
                "AdverseEvent.Read (R4)",
                "Observation.Search (R4)",
            ]
        ),
        encoding="utf-8",
    )
    (data_dir / "adverseevent.profile.json").write_text(
        json.dumps(
            {
                "snapshot": {
                    "element": [
                        {"path": "AdverseEvent"},
                        {"path": "AdverseEvent.subject", "min": 1, "max": "1"},
                        {"path": "AdverseEvent.date", "min": 0, "max": "1"},
                        {"path": "AdverseEvent.outcome", "min": 0, "max": "*"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "observation.profile.json").write_text(
        json.dumps(
            {
                "snapshot": {
                    "element": [
                        {"path": "Observation"},
                        {"path": "Observation.status", "min": 1, "max": "1"},
                        {"path": "Observation.code", "min": 1, "max": "1"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "adverseevent_ai.json").write_text(
        json.dumps(
            {
                "resource": "AdverseEvent",
                "operations": ["read"],
                "fields": ["subject"],
            }
        ),
        encoding="utf-8",
    )

    catalog = build_catalog(resources_path, data_dir, output_path)

    assert catalog["AdverseEvent"] == {
        "operations": ["Read"],
        "fields": {
            "subject": {"cardinality": "1..1", "status": "supported"},
            "date": {"cardinality": "0..1", "status": "unknown"},
            "outcome": {"cardinality": "0..*", "status": "unknown"},
        },
        "search_parameters": [],
    }
    assert catalog["Observation"] == {
        "operations": ["Search"],
        "fields": {
            "status": {"cardinality": "1..1", "status": "unknown"},
            "code": {"cardinality": "1..1", "status": "unknown"},
        },
        "search_parameters": [],
    }
    assert json.loads(output_path.read_text(encoding="utf-8")) == catalog


def test_build_catalog_uses_hl7_fallback_when_profile_and_epic_cache_are_missing(tmp_path):
    resources_path = tmp_path / "resources.txt"
    data_dir = tmp_path / "data"
    output_path = data_dir / "catalog.json"
    data_dir.mkdir()
    resources_path.write_text("Patient.Read (R4)", encoding="utf-8")

    catalog = build_catalog(resources_path, data_dir, output_path)

    assert catalog["Patient"] == {
        "operations": ["Read"],
        "fields": {
            "identifier": {"cardinality": "unknown", "status": "unknown"},
            "active": {"cardinality": "unknown", "status": "unknown"},
            "name": {"cardinality": "unknown", "status": "unknown"},
            "telecom": {"cardinality": "unknown", "status": "unknown"},
            "gender": {"cardinality": "unknown", "status": "unknown"},
            "birthDate": {"cardinality": "unknown", "status": "unknown"},
            "address": {"cardinality": "unknown", "status": "unknown"},
        },
        "search_parameters": [],
    }


def test_load_hl7_fields_uses_observation_and_condition_fallbacks(tmp_path):
    assert load_hl7_fields("Observation", tmp_path) == [
        "status",
        "category",
        "code",
        "subject",
        "effectiveDateTime",
        "value",
    ]
    assert load_hl7_fields("Condition", tmp_path) == [
        "clinicalStatus",
        "verificationStatus",
        "category",
        "severity",
        "code",
        "subject",
        "onsetDateTime",
    ]


def test_fallback_fields_cover_resources_file():
    resources = load_r4_resources("resources.txt")

    assert resources
    assert set(resources).issubset(HL7_FALLBACK_FIELDS)
