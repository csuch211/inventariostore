
import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.skip(reason="Requires the Flet app server running on localhost:8550")
def test_example(page: Page) -> None:
    page.goto("http://localhost:8550/")
    page.wait_for_load_state("networkidle")

    # Expect a title "to contain" a substring.
    expect(page).to_have_title(re.compile("InventarioStore"))

    # create a locator
    get_started = page.get_by_role("link", name="Get started")

    # Expect an attribute "to be strictly equal" to the value.
    expect(get_started).to_have_attribute("href", "/docs/intro")

    # Click the get started link.
    get_started.click()

    # Expects the URL to contain intro.
    expect(page).to_have_url(re.compile(".*intro"))
