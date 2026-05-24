"""Extract structured Epic FHIR details with the OpenAI API."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gpt-4.1-mini"
MODEL_ENV_VAR = "OPENAI_EXTRACTION_MODEL"
DEFAULT_CACHE_DIR = Path("data")
MAX_INPUT_CHARS = 12_000
RESOURCE_SAMPLE_PATHS = {
    "AdverseEvent": Path("data/epic_sample.txt"),
    "Patient": Path("data/patient_sample.txt"),
    "Observation": Path("data/observation_sample.txt"),
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "resource": {"type": "string"},
        "operations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "fields": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["resource", "operations", "fields"],
}


def cache_path_for(resource: str, cache_dir: Path | str = DEFAULT_CACHE_DIR) -> Path:
    """Return the cache file path for a resource extraction."""
    return Path(cache_dir) / f"{resource.lower()}_ai.json"


def response_section(epic_text: str) -> str:
    """Return only the Response section from Epic page text."""
    marker = "Response:"
    start = epic_text.find(marker)
    if start == -1:
        return epic_text
    return epic_text[start:]


def limited_response_text(epic_text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Trim Epic text to the response area and cap size for API cost control."""
    return response_section(epic_text)[:max_chars]


def extract_epic_data(
    epic_text: str,
    resource: str = "adverseevent",
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    client: Any | None = None,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Extract resource, operations, and response fields from Epic text."""
    path = cache_path_for(resource, cache_dir)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    if client is None:
        from openai import OpenAI

        _validate_openai_api_key()
        client = OpenAI()

    trimmed_text = limited_response_text(epic_text)
    selected_model = os.environ.get(MODEL_ENV_VAR, model)
    request = {
        "model": selected_model,
        "instructions": (
            "Extract structured data from Epic FHIR documentation. "
            "Only use fields found in the Response section for the target resource. "
            "Return top-level FHIR field names only, such as name instead of name.family. "
            "If the response is a Bundle, extract fields from the target resource entries, "
            "not from the Bundle wrapper. "
            "Return JSON matching the provided schema."
        ),
        "input": (
            f"Resource hint: {resource}\n\n"
            "Epic Response section text:\n"
            f"{trimmed_text}"
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "epic_fhir_extraction",
                "schema": EXTRACTION_SCHEMA,
                "strict": True,
            }
        },
    }
    if _supports_temperature(selected_model):
        request["temperature"] = 0

    response = client.responses.create(**request)

    extracted = json.loads(_response_output_text(response))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(extracted, indent=2), encoding="utf-8")
    return extracted


def _response_output_text(response: Any) -> str:
    """Read text from an OpenAI Responses API result."""
    if hasattr(response, "output_text"):
        return response.output_text
    if isinstance(response, dict) and "output_text" in response:
        return response["output_text"]
    raise ValueError("OpenAI response did not include output_text")


def _validate_openai_api_key() -> None:
    """Fail early when the OpenAI API key environment variable is malformed."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    if "\n" in api_key or "\r" in api_key:
        raise ValueError("OPENAI_API_KEY must contain one key on a single line.")


def _supports_temperature(model: str) -> bool:
    """Return whether this model family supports a temperature override."""
    return not model.startswith(("o", "gpt-5"))


def sample_path_for(resource: str) -> Path:
    """Return the expected sample text path for a resource."""
    return RESOURCE_SAMPLE_PATHS.get(resource, Path("data") / f"{resource.lower()}_sample.txt")


if __name__ == "__main__":
    selected_resource = sys.argv[1] if len(sys.argv) > 1 else "AdverseEvent"
    sample_path = sample_path_for(selected_resource)
    if not sample_path.exists():
        raise SystemExit(f"Sample file not found: {sample_path}")

    extracted = extract_epic_data(sample_path.read_text(encoding="utf-8"), resource=selected_resource)
    print(json.dumps(extracted, indent=2))
