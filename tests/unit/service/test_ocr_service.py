from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.service.ocr_service import OCRService


class TestOCRService:
    """Tests for OCRService."""

    @patch("src.service.ocr_service.get_config")
    def test_init(self, mock_get_config: MagicMock) -> None:
        """Test OCRService initialization."""
        mock_config = MagicMock()
        mock_config.ocr.base_url = "https://api.mistral.ai/v1"
        mock_config.ocr.model = "mistral-ocr"
        mock_config.ocr.provider = "mistral"
        mock_get_config.return_value = mock_config

        with patch.dict("os.environ", {"OCR_API_KEY": "test_ocr_key"}):
            service = OCRService()
            assert service.api_key == "test_ocr_key"
            assert service.base_url == "https://api.mistral.ai/v1"
            assert service.model == "mistral-ocr"

    @pytest.mark.asyncio
    @patch("src.service.ocr_service.get_config")
    @patch("src.service.ocr_service.httpx.AsyncClient")
    async def test_extract_text_from_pdf_success(self, mock_client_cls: MagicMock, mock_get_config: MagicMock) -> None:
        """Test successful text extraction."""
        mock_config = MagicMock()
        mock_config.ocr.provider = "mistral"
        mock_config.ocr.base_url = "https://api.mistral.ai/v1"
        mock_config.ocr.model = "mistral-ocr"
        mock_get_config.return_value = mock_config

        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pages": [{"markdown": "# Page 1\nContent"}, {"markdown": "# Page 2\nMore Content"}]
        }
        mock_client.post.return_value = mock_response

        with patch.dict("os.environ", {"OCR_API_KEY": "test_key"}):
            service = OCRService()
            result = await service.extract_text_from_pdf(b"fake pdf content")

            assert result == "# Page 1\nContent\n\n# Page 2\nMore Content"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.service.ocr_service.get_config")
    @patch("src.service.ocr_service.httpx.AsyncClient")
    async def test_extract_text_from_pdf_api_failure(
        self, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test text extraction when API fails."""
        mock_config = MagicMock()
        mock_config.ocr.provider = "mistral"
        mock_config.ocr.base_url = "https://api.mistral.ai/v1"
        mock_config.ocr.model = "mistral-ocr"
        mock_get_config.return_value = mock_config

        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_client.post.return_value = mock_response

        with patch.dict("os.environ", {"OCR_API_KEY": "test_key"}):
            service = OCRService()
            result = await service.extract_text_from_pdf(b"content")

            assert result is None

    @pytest.mark.asyncio
    @patch("src.service.ocr_service.get_config")
    @patch("src.service.ocr_service.httpx.AsyncClient")
    async def test_extract_text_from_pdf_malformed_response(
        self, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test text extraction with unexpected response format."""
        mock_config = MagicMock()
        mock_config.ocr.provider = "mistral"
        mock_config.ocr.base_url = "https://api.mistral.ai/v1"
        mock_config.ocr.model = "mistral-ocr"
        mock_get_config.return_value = mock_config

        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "data"}  # Missing "pages"
        mock_client.post.return_value = mock_response

        with patch.dict("os.environ", {"OCR_API_KEY": "test_key"}):
            service = OCRService()
            result = await service.extract_text_from_pdf(b"content")

            assert result == ""

    @pytest.mark.asyncio
    @patch("src.service.ocr_service.get_config")
    async def test_extract_text_from_pdf_missing_config(self, mock_get_config: MagicMock) -> None:
        """Test OCR skipped if config/key missing."""
        mock_config = MagicMock()
        mock_config.ocr.provider = "other"  # Not mistral
        mock_get_config.return_value = mock_config

        service = OCRService()  # API key empty by default if not in env
        result = await service.extract_text_from_pdf(b"content")
        assert result is None

    @pytest.mark.asyncio
    @patch("src.service.ocr_service.get_config")
    @patch("src.service.ocr_service.httpx.AsyncClient")
    async def test_extract_text_from_pdf_exception(
        self, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test text extraction when exception occurs."""
        mock_config = MagicMock()
        mock_config.ocr.provider = "mistral"
        mock_config.ocr.base_url = "https://api.mistral.ai/v1"
        mock_config.ocr.model = "mistral-ocr"
        mock_get_config.return_value = mock_config

        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = Exception("Network Error")

        with patch.dict("os.environ", {"OCR_API_KEY": "test_key"}):
            service = OCRService()
            result = await service.extract_text_from_pdf(b"content")

            assert result is None
