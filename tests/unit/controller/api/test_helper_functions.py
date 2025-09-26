
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.controller.api.api import (
    create_deliverable_response,
    prepare_file_data,
)


class TestHelperFunctions:
    """Tests for the new helper functions."""

    @pytest.mark.asyncio
    async def test_prepare_file_data_valid(self) -> None:
        """Test _prepare_file_data with valid file."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, None)

        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=b"content")

        result = await prepare_file_data(mock_file, mock_service)

        assert result == ("test.pdf", b"content", "pdf", "application/pdf")

    @pytest.mark.asyncio
    async def test_prepare_file_data_no_filename(self) -> None:
        """Test _prepare_file_data with no filename."""
        mock_service = MagicMock()
        mock_file = MagicMock()
        mock_file.filename = None

        result = await prepare_file_data(mock_file, mock_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_prepare_file_data_invalid(self) -> None:
        """Test _prepare_file_data with invalid file."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (False, "Invalid")

        mock_file = MagicMock()
        mock_file.filename = "test.exe"
        mock_file.content_type = "application/exe"

        result = await prepare_file_data(mock_file, mock_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_prepare_file_data_no_extension(self) -> None:
        """Test _prepare_file_data with file without extension."""
        mock_service = MagicMock()
        mock_service.validate_file_format.return_value = (True, None)

        mock_file = MagicMock()
        mock_file.filename = "test"
        mock_file.content_type = None
        mock_file.read = AsyncMock(return_value=b"content")

        result = await prepare_file_data(mock_file, mock_service)

        assert result == ("test", b"content", "", "application/octet-stream")

    def test_create_deliverable_response_success(self) -> None:
        """Test _create_deliverable_response with valid deliverable."""
        mock_service = MagicMock()
        mock_deliverable = MagicMock()
        mock_deliverable.filename = "test.pdf"
        mock_deliverable.student_name = "John Doe"
        mock_deliverable.uploaded_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_service.get_deliverable.return_value = mock_deliverable

        result = create_deliverable_response("deliverable_id", mock_service)

        assert result is not None
        assert result.id == "deliverable_id"
        assert result.filename == "test.pdf"
        assert result.student_name == "John Doe"
        assert result.message == "Uploaded successfully"

    def test_create_deliverable_response_not_found(self) -> None:
        """Test _create_deliverable_response when deliverable not found."""
        mock_service = MagicMock()
        mock_service.get_deliverable.return_value = None

        result = create_deliverable_response("deliverable_id", mock_service)

        assert result is None
