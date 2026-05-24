# Epic FHIR R4 Capability Explorer

This project compares HL7 FHIR R4 resource definitions with Epic's FHIR R4 implementation and produces a structured catalog showing which fields Epic supports.

The project also includes a browser-based visualization for exploring support across Epic R4 resources.

---

# Project Goal

FHIR R4 defines canonical healthcare resources such as:

* Patient
* Observation
* AdverseEvent
* Procedure

Epic implements FHIR R4, but does not always support the complete standard.

This project helps developers quickly understand:

* which fields Epic supports
* which fields are undocumented
* which fields are explicitly unsupported

without manually reading large Epic documentation pages.

---

# Pipeline Overview

The project is structured as a pipeline with five stages:

1. HL7 Parsing
2. Epic Documentation Scraping
3. AI-Based Field Extraction
4. HL7 vs Epic Comparison
5. Catalog Visualization

---

# Repository Structure

```text
pipeline/
    ai_extractor.py
    catalog_builder.py
    comparator.py
    epic_scraper.py

tests/
    test_catalog_builder.py
    test_comparator.py

data/

resources.txt
requirements.txt
app.py
README.md
```

---

# Setup

## Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

## Install Playwright Browsers

```bash
python3 -m playwright install
```

---

# OpenAI API Setup

Set your OpenAI API key before running extraction:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Optional model override:

```bash
export OPENAI_EXTRACTION_MODEL="o4-mini"
```

---

# Running the Pipeline

## 1. Scrape Epic Documentation

Example:

```bash
python3 pipeline/epic_scraper.py AdverseEvent
python3 pipeline/epic_scraper.py Patient
python3 pipeline/epic_scraper.py Observation
```

This extracts visible text from Epic documentation pages using Playwright.

Generated files:

```text
data/adverseevent_sample.txt
data/patient_sample.txt
data/observation_sample.txt
```

---

## 2. Run AI Extraction

```bash
python3 pipeline/ai_extractor.py AdverseEvent
python3 pipeline/ai_extractor.py Patient
python3 pipeline/ai_extractor.py Observation
```

This converts Epic response examples into structured JSON.

Generated files:

```text
data/adverseevent_ai.json
data/patient_ai.json
data/observation_ai.json
```

Caching is enabled so repeated runs do not trigger repeated API calls.

---

## 3. Build Catalog

```bash
python3 pipeline/catalog_builder.py
```

This processes all R4 resources listed in `resources.txt`.

The generated catalog includes:

* operations
* fields
* support status
* cardinality placeholders
* search parameter placeholders

---

## 4. Run Tests

```bash
python3 -m pytest
```

The tests validate comparison logic using real FHIR field names across:

* AdverseEvent
* Patient
* Observation

---

## 5. Launch Visualization

```bash
python3 -m streamlit run app.py
```

The UI opens locally in the browser and does not require a backend server.

---

# Three-State Classification Logic

Each field is classified into one of three states:

| State         | Meaning                                                          |
| ------------- | ---------------------------------------------------------------- |
| supported     | Epic explicitly supports the field                               |
| unknown       | HL7 defines the field but Epic documentation does not mention it |
| not_supported | Epic explicitly states the field is unsupported                  |

Important:

Missing documentation is intentionally classified as `unknown`, not `not_supported`.

---

# Catalog Structure

Example catalog structure:

```json
{
  "Patient": {
    "operations": ["Read", "Search"],
    "fields": {
      "name": {
        "status": "supported",
        "cardinality": "unknown"
      },
      "birthDate": {
        "status": "unknown",
        "cardinality": "unknown"
      }
    },
    "search_parameters": []
  }
}
```

---

# Technical Challenges

## SPA-rendered Epic Documentation

Epic documentation is dynamically rendered in the browser.

Initially, simpler scraping approaches returned incomplete or nearly empty HTML.

To solve this, Playwright was used to render the page fully before extracting visible text.

---

## Bundle Responses

Epic often returns Bundle responses instead of a direct resource.

To improve extraction quality, the pipeline isolates the target resource inside the Bundle before sending data to the AI extractor.

---

## API Cost Control

To reduce OpenAI API usage:

* extraction input size is limited
* only the Response section is processed
* caching is enabled

Full Epic extraction was only performed for:

* AdverseEvent
* Patient
* Observation

---

# Limitations

* Epic documentation is incomplete for some resources.
* Only three resources currently use full Epic AI extraction:

  * AdverseEvent
  * Patient
  * Observation
* Remaining R4 resources are included using fallback HL7 baseline fields.
* For resources without extracted Epic support data, fields default to `unknown`.
* `not_supported` is only used when Epic explicitly denies support for a field.
* Search parameters are currently included as placeholders for future expansion.

---

# Submission Notes

* Only R4 resources are processed.
* STU3 and DSTU2 resources are ignored.
* The visualization runs locally in the browser using Streamlit.
* No backend deployment is required.

