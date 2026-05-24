"""Streamlit UI for exploring FHIR capability support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st


CATALOG_PATH = Path("data/catalog.json")


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, dict[str, Any]]:
    """Load the generated FHIR capability catalog."""
    return json.loads(path.read_text(encoding="utf-8"))


def render_field_list(fields: list[tuple[str, str]]) -> None:
    """Render fields as a simple bullet list."""
    if not fields:
        st.write("No fields found")
        return

    for field, cardinality in fields:
        st.write(f"- {field} ({cardinality})")


def fields_with_status(resource_data: dict[str, Any], status: str) -> list[tuple[str, str]]:
    """Return fields matching a support status with their cardinalities."""
    fields = resource_data.get("fields", {})
    return [
        (field_name, field_data.get("cardinality", "unknown"))
        for field_name, field_data in fields.items()
        if field_data.get("status") == status
    ]


def main() -> None:
    """Render the FHIR Capability Explorer app."""
    st.set_page_config(page_title="FHIR Capability Explorer", layout="wide")
    st.title("FHIR Capability Explorer")
    st.write(
        "Select a FHIR resource to see which HL7 R4 fields are supported by Epic, "
        "unknown from documentation, or explicitly unsupported."
    )
    st.divider()

    if not CATALOG_PATH.exists():
        st.error("Catalog not found. Run `python3 pipeline/catalog_builder.py` first.")
        return

    catalog = load_catalog()
    resources = sorted(catalog)
    selected_resource = st.selectbox("FHIR resource", resources)
    resource_data: dict[str, Any] = catalog[selected_resource]

    supported = fields_with_status(resource_data, "supported")
    unknown = fields_with_status(resource_data, "unknown")
    not_supported = fields_with_status(resource_data, "not_supported")
    total_fields = len(supported) + len(unknown) + len(not_supported)

    metric_columns = st.columns(4)
    metric_columns[0].metric("Total fields", total_fields)
    metric_columns[1].metric("Supported", len(supported))
    metric_columns[2].metric("Unknown", len(unknown))
    metric_columns[3].metric("Not supported", len(not_supported))

    st.divider()
    st.subheader(selected_resource)

    supported_col, unknown_col, not_supported_col = st.columns(3)

    with supported_col:
        st.success("✅ Supported")
        render_field_list(supported)

    with unknown_col:
        st.warning("❓ Unknown")
        render_field_list(unknown)

    with not_supported_col:
        st.error("❌ Not Supported")
        render_field_list(not_supported)


if __name__ == "__main__":
    main()
