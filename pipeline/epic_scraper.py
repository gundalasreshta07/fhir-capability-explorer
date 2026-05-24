from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright


EPIC_RESOURCE_CONFIGS = {
    "AdverseEvent": {
        "api_id": "981",
        "api_name": "AdverseEvent.Read (R4)",
        "sample_path": Path("data/epic_sample.txt"),
        "target_resource": "AdverseEvent",
        "response_roots": ["AdverseEvent"],
    },
    "Patient": {
        "api_id": "11219",
        "api_name": "Patient.Read (R4)",
        "sample_path": Path("data/patient_sample.txt"),
        "target_resource": "Patient",
        "response_roots": ["Patient"],
    },
    "Observation": {
        "api_id": "973",
        "api_name": "Observation.Search (R4)",
        "sample_path": Path("data/observation_sample.txt"),
        "target_resource": "Observation",
        "response_roots": ["Bundle", "Observation"],
    },
}


def fetch_epic_text(url: str, api_id: str) -> str:
    """Fetch visible text from an Epic FHIR documentation page."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        api_list_item = page.locator(f"#APIListItem{api_id}")
        if api_list_item.count() > 0:
            api_list_item.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)

        text = page.locator("#divApiTestRoot").inner_text()

        browser.close()
        return text


def response_section(text: str, response_roots: list[str], target_resource: str) -> str:
    """Return the FHIR response example from Epic text."""
    start_marker = "Response:"
    start = text.find(start_marker)
    if start == -1 and response_roots:
        start = min(
            (index for root in response_roots if (index := text.find(f"<{root}")) != -1),
            default=-1,
        )
    if start == -1:
        return text

    response_text = text[start:]
    json_response = _extract_json_resource_response(response_text, target_resource)
    if json_response:
        return json_response

    for root in response_roots:
        end_marker = f"</{root}>"
        end = response_text.find(end_marker)
        if end != -1:
            return response_text[: end + len(end_marker)]

    stop_markers = ["FHIR Errors", "Product Information"]
    stop_indexes = [response_text.find(marker) for marker in stop_markers]
    stop_indexes = [index for index in stop_indexes if index != -1]
    if stop_indexes:
        return response_text[: min(stop_indexes)].rstrip()

    return response_text


def save_resource_sample(resource: str) -> Path:
    """Scrape one configured Epic resource and save its response sample."""
    config = EPIC_RESOURCE_CONFIGS[resource]
    url = f"https://fhir.epic.com/Specifications?api={config['api_id']}"
    text = fetch_epic_text(url, str(config["api_id"]))
    response_text = response_section(
        text,
        list(config["response_roots"]),
        str(config["target_resource"]),
    )
    sample_path = Path(config["sample_path"])
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.write_text(response_text, encoding="utf-8")

    print(f"Saved {resource} Response section to {sample_path}")
    print(response_text[:2000])
    return sample_path


def _extract_json_resource_response(response_text: str, target_resource: str) -> str:
    """Extract the target FHIR resource from a JSON response example."""
    json_start = response_text.find("{")
    if json_start == -1:
        return ""

    try:
        payload, _ = json.JSONDecoder().raw_decode(response_text[json_start:])
    except json.JSONDecodeError:
        return ""

    target_payload = _find_resource(payload, target_resource) or payload
    return "Response:\n" + json.dumps(target_payload, indent=2)


def _find_resource(value: Any, target_resource: str) -> Any | None:
    """Return the first nested FHIR resource matching resourceType."""
    if isinstance(value, dict):
        if value.get("resourceType") == target_resource:
            return value

        for child in value.values():
            found = _find_resource(child, target_resource)
            if found is not None:
                return found

    if isinstance(value, list):
        for child in value:
            found = _find_resource(child, target_resource)
            if found is not None:
                return found

    return None


if __name__ == "__main__":
    selected_resource = sys.argv[1] if len(sys.argv) > 1 else "AdverseEvent"
    if selected_resource not in EPIC_RESOURCE_CONFIGS:
        available = ", ".join(sorted(EPIC_RESOURCE_CONFIGS))
        raise SystemExit(f"Unknown resource '{selected_resource}'. Choose one of: {available}")

    save_resource_sample(selected_resource)
