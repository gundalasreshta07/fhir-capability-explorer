"""Extract structured Epic FHIR details with the OpenAI API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "gpt-4.1-mini"
MODEL_ENV_VAR = "OPENAI_EXTRACTION_MODEL"
DEFAULT_CACHE_DIR = Path("data")
MAX_INPUT_CHARS = 12_000

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
            "Only use fields found in the Response section. "
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
