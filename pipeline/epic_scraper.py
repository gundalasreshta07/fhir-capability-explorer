from playwright.sync_api import sync_playwright


EPIC_ADVERSE_EVENT_URL = "https://fhir.epic.com/Specifications?api=981"
ADVERSE_EVENT_API_NAME = "AdverseEvent.Read (R4)"
EPIC_SAMPLE_PATH = "data/epic_sample.txt"


def fetch_epic_text(url: str) -> str:
    """Fetch visible text from an Epic FHIR documentation page."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        if page.locator("#APIListItem981").count() > 0:
            page.locator("#APIListItem981").click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)

        text = page.locator("#divApiTestRoot").inner_text()

        browser.close()
        return text


def response_section(text: str) -> str:
    """Return the AdverseEvent XML from the Response section."""
    start_marker = "Response:"
    start = text.find(start_marker)
    if start == -1:
        start = text.find("<AdverseEvent")
    if start == -1:
        return text

    response_text = text[start:]
    end_marker = "</AdverseEvent>"
    end = response_text.find(end_marker)
    if end == -1:
        return response_text

    return response_text[: end + len(end_marker)]


if __name__ == "__main__":
    text = fetch_epic_text(EPIC_ADVERSE_EVENT_URL)
    response_text = response_section(text)

    with open(EPIC_SAMPLE_PATH, "w", encoding="utf-8") as sample_file:
        sample_file.write(response_text)

    print(f"Saved full Response section to {EPIC_SAMPLE_PATH}")
    print(response_text[:2000])
