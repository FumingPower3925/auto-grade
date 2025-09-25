import os
import re
import tempfile

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.test_helpers import cleanup_assignments_by_name


class TestDeliverableSubmissionE2E:
    @pytest.fixture(autouse=True)
    def setup_test_assignment(self, page: Page) -> None:
        """Create a test assignment for deliverable tests."""
        self.base_url = os.getenv("PLAYWRIGHT_BASE_URL", "http://auto-grade:8080") # NOSONAR
        page.goto(self.base_url)
        self.page = page

        # Clean up any existing assignments with this name first
        cleanup_assignments_by_name(page, "E2E Deliverable Test")

        # Create test assignment
        page.click("button:has-text('Create New Assignment')")
        page.fill("#assignmentName", "E2E Deliverable Test")
        page.fill("#confidenceThreshold", "0.85")
        page.click("#createAssignmentForm button[type='submit']")
        page.wait_for_timeout(2000)  # Give more time for creation

        # Navigate to assignment detail
        # Use .first to handle any potential duplicates
        assignment_card = page.locator(".assignment-card:has-text('E2E Deliverable Test')").first

        if assignment_card.count() > 0:
            # Try to find link within the card
            assignment_link = assignment_card.locator("a").first
            if assignment_link.count() == 0:
                # Try clicking the card title directly, but use .first
                assignment_link = assignment_card.locator(".assignment-title").first

            if assignment_link and assignment_link.count() > 0:
                assignment_link.click()
                page.wait_for_url(re.compile(r"/assignments/[a-f0-9]+"), timeout=10000)

                # Store assignment URL for cleanup
                self.assignment_url = page.url
                self.assignment_id = self.assignment_url.split("/")[-1]
            else:
                # If we can't navigate, at least try to get the assignment ID
                self.assignment_id = "unknown"
                self.assignment_url = f"{self.base_url}/"
        else:
            # No assignment found, create a fallback
            self.assignment_id = "unknown"
            self.assignment_url = f"{self.base_url}/"

    def teardown_method(self, _) -> None:
        """Clean up test assignment after each test."""
        if hasattr(self, "page"):
            try:
                # Navigate back to home
                self.page.goto(self.base_url)
                # Clean up all assignments with the test name
                cleanup_assignments_by_name(self.page, "E2E Deliverable Test")
            except Exception:
                pass

    def test_upload_deliverable_workflow(self, page: Page) -> None:
        """Test complete workflow for uploading a deliverable."""
        # Open upload modal
        upload_button = page.locator("button:has-text('Upload Deliverables')").first
        expect(upload_button).to_be_visible()
        upload_button.click()

        # Verify modal opens
        modal = page.locator("#deliverableUploadModal")
        expect(modal).to_be_visible()

        # Check extract names checkbox is checked by default
        extract_checkbox = page.locator("#extractNames")
        expect(extract_checkbox).to_be_checked()

        # Create and select a test file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 Test PDF content for E2E test")
            tmp_path = tmp.name

        try:
            # Select file
            with page.expect_file_chooser() as fc_info:
                page.click("button:has-text('Select Files')")
            file_chooser = fc_info.value
            file_chooser.set_files(tmp_path)

            # Verify file is selected
            selected_files = page.locator("#selectedFiles")
            expect(selected_files).to_be_visible()
            expect(selected_files).to_contain_text(".pdf")

            # Upload button should be enabled
            upload_btn = page.locator("#uploadDeliverablesBtn")
            expect(upload_btn).to_be_enabled()

            # Upload the file
            upload_btn.click()

            # Wait for upload and modal to close
            page.wait_for_timeout(2000)
            expect(modal).not_to_be_visible()

            # Verify deliverable appears in list
            deliverable_card = page.locator(".deliverable-card").first
            expect(deliverable_card).to_be_visible()
            expect(deliverable_card).to_contain_text(".pdf")

        finally:
            os.unlink(tmp_path)

    def test_edit_deliverable_information(self, page: Page) -> None:
        """Test editing deliverable information."""
        # First upload a deliverable via API simulation
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test content'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'test_submission.pdf');
                formData.append('extract_name', 'false');

                await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});

                window.loadDeliverables();
            }})()
        """)

        # Wait for deliverable to appear
        page.wait_for_timeout(2000)

        # Click edit button
        edit_button = page.locator(".deliverable-card button:has-text('Edit')").first
        edit_button.click()

        # Verify edit modal opens
        edit_modal = page.locator("#editDeliverableModal")
        expect(edit_modal).to_be_visible()

        # Update student name
        student_name_input = page.locator("#editStudentName")
        student_name_input.clear()
        student_name_input.fill("John Smith")

        # Update mark
        mark_input = page.locator("#editMark")
        mark_input.clear()
        mark_input.fill("8.75")

        # Update certainty
        certainty_input = page.locator("#editCertainty")
        certainty_input.clear()
        certainty_input.fill("0.92")

        # Save changes
        page.click("#editDeliverableModal button:has-text('Save')")
        expect(edit_modal).not_to_be_visible()

        # Wait for update
        page.wait_for_timeout(1000)

        # Verify changes are reflected
        deliverable_card = page.locator(".deliverable-card").first
        expect(deliverable_card).to_contain_text("John Smith")
        expect(deliverable_card).to_contain_text("8.75")
        expect(deliverable_card).to_contain_text("92%")

    def test_delete_deliverable_workflow(self, page: Page) -> None:
        """Test deleting a deliverable."""
        # Upload a deliverable first
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test content'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'to_delete.pdf');
                formData.append('extract_name', 'false');

                await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});

                window.loadDeliverables();
            }})()
        """)

        page.wait_for_timeout(2000)

        # Click delete button
        delete_button = page.locator(".deliverable-card button:has-text('Delete')").first
        delete_button.click()

        # Verify confirmation modal
        confirm_modal = page.locator("#deleteConfirmModal")
        expect(confirm_modal).to_be_visible()
        expect(confirm_modal).to_contain_text("Are you sure you want to delete this deliverable?")

        # Cancel deletion
        page.click("#deleteConfirmModal button:has-text('Cancel')")
        expect(confirm_modal).not_to_be_visible()

        # Deliverable should still exist
        deliverable_card = page.locator(".deliverable-card:has-text('to_delete.pdf')")
        expect(deliverable_card).to_be_visible()

        # Now actually delete it
        delete_button.click()

        # Try different selectors for the confirm button
        confirm_button = page.locator("#confirmDeleteBtn")
        if confirm_button.count() == 0:
            confirm_button = page.locator("#deleteConfirmModal button.btn-danger")
        if confirm_button.count() == 0:
            confirm_button = page.locator("#deleteConfirmModal button").filter(has_text="Delete")

        if confirm_button.count() > 0:
            confirm_button.click()

        # Wait for deletion
        page.wait_for_timeout(1500)

        # Deliverable should be gone
        expect(deliverable_card).not_to_be_visible(timeout=5000)

        # Should show no deliverables message (be specific about which .no-files)
        # Look for the no-files message in the deliverables section specifically
        no_files_msg = page.locator("#deliverables-list .no-files, .deliverables-section .no-files").first
        if no_files_msg.count() > 0:
            expect(no_files_msg).to_be_visible()
            expect(no_files_msg).to_contain_text("No deliverables")

    def test_drag_and_drop_upload(self, page: Page) -> None:
        """Test drag and drop functionality for file upload."""
        # Open upload modal
        page.click("button:has-text('Upload Deliverables')")
        modal = page.locator("#deliverableUploadModal")
        expect(modal).to_be_visible()

        # Get upload area
        upload_area = page.locator("#uploadArea")
        expect(upload_area).to_be_visible()

        # Simulate drag over (visual feedback test)
        upload_area.dispatch_event("dragover")  # type: ignore

        # Simulate drag leave
        upload_area.dispatch_event("dragleave")  # type: ignore

        # Close modal
        page.click("#deliverableUploadModal .close")
        expect(modal).not_to_be_visible()

    def test_multiple_deliverable_management(self, page: Page) -> None:
        """Test managing multiple deliverables."""
        # Upload multiple deliverables via API
        page.evaluate(f"""
            (async () => {{
                for (let i = 1; i <= 3; i++) {{
                    const formData = new FormData();
                    const pdfContent = new Blob(['%PDF-1.4 Content ' + i], {{type: 'application/pdf'}});
                    formData.append('file', pdfContent, `submission_${{i}}.pdf`);
                    formData.append('extract_name', 'false');

                    await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                        method: 'POST',
                        body: formData
                    }});
                }}

                window.loadDeliverables();
            }})()
        """)

        # Wait for deliverables to load
        page.wait_for_timeout(2500)

        # Verify all deliverables are shown
        deliverable_cards = page.locator(".deliverable-card")
        expect(deliverable_cards).to_have_count(3)

        # Update different deliverables with different marks
        for i in range(3):
            card = deliverable_cards.nth(i)
            edit_button = card.locator("button:has-text('Edit')")
            edit_button.click()

            # Update mark
            mark_input = page.locator("#editMark")
            mark_input.clear()
            mark_input.fill(str(7.0 + i))

            # Save
            page.click("#editDeliverableModal button:has-text('Save')")
            page.wait_for_timeout(500)

        # Verify all updates
        for i in range(3):
            card = deliverable_cards.nth(i)
            expect(card).to_contain_text(f"{7.0 + i:.1f}")

    def test_file_link_functionality(self, page: Page) -> None:
        """Test that file links work correctly."""
        # Upload a deliverable
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test content'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'test_link.pdf');
                formData.append('extract_name', 'false');

                await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});

                window.loadDeliverables();
            }})()
        """)

        page.wait_for_timeout(2000)

        # Find file link
        file_link = page.locator(".deliverable-card a[href*='/api/deliverables/']").first
        expect(file_link).to_be_visible()
        expect(file_link).to_contain_text(".pdf")

        # Verify link has target="_blank"
        expect(file_link).to_have_attribute("target", "_blank")

    def test_extract_names_toggle(self, page: Page) -> None:
        """Test the extract names checkbox functionality."""
        # Open upload modal
        page.click("button:has-text('Upload Deliverables')")

        # Get checkbox
        checkbox = page.locator("#extractNames")

        # Should be checked by default
        expect(checkbox).to_be_checked()

        # Toggle it
        checkbox.uncheck()
        expect(checkbox).not_to_be_checked()

        checkbox.check()
        expect(checkbox).to_be_checked()

        # Close modal
        page.click("#deliverableUploadModal .close")

    def test_deliverable_status_indicators(self, page: Page) -> None:
        """Test that deliverable status is correctly displayed."""
        # Upload a deliverable
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'status_test.pdf');
                formData.append('extract_name', 'false');

                const response = await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});

                window.loadDeliverables();
            }})()
        """)

        page.wait_for_timeout(2000)

        # Initially should show "Unmarked"
        deliverable_card = page.locator(".deliverable-card").first
        expect(deliverable_card).to_contain_text("Unmarked")

        # Edit and add a mark
        page.click(".deliverable-card button:has-text('Edit')")
        page.fill("#editMark", "7.5")
        page.click("#editDeliverableModal button:has-text('Save')")

        page.wait_for_timeout(1000)

        # Should now show "Marked"
        expect(deliverable_card).to_contain_text("Marked")
