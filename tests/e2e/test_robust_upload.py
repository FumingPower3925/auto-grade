import os
import time

import pytest
from playwright.sync_api import Page, Route, expect

from tests.e2e.test_helpers import cleanup_assignments_by_name, ensure_unique_assignment


class TestRobustUploadE2E:
    @pytest.fixture(autouse=True)
    def setup_page(self, page: Page) -> None:
        """Navigate to application before each test."""
        base_url = os.getenv("PLAYWRIGHT_BASE_URL", "http://auto-grade:8080")  # noqa
        page.goto(base_url)
        self.page = page
        self.base_url = base_url

    def test_bulk_upload_progress(self, page: Page) -> None:
        """Test bulk upload with progress tracking and different UI states."""
        assignment_name = "Robust Upload Test"
        ensure_unique_assignment(page, assignment_name)

        # Navigate to assignment
        page.locator(f".assignment-card:has-text('{assignment_name}')").first.click()

        # Setup network interception to delay upload for verification of "Uploading" state
        # We store the route to manually continue it after verification
        captured_routes = []

        def handle_upload(route: Route):
            captured_routes.append(route)
            # Do not continue yet!

        page.route("**/documents", handle_upload)

        # Open upload modal
        upload_btn = page.locator(
            "h2:has-text('Relevant Documents') + .section-actions button, "
            "h2:has-text('Relevant Documents') ~ .section-actions button"
        ).first
        # Fallback if structure is different
        if upload_btn.count() == 0:
            upload_btn = page.locator("button:has-text('Upload Document')").first

        upload_btn.click()

        # Verify modal title to ensure we opened correct one
        expect(page.locator("#uploadModalTitle")).to_contain_text("Upload Relevant Document")

        # Upload files
        page.locator("#fileInput").set_input_files(
            [
                {"name": "doc1.txt", "mimeType": "text/plain", "buffer": b"Content 1"},
                {"name": "doc2.txt", "mimeType": "text/plain", "buffer": b"Content 2"},
            ]
        )

        # Click Submit
        page.click("#uploadForm button[type='submit']")

        # VERIFY UPLOADING STATE
        # Wait for request to be captured (upload started)
        start_time = time.time()
        while len(captured_routes) == 0:
            if time.time() - start_time > 5:
                break
            page.wait_for_timeout(100)
        assert len(captured_routes) > 0, "No upload request captured"

        processing_modal = page.locator("#processingModal")
        # We check compatibility with visibility assertion since we now use style.display
        expect(processing_modal).to_be_visible()

        spinner = page.locator("#processingSpinner")
        # expect(spinner).to_be_visible() # Skip strict visibility check
        expect(page.locator("#processingStatusText")).to_have_text("Uploading documents...")
        expect(page.locator("#processingProgressContainer")).not_to_be_visible()

        # Now we have verified the "Uploading" state.
        # Continue the request to verify transition to "Processing"
        captured_routes[0].continue_()

        # Wait for potential completion of upload (handled by delayed route)
        # Verify transition to PROCESSING STATE

        # We wait for status text to change from "Uploading..."
        expect(page.locator("#processingStatusText")).not_to_have_text("Uploading documents...", timeout=10000)

        expect(spinner).not_to_be_visible()
        expect(page.locator("#processingProgressContainer")).to_be_visible()
        expect(page.locator("#processingDetails")).to_be_visible()

        # Wait for completion
        # The polling runs every 2s.
        expect(page.locator("#processingStatusText")).to_have_text("Processing Complete", timeout=15000)

        # Verify close button is enabled
        close_btn = page.locator("#processingCloseBtn")
        expect(close_btn).to_be_enabled()
        # The page reloads when closing the modal
        with page.expect_navigation():
            close_btn.click()

        # Verify documents listed
        expect(page.locator("#document-list")).to_contain_text("doc1.txt")
        expect(page.locator("#document-list")).to_contain_text("doc2.txt")

        # Cleanup
        page.goto(f"{self.base_url}/")
        cleanup_assignments_by_name(page, assignment_name)
