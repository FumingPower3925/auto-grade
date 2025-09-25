from playwright.sync_api import Page


def cleanup_assignments_by_name(page: Page, assignment_name: str) -> None:
    """Delete all assignments with the given name."""
    # First check if delete modal is open and close it
    delete_modal = page.locator("#deleteConfirmModal")
    if delete_modal.is_visible():
        cancel_button = page.locator("#deleteConfirmModal button:has-text('Cancel')")
        if cancel_button.count() > 0:
            cancel_button.click()
            page.wait_for_timeout(500)

    # Find all assignments with the given name
    assignments = page.locator(f".assignment-card:has-text('{assignment_name}')")
    count = assignments.count()

    # Delete each one
    for _ in range(count):
        # Always get the first one since the list changes after deletion
        assignment_card = page.locator(f".assignment-card:has-text('{assignment_name}')").first
        if assignment_card.count() == 0:
            break

        delete_button = assignment_card.locator("button:has-text('Delete')")
        if delete_button.count() > 0:
            delete_button.click()

            # Try different selectors for the confirm button
            confirm_button = page.locator("#confirmDeleteBtn")
            if confirm_button.count() == 0:
                confirm_button = page.locator("#deleteConfirmModal button.btn-danger")
            if confirm_button.count() == 0:
                confirm_button = page.locator("#deleteConfirmModal button").filter(has_text="Delete")

            if confirm_button.count() > 0:
                confirm_button.click()
                page.wait_for_timeout(500)  # Wait for deletion to complete


def ensure_unique_assignment(page: Page, assignment_name: str, confidence_threshold: str = "0.75") -> None:
    """Ensure only one assignment exists with the given name by cleaning up duplicates."""
    # First, clean up any existing assignments with this name
    cleanup_assignments_by_name(page, assignment_name)

    # Create the new assignment
    page.click("button:has-text('Create New Assignment')")
    page.fill("#assignmentName", assignment_name)
    page.fill("#confidenceThreshold", confidence_threshold)
    page.click("#createAssignmentForm button[type='submit']")
    page.wait_for_timeout(1500)  # Wait for creation
