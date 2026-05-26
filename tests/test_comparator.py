import json

from pipeline.comparator import compare_adverseevent_fields, compare_fields


def test_compare_fields_classifies_supported_unknown_and_not_supported():
    hl7_fields = ["identifier", "subject", "date", "outcome"]
    epic_fields = ["id", "subject", "date", "unexpectedEpicField"]

    comparison = compare_fields(hl7_fields, epic_fields)

    assert comparison["supported"] == ["subject", "date"]
    assert comparison["unknown"] == ["identifier", "outcome"]
    assert comparison["not_supported"] == []


def test_compare_fields_for_adverseevent_real_r4_fields():
    hl7_fields = ["identifier", "actuality", "category", "event", "subject", "date"]
    epic_fields = ["actuality", "date"]

    result = compare_fields(hl7_fields, epic_fields)

    assert result["supported"] == ["actuality", "date"]
    assert result["unknown"] == ["identifier", "category", "event", "subject"]
    assert result["not_supported"] == []


def test_compare_fields_for_patient_real_r4_fields():
    hl7_fields = ["identifier", "active", "name", "telecom", "gender", "birthDate", "address"]
    epic_fields = ["name", "gender", "birthDate"]

    result = compare_fields(hl7_fields, epic_fields)

    assert result["supported"] == ["name", "gender", "birthDate"]
    assert result["unknown"] == ["identifier", "active", "telecom", "address"]
    assert result["not_supported"] == []


def test_compare_fields_for_observation_real_r4_fields():
    hl7_fields = ["status", "category", "code", "subject", "effectiveDateTime", "value"]
    epic_fields = ["status", "code"]

    result = compare_fields(hl7_fields, epic_fields)

    assert result["supported"] == ["status", "code"]
    assert result["unknown"] == ["category", "subject", "effectiveDateTime", "value"]
    assert result["not_supported"] == []


def test_compare_adverseevent_fields_loads_sample_files(tmp_path):
    hl7_profile_path = tmp_path / "adverseevent.profile.json"
    epic_ai_path = tmp_path / "adverseevent_ai.json"
    hl7_profile_path.write_text(
        json.dumps(
            {
                "snapshot": {
                    "element": [
                        {"path": "AdverseEvent"},
                        {"path": "AdverseEvent.id"},
                        {"path": "AdverseEvent.subject"},
                        {"path": "AdverseEvent.date"},
                        {"path": "AdverseEvent.outcome"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    epic_ai_path.write_text(
        json.dumps(
            {
                "resource": "AdverseEvent",
                "operations": ["read"],
                "fields": ["subject", "date", "extension"],
            }
        ),
        encoding="utf-8",
    )

    comparison = compare_adverseevent_fields(hl7_profile_path, epic_ai_path)

    assert comparison == {
        "supported": ["subject", "date"],
        "not_supported": [],
        "unknown": ["outcome"],
    }
