from pathlib import Path

from pipeline.hl7_parser import extract_adverse_event_fields


def test_extract_adverse_event_fields_includes_subject_and_date():
    fields = extract_adverse_event_fields(Path("data/adverseevent.profile.json"))

    assert "subject" in fields
    assert "date" in fields
