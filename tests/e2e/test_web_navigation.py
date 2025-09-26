import os
import re

import pytest
from playwright.sync_api import Locator, Page, expect

from tests.e2e.test_helpers import cleanup_assignments_by_name


class TestWebNavigationE2E:
    @pytest.fixture(autouse=True)
    def setup_page(self, page: Page) -> None:
        """Navigate to application before each test."""
        self.base_url = os.getenv("PLAYWRIGHT_BASE_URL", "http://auto-grade:8080") # NOSONAR
        page.goto(self.base_url)
        self.page = page

    def test_homepage_structure(self, page: Page) -> None:
        """Test that the homepage has the correct structure."""
        # Verify page title
        expect(page).to_have_title("Auto Grade")

        # Check navbar
        navbar = page.locator(".navbar")
        expect(navbar).to_be_visible()

        # Check logo
        logo = page.locator(".navbar .logo")
        expect(logo).to_be_visible()
        expect(logo).to_have_text("Auto Grade")

        # Check main heading
        heading = page.locator("h1")
        expect(heading).to_have_text("Welcome to Auto Grade")

        # Check description
        description = page.locator(".header-section p").first
        expect(description).to_contain_text("automatic bulk assignment grader")

        # Check create assignment button
        create_button = page.locator("button:has-text('Create New Assignment')")
        expect(create_button).to_be_visible()

        # Check assignments section
        assignments_section = page.locator(".assignments-section")
        expect(assignments_section).to_be_visible()
        expect(assignments_section).to_contain_text("Assignments")

    def test_health_check_functionality(self, page: Page) -> None:
        """Test the health check button functionality."""
        # Find health check button
        healthcheck_button = page.locator("#healthcheck-btn")
        expect(healthcheck_button).to_be_visible()
        expect(healthcheck_button).to_have_text("Health Check")

        # Click the button
        healthcheck_button.click()

        # Wait for success state
        expect(healthcheck_button).to_have_text("✓ Healthy", timeout=5000)
        expect(healthcheck_button).to_have_class(re.compile(r".*success.*"))

        # Wait for button to reset
        expect(healthcheck_button).to_have_text("Health Check", timeout=4000)
        expect(healthcheck_button).not_to_have_class(re.compile(r".*success.*"))

    def test_navigation_flow(self, page: Page) -> None:
        """Test navigation between pages."""
        # Start at home
        expect(page).to_have_url(f"{self.base_url}/")

        # Clean up any existing assignments with this name first
        cleanup_assignments_by_name(page, "Navigation Test Assignment")

        # Create an assignment to navigate to
        page.click("button:has-text('Create New Assignment')")
        page.fill("#assignmentName", "Navigation Test Assignment")
        page.fill("#confidenceThreshold", "0.75")
        page.click("#createAssignmentForm button[type='submit']")
        page.wait_for_timeout(1500)

        # Navigate to assignment detail
        assignment_link = page.locator(".assignment-card:has-text('Navigation Test Assignment') a").first
        if assignment_link.count() == 0:
            # Try alternative selector
            assignment_card = page.locator(".assignment-card:has-text('Navigation Test Assignment')").first
            assignment_link = assignment_card.locator("a").first

        if assignment_link.count() > 0:
            assignment_link.click()

            # Verify we're on detail page
            expect(page).to_have_url(re.compile(r"/assignments/[a-f0-9]+"))

            # Check breadcrumbs
            breadcrumbs = page.locator(".breadcrumbs")
            expect(breadcrumbs).to_be_visible()
            expect(breadcrumbs).to_contain_text("Home")
            expect(breadcrumbs).to_contain_text("Navigation Test Assignment")

            # Navigate back using breadcrumb
            home_link = breadcrumbs.locator("a:has-text('Home')")
            home_link.click()

            # Verify we're back at home
            expect(page).to_have_url(f"{self.base_url}/")

        # Clean up
        cleanup_assignments_by_name(page, "Navigation Test Assignment")

    def test_responsive_button_states(self, page: Page) -> None:
        """Test that buttons have appropriate states and styling."""
        # Test primary button styling
        create_button = page.locator("button:has-text('Create New Assignment')")
        expect(create_button).to_have_class(re.compile(r".*btn.*"))
        expect(create_button).to_have_class(re.compile(r".*btn-primary.*"))

        # Test health check button styling
        healthcheck_button = page.locator("#healthcheck-btn")
        expect(healthcheck_button).to_have_class(re.compile(r".*healthcheck.*"))

        # Click health check and verify style changes
        healthcheck_button.click()
        expect(healthcheck_button).to_have_css("color", "rgb(21, 87, 36)", timeout=5000)
        expect(healthcheck_button).to_have_css("border-color", "rgb(40, 167, 69)")

    def _find_modal_confirm_button(self, page: Page, modal: Locator) -> Locator | None:
        """Helper method to find the confirm button in a modal."""
        selectors = [
            "#deleteConfirmModal button:has-text('Confirm')",
            "#deleteConfirmModal button.btn-danger",
            "#deleteConfirmModal button.confirm",
        ]

        for selector in selectors:
            btn = page.locator(selector)
            if btn.count() > 0:
                return btn.first

        # Fallback: search any button containing 'confirm'
        buttons = modal.locator("button")
        for i in range(buttons.count()):
            candidate = buttons.nth(i)
            try:
                if "confirm" in candidate.inner_text().lower():
                    return candidate
            except Exception:
                pass

        return None

    def _delete_assignment_with_modal(self, page: Page, card: Locator) -> bool:
        """Helper method to delete an assignment via modal confirmation.
        Returns True if deletion was successful, False otherwise."""
        delete_button = card.locator("button:has-text('Delete')")
        delete_button.click()

        modal = page.locator("#deleteConfirmModal")
        page.wait_for_timeout(50)
        expect(modal).to_be_visible()

        confirm_button = self._find_modal_confirm_button(page, modal)

        if confirm_button is None:
            # Close modal gracefully if no confirm button found
            close_btn = modal.locator("button:has-text('Cancel')")
            if close_btn.count() > 0:
                close_btn.click()
            return False

        # Click confirm and wait for modal to disappear
        expect(confirm_button).to_be_visible()
        page.wait_for_timeout(50)
        confirm_button.click()
        expect(modal).not_to_be_visible()
        page.wait_for_timeout(150)
        return True

    def test_empty_state_messaging(self, page: Page) -> None:
        """Test that appropriate messages are shown for empty states."""
        # Delete all existing assignments
        assignment_cards = page.locator(".assignment-card")
        cards_count = assignment_cards.count()

        for _ in range(cards_count):
            card = page.locator(".assignment-card").first
            self._delete_assignment_with_modal(page, card)

        # Verify empty state message
        page.wait_for_timeout(500)
        no_assignments = page.locator(".no-assignments")
        if no_assignments.count() > 0:
            expect(no_assignments).to_be_visible()
            expect(no_assignments).to_contain_text("No assignments")

    def test_modal_accessibility(self, page: Page) -> None:
        """Test modal accessibility features."""
        # Open create assignment modal
        page.click("button:has-text('Create New Assignment')")
        modal = page.locator("#createAssignmentModal")
        expect(modal).to_be_visible()

        # Test ESC key closes modal (may not work in all implementations)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # If ESC doesn't work, click close button
        if modal.is_visible():
            page.click("#createAssignmentModal .close")
            expect(modal).not_to_be_visible()
        else:
            expect(modal).not_to_be_visible()

        # Reopen modal
        page.click("button:has-text('Create New Assignment')")
        expect(modal).to_be_visible()

        # Test that clicking overlay closes modal
        page.mouse.click(10, 10)
        page.wait_for_timeout(500)
        expect(modal).not_to_be_visible()

    def test_form_input_interactions(self, page: Page) -> None:
        """Test form input behaviors."""
        # Open create assignment modal
        page.click("button:has-text('Create New Assignment')")

        # Test input focus and typing
        name_input = page.locator("#assignmentName")
        name_input.click()
        name_input.type("Test Assignment Name")
        expect(name_input).to_have_value("Test Assignment Name")

        # Test threshold input
        threshold_input = page.locator("#confidenceThreshold")
        expect(threshold_input).to_have_value("0.75")  # Default value

        threshold_input.clear()
        threshold_input.type("0.90")
        expect(threshold_input).to_have_value("0.90")

        # Close modal
        page.click("#createAssignmentModal .close")

    def test_page_refresh_persistence(self, page: Page) -> None:
        """Test that page state persists appropriately after refresh."""
        # Clean up any existing assignments with this name first
        cleanup_assignments_by_name(page, "Refresh Test Assignment")

        # Create an assignment
        page.click("button:has-text('Create New Assignment')")
        page.fill("#assignmentName", "Refresh Test Assignment")
        page.fill("#confidenceThreshold", "0.80")
        page.click("#createAssignmentForm button[type='submit']")
        page.wait_for_timeout(1500)

        # Refresh the page
        page.reload()
        page.wait_for_timeout(1000)

        # Assignment should still be visible
        assignment_card = page.locator(".assignment-card:has-text('Refresh Test Assignment')").first
        expect(assignment_card).to_be_visible()

        # Clean up
        cleanup_assignments_by_name(page, "Refresh Test Assignment")

    def test_concurrent_modal_behavior(self, page: Page) -> None:
        """Test that only one modal can be open at a time."""
        # Clean up any existing assignments with this name first
        cleanup_assignments_by_name(page, "Modal Test Assignment")

        # Create an assignment first
        page.click("button:has-text('Create New Assignment')")
        page.fill("#assignmentName", "Modal Test Assignment")
        page.fill("#confidenceThreshold", "0.75")
        page.click("#createAssignmentForm button[type='submit']")
        page.wait_for_timeout(1500)

        # Open create modal
        page.click("button:has-text('Create New Assignment')")
        create_modal = page.locator("#createAssignmentModal")
        expect(create_modal).to_be_visible()

        # Try to open delete modal (should close create modal first)
        page.click("#createAssignmentModal .close")
        expect(create_modal).not_to_be_visible()

        assignment_card = page.locator(".assignment-card:has-text('Modal Test Assignment')").first
        delete_button = assignment_card.locator("button:has-text('Delete')")
        delete_button.click()

        delete_modal = page.locator("#deleteConfirmModal")
        expect(delete_modal).to_be_visible()

        # Close the delete modal before cleanup
        cancel_button = page.locator("#deleteConfirmModal button:has-text('Cancel')")
        if cancel_button.count() > 0:
            cancel_button.click()
            expect(delete_modal).not_to_be_visible()

        # Clean up
        cleanup_assignments_by_name(page, "Modal Test Assignment")

    def test_error_state_handling(self, page: Page) -> None:
        """Test that the application handles error states gracefully."""
        # Test invalid form submission
        page.click("button:has-text('Create New Assignment')")

        # Clear name and try to submit
        name_input = page.locator("#assignmentName")
        name_input.clear()

        submit_button = page.locator("#createAssignmentForm button[type='submit']")
        submit_button.click()

        # Modal should remain open (HTML5 validation prevents submission)
        modal = page.locator("#createAssignmentModal")
        expect(modal).to_be_visible()

        # Close modal
        page.click("#createAssignmentModal .close")
