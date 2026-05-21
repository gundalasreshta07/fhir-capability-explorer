from playwright.sync_api import sync_playwright


EPIC_ADVERSE_EVENT_URL = "https://fhir.epic.com/Specifications?api=981"
ADVERSE_EVENT_API_NAME = "AdverseEvent.Read (R4)"


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


if __name__ == "__main__":
    text = fetch_epic_text(EPIC_ADVERSE_EVENT_URL)
    print(text[:2000])
