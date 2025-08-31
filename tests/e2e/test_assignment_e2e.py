import pytest
import re
import os
from playwright.sync_api import Page, expect, Locator


class TestAssignmentE2E:
    """End-to-end tests for assignment functionality."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page: Page) -> None:
        """Setup page navigation before each test."""
        # Get base URL from environment or use default
        base_url = os.getenv("PLAYWRIGHT_BASE_URL", "http://auto-grade:8080")
        page.goto(base_url)

    def test_create_assignment_modal(self, page: Page) -> None:
        """Test that the create assignment modal opens and closes."""
        # Find and click the create assignment button
        create_button: Locator = page.locator("button:has-text('Create New Assignment')")
        expect(create_button).to_be_visible()
        create_button.click()

        # Check modal is visible
        modal: Locator = page.locator("#createAssignmentModal")
        expect(modal).to_be_visible()

        # Check form elements are present
        name_input: Locator = page.locator("#assignmentName")
        expect(name_input).to_be_visible()

        threshold_input: Locator = page.locator("#confidenceThreshold")
        expect(threshold_input).to_be_visible()
        expect(threshold_input).to_have_value("0.75")

        # Close modal
        close_button: Locator = page.locator("#createAssignmentModal .close")
        close_button.click()
        expect(modal).not_to_be_visible()

    def test_assignments_list_loads(self, page: Page) -> None:
        """Test that the assignments list loads on page load."""
        # Wait for the assignments section
        assignments_section: Locator = page.locator(".assignments-section")
        expect(assignments_section).to_be_visible()

        # Check the heading
        heading: Locator = page.locator(".assignments-section h2")
        expect(heading).to_have_text("Assignments")

        # The list should be present (may be empty or have items)
        assignments_list: Locator = page.locator("#assignments-list")
        expect(assignments_list).to_be_visible()
        
        # Wait a bit for HTMX to load content
        page.wait_for_timeout(500)
        
        # Check that either we have assignment cards or the no-assignments message
        assignment_cards = page.locator(".assignment-card").count()
        no_assignments = page.locator(".no-assignments").count()
        
        assert assignment_cards > 0 or no_assignments > 0, "Should have either assignments or empty message"

    def test_create_assignment_validation(self, page: Page) -> None:
        """Test form validation for creating assignments."""
        # Open create modal
        create_button: Locator = page.locator("button:has-text('Create New Assignment')")
        create_button.click()

        # Try to submit with empty name
        name_input: Locator = page.locator("#assignmentName")
        name_input.clear()

        # HTML5 validation should prevent submission
        submit_button: Locator = page.locator("#createAssignmentForm button[type='submit']")
        submit_button.click()

        # The modal should still be visible (form not submitted)
        modal: Locator = page.locator("#createAssignmentModal")
        expect(modal).to_be_visible()

        # Now fill in valid data
        name_input.fill("E2E Test Assignment")
        
        threshold_input: Locator = page.locator("#confidenceThreshold")
        threshold_input.clear()
        threshold_input.fill("0.80")

        # Close modal without submitting
        cancel_button: Locator = page.locator("#createAssignmentModal button:has-text('Cancel')")
        cancel_button.click()
        expect(modal).not_to_be_visible()

    def test_delete_confirmation_modal(self, page: Page) -> None:
        """Test that delete confirmation modal works properly."""
        # First, check if there are any assignment cards
        page.wait_for_timeout(1000)  # Wait for assignments to load
        
        assignment_cards = page.locator(".assignment-card").count()
        
        if assignment_cards > 0:
            # Click delete on the first assignment
            delete_button: Locator = page.locator(".assignment-card button:has-text('Delete')").first
            delete_button.click()

            # Check confirmation modal appears
            confirm_modal: Locator = page.locator("#deleteConfirmModal")
            expect(confirm_modal).to_be_visible()

            # Check modal content
            modal_text: Locator = page.locator("#deleteConfirmModal .modal-body")
            expect(modal_text).to_contain_text("Are you sure you want to delete this assignment?")

            # Cancel the deletion
            cancel_button: Locator = page.locator("#deleteConfirmModal button:has-text('Cancel')")
            cancel_button.click()
            expect(confirm_modal).not_to_be_visible()
        else:
            # If no assignments, just verify the delete modal structure exists
            assert page.locator("#deleteConfirmModal").count() == 1

    def test_navigation_to_assignment_detail(self, page: Page) -> None:
        """Test navigation to assignment detail page."""
        # Wait for assignments to load
        page.wait_for_timeout(1000)
        
        assignment_links = page.locator(".assignment-title a").count()
        
        if assignment_links > 0:
            # Click on the first assignment link
            first_assignment: Locator = page.locator(".assignment-title a").first
            assignment_name = first_assignment.text_content()
            first_assignment.click()

            # Check we're on the detail page
            expect(page).to_have_url(re.compile(r"/assignments/[a-f0-9]+"))
            
            # Check breadcrumbs
            breadcrumbs: Locator = page.locator(".breadcrumbs")
            expect(breadcrumbs).to_be_visible()
            expect(breadcrumbs).to_contain_text("Home")
            
            # Check assignment name is displayed
            page_heading: Locator = page.locator(".assignment-detail h1")
            if assignment_name:
                expect(page_heading).to_have_text(assignment_name)
            
            # Navigate back to home
            home_link: Locator = page.locator(".breadcrumbs a:has-text('Home')")
            home_link.click()
            expect(page).to_have_url(re.compile(r"/$"))

    def test_modal_closes_on_outside_click(self, page: Page) -> None:
        """Test that modals close when clicking outside."""
        # Open create assignment modal
        create_button: Locator = page.locator("button:has-text('Create New Assignment')")
        create_button.click()

        modal: Locator = page.locator("#createAssignmentModal")
        expect(modal).to_be_visible()

        # Click outside the modal (on the overlay)
        page.mouse.click(10, 10)  # Click in top-left corner
        
        # Modal should close
        page.wait_for_timeout(500)  # Small wait for animation
        expect(modal).not_to_be_visible()

    def test_page_structure_and_styling(self, page: Page) -> None:
        """Test that the page has proper structure and styling."""
        # Check navbar is present
        navbar: Locator = page.locator(".navbar")
        expect(navbar).to_be_visible()
        
        # Check logo
        logo: Locator = page.locator(".navbar .logo")
        expect(logo).to_have_text("Auto Grade")
        
        # Check container
        container: Locator = page.locator(".container")
        expect(container).to_be_visible()
        
        # Check header section
        header: Locator = page.locator(".header-section")
        expect(header).to_be_visible()
        expect(header).to_contain_text("Welcome to Auto Grade")
        expect(header).to_contain_text("A PoC of an automatic bulk assignment grader LLM engine")
        
        # Check create button styling
        create_button: Locator = page.locator("button:has-text('Create New Assignment')")
        expect(create_button).to_have_class(re.compile(r".*btn.*"))
        expect(create_button).to_have_class(re.compile(r".*btn-primary.*"))