
from playwright.sync_api import Locator, Page


def _close_delete_modal_if_open(page: Page) -> None:
    """Close delete modal if it's currently open."""
    delete_modal: Locator = page.locator("#deleteConfirmModal")
    if not delete_modal.is_visible():
        return

    cancel_button: Locator = page.locator("#deleteConfirmModal button:has-text('Cancel')")
    if cancel_button.count() > 0:
        cancel_button.click()
        page.wait_for_timeout(500)


def _find_confirm_button(page: Page) -> Locator | None:
    """Find the delete confirmation button using multiple selectors."""
    selectors: list[str] = [
        "#confirmDeleteBtn",
        "#deleteConfirmModal button.btn-danger",
        "#deleteConfirmModal button"
    ]

    for selector in selectors[:2]:
        button: Locator = page.locator(selector)
        if button.count() > 0:
            return button

    # Last selector needs filtering
    button: Locator = page.locator(selectors[2]).filter(has_text="Delete")
    return button if button.count() > 0 else None


def _delete_single_assignment(page: Page, assignment_card: Locator) -> bool:
    """Delete a single assignment card. Returns True if deleted successfully."""
    delete_button: Locator = assignment_card.locator("button:has-text('Delete')")
    if delete_button.count() == 0:
        return False

    delete_button.click()
    confirm_button: Locator | None = _find_confirm_button(page)

    if confirm_button:
        confirm_button.click()
        page.wait_for_timeout(500)  # Wait for deletion to complete
        return True

    return False


def cleanup_assignments_by_name(page: Page, assignment_name: str) -> None:
    """Delete all assignments with the given name."""
    _close_delete_modal_if_open(page)

    # Find all assignments with the given name
    assignments: Locator = page.locator(f".assignment-card:has-text('{assignment_name}')")
    count: int = assignments.count()

    # Delete each one
    for _ in range(count):
        # Always get the first one since the list changes after deletion
        assignment_card: Locator = page.locator(f".assignment-card:has-text('{assignment_name}')").first
        if assignment_card.count() == 0:
            break

        _delete_single_assignment(page, assignment_card)


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
