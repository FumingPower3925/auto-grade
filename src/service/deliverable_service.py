import os
import re
import base64
from typing import List, Optional, Tuple
from src.repository.db.factory import get_database_repository
from src.repository.db.models import DeliverableModel
import requests
import json


class DeliverableService:
    """Service for handling deliverable operations."""

    def __init__(self) -> None:
        self.db_repository = get_database_repository()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    def extract_student_name_from_pdf(self, pdf_content: bytes) -> Tuple[str, Optional[str]]:
        """Extract student name from PDF content using OpenAI API.
        
        Args:
            pdf_content: The PDF content as bytes.
            
        Returns:
            A tuple of (student_name, extracted_text).
        """
        if not self.openai_api_key:
            return ("Unknown", None)
        
        try:
            base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }
            
            # Note: In production, you'd use a proper PDF to text extraction library first
            # For now, we'll simulate with a text extraction request
            # In reality, you'd need to convert PDF to images or use a PDF extraction service
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts student names from academic documents. "
                                   "Look for patterns like 'Name:', 'Student:', 'Author:', 'Submitted by:', "
                                   "or names at the beginning of the document. Return ONLY the student name or 'Unknown' if not found."
                    },
                    {
                        "role": "user",
                        "content": "Extract the student name from this document. Return only the name or 'Unknown'."
                    }
                ],
                "max_tokens": 50,
                "temperature": 0
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                student_name = result.get("choices", [{}])[0].get("message", {}).get("content", "Unknown").strip()
                
                student_name = self._clean_student_name(student_name)
                
                return (student_name, None)
            else:
                return ("Unknown", None)
                
        except Exception:
            return ("Unknown", None)

    def _clean_student_name(self, name: str) -> str:
        """Clean and validate the extracted student name.
        
        Args:
            name: The raw extracted name.
            
        Returns:
            Cleaned student name or "Unknown".
        """
        if not name or name.lower() in ["unknown", "not found", "n/a", "none"]:
            return "Unknown"
        
        prefixes_to_remove = ["Name:", "Student:", "Author:", "Submitted by:", "By:"]
        for prefix in prefixes_to_remove:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
        
        name = re.sub(r'[^a-zA-Z0-9\s\-\']', '', name).strip()
        
        if not re.search(r'[a-zA-Z]', name):
            return "Unknown"
        
        if len(name) > 100:
            name = name[:100]
        
        return name if name else "Unknown"

    def upload_deliverable(self, assignment_id: str, filename: str, content: bytes,
                          extension: str, content_type: str,
                          extract_name: bool = True) -> str:
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
        
        return self.db_repository.store_deliverable(
            assignment_id=assignment_id,
            filename=filename,
            content=content,
            extension=extension,
            content_type=content_type,
            student_name=student_name,
            extracted_text=extracted_text
        )

    def upload_multiple_deliverables(self, assignment_id: str, 
                                    files: List[Tuple[str, bytes, str, str]],
                                    extract_names: bool = True) -> List[str]:
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
        
        deliverable_ids: List[str] = []
        
        for filename, content, extension, content_type in files:
            try:
                deliverable_id = self.upload_deliverable(
                    assignment_id=assignment_id,
                    filename=filename,
                    content=content,
                    extension=extension,
                    content_type=content_type,
                    extract_name=extract_names
                )
                deliverable_ids.append(deliverable_id)
            except Exception:
                continue
        
        return deliverable_ids

    def update_deliverable(self, deliverable_id: str, student_name: Optional[str] = None,
                          mark: Optional[float] = None, 
                          certainty_threshold: Optional[float] = None) -> bool:
        """Update a deliverable's information.
        
        Args:
            deliverable_id: The ID of the deliverable.
            student_name: Optional new student name.
            mark: Optional mark (0-100).
            certainty_threshold: Optional certainty threshold (0-1).
            
        Returns:
            True if the deliverable was updated, False otherwise.
        """
        # Check if deliverable exists
        deliverable = self.db_repository.get_deliverable(deliverable_id)
        if not deliverable:
            return False
        
        # Prepare update data
        update_data: dict[str, float | str] = {}
        
        if student_name is not None:
            update_data["student_name"] = student_name
        
        if mark is not None:
            if not 0.0 <= mark <= 100.0:
                raise ValueError("Mark must be between 0.0 and 100.0")
            update_data["mark"] = round(mark, 2)
        
        if certainty_threshold is not None:
            if not 0.0 <= certainty_threshold <= 1.0:
                raise ValueError("Certainty threshold must be between 0.0 and 1.0")
            update_data["certainty_threshold"] = round(certainty_threshold, 2)
        
        if not update_data:
            return False
        
        return self.db_repository.update_deliverable(deliverable_id, **update_data)

    def get_deliverable(self, deliverable_id: str) -> Optional[DeliverableModel]:
        """Get a deliverable by ID.
        
        Args:
            deliverable_id: The ID of the deliverable.
            
        Returns:
            The deliverable model if found, otherwise None.
        """
        return self.db_repository.get_deliverable(deliverable_id)

    def list_deliverables(self, assignment_id: str) -> List[DeliverableModel]:
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

    def validate_file_format(self, filename: str, content_type: str) -> Tuple[bool, str]:
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