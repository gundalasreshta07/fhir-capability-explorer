import json
from types import SimpleNamespace

from pipeline.ai_extractor import extract_epic_data


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text=json.dumps(
                {
                    "resource": "AdverseEvent",
                    "operations": ["read"],
                    "fields": ["id", "actuality", "subject"],
                }
            )
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_extract_epic_data_extracts_known_response_field(tmp_path):
    epic_text = """
    General Information
    HTTP Method:
    GET
    Request:
    ID (String)
    Response:
    <AdverseEvent xmlns="http://hl7.org/fhir">
      <id value="abc123" />
      <actuality value="actual" />
      <subject>
        <reference value="Patient/example" />
      </subject>
    </AdverseEvent>
    """
    client = FakeClient()

    result = extract_epic_data(epic_text, cache_dir=tmp_path, client=client)

    assert "id" in result["fields"]
    assert len(client.responses.calls) == 1
    assert "General Information" not in client.responses.calls[0]["input"]
    assert (tmp_path / "adverseevent_ai.json").exists()
