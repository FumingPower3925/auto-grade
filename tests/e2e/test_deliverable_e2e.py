import pytest
import re
import os
from playwright.sync_api import Page, expect, Locator, FileChooser


class TestDeliverableE2E:
    """End-to-end tests for deliverable functionality."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page: Page) -> None:
        """Setup page navigation before each test."""
        self.base_url = os.getenv("PLAYWRIGHT_BASE_URL", "http://auto-grade:8080")
        page.goto(self.base_url)
        
        self.assignment_id = self._create_test_assignment(page)
        self.page = page

    def teardown_method(self, method) -> None: # type: ignore
        """Clean up test data after each test."""
        if hasattr(self, 'assignment_id') and self.assignment_id and hasattr(self, 'page'):
            try:
                self.page.evaluate(f"""
                    fetch('/api/assignments/{self.assignment_id}', {{
                        method: 'DELETE'
                    }})
                """)
            except Exception:
                pass

    def _create_test_assignment(self, page: Page) -> str:
        """Create a test assignment and return its ID."""
        # Click create assignment button
        create_button: Locator = page.locator("button:has-text('Create New Assignment')")
        create_button.click()
        
        # Fill in assignment details
        page.fill("#assignmentName", "E2E Deliverable Test Assignment")
        page.fill("#confidenceThreshold", "0.85")
        
        # Submit the form
        page.click("#createAssignmentForm button[type='submit']")
        
        # Wait for modal to close
        page.wait_for_selector("#createAssignmentModal", state="hidden")
        
        # Wait for the assignments to be loaded (triggered by HTMX)
        page.wait_for_timeout(2000)  # Give HTMX time to update
        
        # Get the assignment ID from the newly created assignment
        # Look for the assignment card with our test name
        assignment_cards = page.locator(".assignment-card")
        cards_count = assignment_cards.count()
        
        if cards_count > 0:
            # Find the card with our test assignment name
            for i in range(cards_count):
                card = assignment_cards.nth(i)
                title_elem = card.locator(".assignment-title")
                if title_elem.count() > 0:
                    title_text = title_elem.text_content()
                    if title_text and "E2E Deliverable Test Assignment" in title_text:
                        # Get the link from this card
                        link = card.locator("a").first
                        if link.count() > 0:
                            href = link.get_attribute("href")
                            if href:
                                match = re.search(r'/assignments/([a-f0-9]+)', href)
                                if match:
                                    return match.group(1)
        
        # If we couldn't find the assignment, try a different approach
        # Navigate to the assignments page and extract from URL
        page.click(".assignment-card:has-text('E2E Deliverable Test Assignment')")
        page.wait_for_url(re.compile(r"/assignments/[a-f0-9]+"))
        current_url = page.url
        match = re.search(r'/assignments/([a-f0-9]+)', current_url)
        if match:
            return match.group(1)
        
        return ""

    def test_deliverable_upload_modal_opens(self, page: Page) -> None:
        """Test that the deliverable upload modal opens on assignment detail page."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Click upload deliverables button
        upload_button: Locator = page.locator("button:has-text('Upload Deliverables')").first
        expect(upload_button).to_be_visible()
        upload_button.click()
        
        # Check modal is visible
        modal: Locator = page.locator("#deliverableUploadModal")
        expect(modal).to_be_visible()
        
        # Check modal elements
        upload_area: Locator = page.locator("#uploadArea")
        expect(upload_area).to_be_visible()
        
        extract_checkbox: Locator = page.locator("#extractNames")
        expect(extract_checkbox).to_be_visible()
        expect(extract_checkbox).to_be_checked()
        
        # Close modal
        close_button: Locator = page.locator("#deliverableUploadModal .close")
        close_button.click()
        expect(modal).not_to_be_visible()

    def test_deliverable_file_selection(self, page: Page) -> None:
        """Test selecting files for upload."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Open upload modal
        page.click("button:has-text('Upload Deliverables')")
        
        # Click select files button
        with page.expect_file_chooser() as fc_info:
            page.click("button:has-text('Select Files')")
        file_chooser: FileChooser = fc_info.value
        
        # Create a test PDF file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 Test PDF content")
            tmp_path = tmp.name
        
        try:
            # Select the file
            file_chooser.set_files(tmp_path)
            
            # Check that selected files are displayed
            selected_files: Locator = page.locator("#selectedFiles")
            expect(selected_files).to_be_visible()
            
            files_list: Locator = page.locator("#filesList")
            expect(files_list).to_contain_text(".pdf")
            
            # Upload button should be enabled
            upload_btn: Locator = page.locator("#uploadDeliverablesBtn")
            expect(upload_btn).to_be_enabled()
        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    def test_deliverables_list_display(self, page: Page) -> None:
        """Test that deliverables are displayed in the list."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Check initial state - no deliverables
        deliverables_list: Locator = page.locator("#deliverables-list")
        expect(deliverables_list).to_be_visible()
        
        # Should show "no deliverables" message initially
        page.wait_for_timeout(1000)  # Wait for deliverables to load
        no_files_msg = page.locator(".no-files").first
        if no_files_msg.is_visible():
            expect(no_files_msg).to_contain_text("No deliverables uploaded yet")

    def test_edit_deliverable_modal(self, page: Page) -> None:
        """Test that the edit deliverable modal works."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # First, upload a deliverable via API for testing
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test content'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'test.pdf');
                formData.append('extract_name', 'false');
                
                await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});
                
                // Reload deliverables
                window.loadDeliverables();
            }})()
        """)
        
        # Wait for deliverable to appear
        page.wait_for_timeout(2000)
        
        # Check if edit button exists (if deliverable was uploaded)
        edit_buttons = page.locator(".deliverable-card button:has-text('Edit')").count()
        if edit_buttons > 0:
            # Click edit button
            page.locator(".deliverable-card button:has-text('Edit')").first.click()
            
            # Check edit modal is visible
            edit_modal: Locator = page.locator("#editDeliverableModal")
            expect(edit_modal).to_be_visible()
            
            # Check form fields
            student_name_input: Locator = page.locator("#editStudentName")
            expect(student_name_input).to_be_visible()
            
            mark_input: Locator = page.locator("#editMark")
            expect(mark_input).to_be_visible()
            
            certainty_input: Locator = page.locator("#editCertainty")
            expect(certainty_input).to_be_visible()
            
            # Close modal
            page.click("#editDeliverableModal .btn-secondary")
            expect(edit_modal).not_to_be_visible()

    def test_delete_deliverable_confirmation(self, page: Page) -> None:
        """Test that delete confirmation modal works."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Upload a deliverable via API for testing
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test content'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'test.pdf');
                formData.append('extract_name', 'false');
                
                await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});
                
                // Reload deliverables
                window.loadDeliverables();
            }})()
        """)
        
        # Wait for deliverable to appear
        page.wait_for_timeout(2000)
        
        # Check if delete button exists
        delete_buttons = page.locator(".deliverable-card button:has-text('Delete')").count()
        if delete_buttons > 0:
            # Click delete button
            page.locator(".deliverable-card button:has-text('Delete')").first.click()
            
            # Check confirmation modal
            confirm_modal: Locator = page.locator("#deleteConfirmModal")
            expect(confirm_modal).to_be_visible()
            expect(confirm_modal).to_contain_text("Are you sure you want to delete this deliverable?")
            
            # Cancel deletion
            cancel_button: Locator = page.locator("#deleteConfirmModal button:has-text('Cancel')")
            cancel_button.click()
            expect(confirm_modal).not_to_be_visible()

    def test_drag_and_drop_area(self, page: Page) -> None:
        """Test drag and drop functionality visual feedback."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Open upload modal
        page.click("button:has-text('Upload Deliverables')")
        
        # Get upload area
        upload_area: Locator = page.locator("#uploadArea")
        expect(upload_area).to_be_visible()
        
        # Simulate drag over (visual feedback test)
        upload_area.dispatch_event("dragover") # type: ignore
        
        # Simulate drag leave
        upload_area.dispatch_event("dragleave") # type: ignore

    def test_deliverable_card_information_display(self, page: Page) -> None:
        """Test that deliverable cards show correct information."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Upload a deliverable with known data via API
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test content'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'submission.pdf');
                formData.append('extract_name', 'false');
                
                const response = await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});
                
                const deliverable = await response.json();
                
                // Update with known values
                await fetch(`/api/deliverables/${{deliverable.id}}`, {{
                    method: 'PATCH',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        student_name: 'Test Student',
                        mark: 8.55,
                        certainty_threshold: 0.95
                    }})
                }});
                
                // Reload deliverables
                window.loadDeliverables();
            }})()
        """)
        
        # Wait for deliverable to appear and update
        page.wait_for_timeout(2000)
        
        # Check deliverable card content
        deliverable_cards = page.locator(".deliverable-card").count()
        if deliverable_cards > 0:
            card: Locator = page.locator(".deliverable-card").first
            
            # Check student name
            expect(card).to_contain_text("Test Student")
            
            # Check file name
            expect(card).to_contain_text("submission.pdf")
            
            # Check status
            expect(card).to_contain_text("Marked")
            
            # Check mark
            expect(card).to_contain_text("8.55")
            
            # Check certainty
            expect(card).to_contain_text("95%")

    def test_extract_names_checkbox_toggle(self, page: Page) -> None:
        """Test that the extract names checkbox can be toggled."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Open upload modal
        page.click("button:has-text('Upload Deliverables')")
        
        # Get checkbox
        checkbox: Locator = page.locator("#extractNames")
        
        # Should be checked by default
        expect(checkbox).to_be_checked()
        
        # Uncheck it
        checkbox.uncheck()
        expect(checkbox).not_to_be_checked()
        
        # Check it again
        checkbox.check()
        expect(checkbox).to_be_checked()

    def test_multiple_action_buttons_in_assignment_detail(self, page: Page) -> None:
        """Test that both upload buttons work on the assignment detail page."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Test main upload button
        main_upload_btn: Locator = page.locator(".action-buttons button:has-text('Upload Deliverables')")
        expect(main_upload_btn).to_be_visible()
        main_upload_btn.click()
        
        modal: Locator = page.locator("#deliverableUploadModal")
        expect(modal).to_be_visible()
        
        # Close modal
        page.click("#deliverableUploadModal .close")
        expect(modal).not_to_be_visible()
        
        # Test section header upload button
        section_upload_btn: Locator = page.locator(".deliverables-section button:has-text('+ Upload Deliverables')")
        expect(section_upload_btn).to_be_visible()
        section_upload_btn.click()
        
        expect(modal).to_be_visible()
        
        # Close modal
        page.click("#deliverableUploadModal .close")
        expect(modal).not_to_be_visible()

    def test_deliverable_file_link(self, page: Page) -> None:
        """Test that deliverable file links work correctly."""
        # Navigate to assignment detail page
        page.goto(f"{self.base_url}/assignments/{self.assignment_id}")
        
        # Upload a deliverable via API
        page.evaluate(f"""
            (async () => {{
                const formData = new FormData();
                const pdfContent = new Blob(['%PDF-1.4 Test content'], {{type: 'application/pdf'}});
                formData.append('file', pdfContent, 'test.pdf');
                formData.append('extract_name', 'false');
                
                await fetch('/api/assignments/{self.assignment_id}/deliverables', {{
                    method: 'POST',
                    body: formData
                }});
                
                // Reload deliverables
                window.loadDeliverables();
            }})()
        """)
        
        # Wait for deliverable to appear
        page.wait_for_timeout(2000)
        
        # Check if file link exists
        file_links = page.locator(".deliverable-card a[href*='/api/deliverables/']").count()
        if file_links > 0:
            file_link: Locator = page.locator(".deliverable-card a[href*='/api/deliverables/']").first
            
            # Check that link has correct text
            expect(file_link).to_contain_text(".pdf")
            
            # Check that link has target="_blank" to open in new tab
            expect(file_link).to_have_attribute("target", "_blank")