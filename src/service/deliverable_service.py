import io
import logging
import os
import re
from typing import Any

import httpx
from pypdf import PdfReader

from src.repository.db.factory import get_database_repository
from src.repository.db.models import DeliverableModel

logger = logging.getLogger(__name__)


class DeliverableService:
    """Service for handling deliverable operations."""

    def __init__(self) -> None:
        self.db_repository = get_database_repository()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    def extract_student_name_from_pdf(self, pdf_content: bytes) -> tuple[str, str | None]:
        """Extract student name from PDF content using PyPDF2.

        Args:
            pdf_content: The PDF content as bytes.

        Returns:
            A tuple of (student_name, extracted_text).
        """
        try:
            pdf_file = io.BytesIO(pdf_content)

            pdf_reader = PdfReader(pdf_file)

            extracted_text = ""
            pages_to_check = min(3, len(pdf_reader.pages))

            for page_num in range(pages_to_check):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    extracted_text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    continue

            student_name = self.extract_name_from_text(extracted_text)

            if student_name == "Unknown" and self.openai_api_key and extracted_text:
                student_name = self.extract_name_with_openai(extracted_text[:2000])

            return (student_name, extracted_text[:5000] if extracted_text else None)

        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return ("Unknown", None)

    def extract_name_with_openai(self, text: str) -> str:
        """Extract student name using OpenAI API.

        Args:
            text: The extracted text from the PDF.

        Returns:
            The extracted student name or "Unknown".
        """
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}

            prompt = (
                "Extract the student's full name from the following text. "
                "If you can identify a student name, return ONLY the name. "
                "If no student name can be found, return 'Unknown'. "
                "Do not include titles, prefixes like 'Name:', or any other text.\n\n"
                f"Text:\n{text}"
            )

            data: dict[str, Any] = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts student names from documents.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": 50,
            }

            response = httpx.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                name = result["choices"][0]["message"]["content"].strip()

                cleaned_name = self.clean_student_name(name)

                if cleaned_name != "Unknown":
                    logger.info(f"OpenAI extracted student name: {cleaned_name}")
                    return cleaned_name
            else:
                logger.warning(f"OpenAI API returned status {response.status_code}")

        except httpx.TimeoutException:
            logger.warning("OpenAI API request timed out")
        except Exception as e:
            logger.error(f"Failed to extract name with OpenAI: {e}")

        return "Unknown"

    def clean_student_name(self, name: str) -> str:
        """Clean and validate the extracted student name.

        Args:
            name: The raw extracted name.

        Returns:
            Cleaned student name or "Unknown".
        """
        if not name or name.lower() in ["unknown", "not found", "n/a", "none"]:
            return "Unknown"

        prefixes_to_remove = ["Name:", "Student:", "Author:", "Submitted by:", "By:", "Student Name:"]
        for prefix in prefixes_to_remove:
            if name.lower().startswith(prefix.lower()):
                name = name[len(prefix) :].strip()

        name = re.sub(r"[^a-zA-Z0-9\s\-\'\.]", " ", name)
        name = re.sub(r"\s+", " ", name).strip()

        if not re.search(r"[a-zA-Z]", name):
            return "Unknown"

        if len(name) < 2 or name.replace(" ", "").isdigit():
            return "Unknown"

        if len(name) > 100:
            name = name[:100]

        return name if name else "Unknown"

    def extract_name_from_text(self, text: str) -> str:
        """Extract student name from text using pattern matching."""
        if not text:
            return "Unknown"

        patterns = [
            r"(?:Name|Student|Author|Submitted by|By|Student Name)[\s:]*([A-Z][a-zA-Z]+(?:[ \t]+[A-Z][a-zA-Z]+){1,3})",
            r"^([A-Z][a-zA-Z]+(?:[ \t]+[A-Z][a-zA-Z]+){1,3})$",
            r"^([A-Z][a-zA-Z]+(?:[ \t]+[A-Z][a-zA-Z]+){1,3})[ \t]*\n",
            r"(?:Prepared by|Written by|Created by)[\s:]*([A-Z][a-zA-Z]+(?:[ \t]+[A-Z][a-zA-Z]+){1,3})",
        ]

        for pattern in patterns:
            matches = re.search(pattern, text, re.MULTILINE)
            if matches:
                name = matches.group(1).strip()
                cleaned_name = self.clean_student_name(name)
                if cleaned_name != "Unknown":
                    return cleaned_name

        return "Unknown"

    def upload_deliverable(
        self,
        assignment_id: str,
        filename: str,
        content: bytes,
        extension: str,
        content_type: str,
        extract_name: bool = True,
    ) -> str:
        """Upload a deliverable for an assignment.

        Args:
            assignment_id: The ID of the assignment.
            filename: The name of the file.
            content: The file content as bytes.
            extension: The file extension.
            content_type: The MIME type of the file.
            extract_name: Whether to extract student name from the document.

        Returns:
            The ID of the uploaded deliverable.
        """
        assignment = self.db_repository.get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment with ID {assignment_id} not found")

        student_name = "Unknown"
        extracted_text = None

        if extract_name and extension.lower() == "pdf":
            student_name, extracted_text = self.extract_student_name_from_pdf(content)
            logger.info(f"Extracted student name: {student_name}")

        return self.db_repository.store_deliverable(
            assignment_id=assignment_id,
            filename=filename,
            content=content,
            extension=extension,
            content_type=content_type,
            student_name=student_name,
            extracted_text=extracted_text,
        )

    def upload_multiple_deliverables(
        self, assignment_id: str, files: list[tuple[str, bytes, str, str]], extract_names: bool = True
    ) -> list[str]:
        """Upload multiple deliverables for an assignment.

        Args:
            assignment_id: The ID of the assignment.
            files: List of tuples (filename, content, extension, content_type).
            extract_names: Whether to extract student names from the documents.

        Returns:
            List of IDs of the uploaded deliverables.
        """
        assignment = self.db_repository.get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment with ID {assignment_id} not found")

        deliverable_ids: list[str] = []

        for filename, content, extension, content_type in files:
            try:
                deliverable_id = self.upload_deliverable(
                    assignment_id=assignment_id,
                    filename=filename,
                    content=content,
                    extension=extension,
                    content_type=content_type,
                    extract_name=extract_names,
                )
                deliverable_ids.append(deliverable_id)
            except Exception as e:
                logger.error(f"Failed to upload {filename}: {e}")
                continue

        return deliverable_ids

    def update_deliverable(
        self,
        deliverable_id: str,
        student_name: str | None = None,
        mark: float | None = None,
        certainty_threshold: float | None = None,
    ) -> bool:
        """Update a deliverable's information.

        Args:
            deliverable_id: The ID of the deliverable.
            student_name: Optional new student name.
            mark: Optional mark (0-10).
            certainty_threshold: Optional certainty threshold (0-1).

        Returns:
            True if the deliverable was updated, False otherwise.
        """
        deliverable = self.db_repository.get_deliverable(deliverable_id)
        if not deliverable:
            return False

        update_data: dict[str, float | str] = {}

        if student_name is not None:
            update_data["student_name"] = student_name

        if mark is not None:
            if not 0.0 <= mark <= 10.0:
                raise ValueError("Mark must be between 0.0 and 10.0")
            update_data["mark"] = round(mark, 2)

        if certainty_threshold is not None:
            if not 0.0 <= certainty_threshold <= 1.0:
                raise ValueError("Certainty threshold must be between 0.0 and 1.0")
            update_data["certainty_threshold"] = round(certainty_threshold, 2)

        if not update_data:
            return False

        return self.db_repository.update_deliverable(deliverable_id, **update_data)

    def get_deliverable(self, deliverable_id: str) -> DeliverableModel | None:
        """Get a deliverable by ID.

        Args:
            deliverable_id: The ID of the deliverable.

        Returns:
            The deliverable model if found, otherwise None.
        """
        return self.db_repository.get_deliverable(deliverable_id)

    def list_deliverables(self, assignment_id: str) -> list[DeliverableModel]:
        """List all deliverables for an assignment.

        Args:
            assignment_id: The ID of the assignment.

        Returns:
            A list of deliverables for the assignment.
        """
        return self.db_repository.list_deliverables_by_assignment(assignment_id)

    def delete_deliverable(self, deliverable_id: str) -> bool:
        """Delete a deliverable.

        Args:
            deliverable_id: The ID of the deliverable to delete.

        Returns:
            True if the deliverable was deleted, False otherwise.
        """
        return self.db_repository.delete_deliverable(deliverable_id)

    def validate_file_format(self, filename: str, content_type: str) -> tuple[bool, str]:
        """Validate if the file format is supported.

        Args:
            filename: The name of the file.
            content_type: The MIME type of the file.

        Returns:
            A tuple of (is_valid, error_message).
        """
        supported_extensions = [".pdf"]
        supported_mime_types = ["application/pdf"]

        extension = os.path.splitext(filename)[1].lower()

        if extension not in supported_extensions:
            return (False, f"File format not supported. Supported formats: {', '.join(supported_extensions)}")

        if content_type not in supported_mime_types:
            return (False, f"Content type not supported. Supported types: {', '.join(supported_mime_types)}")

        return (True, "")
