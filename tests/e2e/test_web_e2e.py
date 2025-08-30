import pytest
import re
import os
from playwright.sync_api import Page, expect, Locator


class TestWebE2E:
    """End-to-end tests for the web interface."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page: Page) -> None:
        """Setup page navigation before each test."""
        # Get base URL from environment or use default
        base_url = os.getenv("PLAYWRIGHT_BASE_URL", "http://auto-grade:8080")
        page.goto(base_url)

    def test_healthcheck_button_success_flow(self, page: Page) -> None:
        """Test that the healthcheck button shows success state after API call."""
        # Wait for page to load and find the healthcheck button
        healthcheck_button: Locator = page.locator("#healthcheck-btn")
        expect(healthcheck_button).to_be_visible()

        # Verify initial button text
        expect(healthcheck_button).to_have_text("Health Check")

        # Click the button to trigger the health check
        healthcheck_button.click()

        # Wait for the API request to complete and check for success state
        # The button should show "✓ Healthy" and have the success class
        expect(healthcheck_button).to_have_text("✓ Healthy", timeout=5000)
        expect(healthcheck_button).to_have_class(re.compile(r".*success.*"))

        # Wait for the button to return to original state (after 3 seconds)
        expect(healthcheck_button).to_have_text("Health Check", timeout=4000)
        expect(healthcheck_button).not_to_have_class(re.compile(r".*success.*"))

    def test_page_loads_with_correct_title(self, page: Page) -> None:
        """Test that the main page loads with correct title."""
        expect(page).to_have_title("Auto Grade")

    def test_navbar_elements_present(self, page: Page) -> None:
        """Test that navbar elements are present and functional."""
        # Check navbar is present
        navbar: Locator = page.locator(".navbar")
        expect(navbar).to_be_visible()

        # Check logo is present and clickable
        logo: Locator = page.locator(".navbar .logo")
        expect(logo).to_be_visible()
        expect(logo).to_have_text("Auto Grade")

        # Check healthcheck button is in navbar
        healthcheck_button: Locator = page.locator(".navbar #healthcheck-btn")
        expect(healthcheck_button).to_be_visible()

    def test_main_content_present(self, page: Page) -> None:
        """Test that main page content is present."""
        # Check main container
        container: Locator = page.locator(".container")
        expect(container).to_be_visible()

        # Check main heading
        heading: Locator = page.locator("h1")
        expect(heading).to_have_text("Welcome to Auto Grade")

        # Check description
        description: Locator = page.locator("p")
        expect(description).to_contain_text("A PoC of an automatic bulk assignment grader LLM engine")

    def test_healthcheck_button_styling(self, page: Page) -> None:
        """Test that the healthcheck button has correct styling."""
        healthcheck_button: Locator = page.locator("#healthcheck-btn")

        # Check initial styling
        expect(healthcheck_button).to_have_class(re.compile(r".*healthcheck.*"))

        # Click the button
        healthcheck_button.click()

        # Use Playwright's built-in CSS expectation to robustly wait for the style to apply
        # The color #155724 from the CSS file corresponds to rgb(21, 87, 36)
        expect(healthcheck_button).to_have_css("color", "rgb(21, 87, 36)", timeout=5000)
        expect(healthcheck_button).to_have_css("border-color", "rgb(40, 167, 69)")

        # Verify the success class is present
        expect(healthcheck_button).to_have_class(re.compile(r".*success.*"))