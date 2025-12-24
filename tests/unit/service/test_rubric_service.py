from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.repository.db.models import ExtractedRubricModel
from src.service.rubric_service import RubricService


class TestRubricService:
    """Tests for RubricService."""

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    def test_init(self, mock_ocr_service_cls: MagicMock, mock_get_config: MagicMock) -> None:
        """Test RubricService initialization."""
        mock_config = MagicMock()
        mock_config.llm.base_url = "https://api.test.com/v1"
        mock_config.llm.default_model = "default-model"
        mock_config.llm.smart_model = "smart-model"
        mock_get_config.return_value = mock_config

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            assert service.llm_api_key == "test_key"
            assert service.llm_base_url == "https://api.test.com/v1"
            assert service.default_model == "default-model"
            assert service.smart_model == "smart-model"
            mock_ocr_service_cls.assert_called_once()

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.PdfReader")
    @patch("src.service.rubric_service.OCRService")
    def test_extract_text_from_pdf_raw(
        self, mock_ocr_service: MagicMock, mock_pdf_reader: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test raw PDF text extraction."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page content"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        service = RubricService()
        result = service.extract_text_from_pdf_raw(b"pdf content")
        assert result == "Page content"

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    @patch("src.service.rubric_service.httpx.AsyncClient")
    async def test_try_llm_extraction_success(
        self, mock_client_cls: MagicMock, mock_ocr_service: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test successful LLM extraction."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"title": "Test", "criteria": []}'}}]
        }
        mock_client.post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = await service._try_llm_extraction("text", "model")

            assert result is not None
            assert result.title == "Test"

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    async def test_parse_rubric_fallback_strategy_ocr_default_success(
        self, mock_ocr_service_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test strategy 1: OCR succeeds, Default Model succeeds."""
        mock_ocr_instance = AsyncMock()
        mock_ocr_instance.extract_text_from_pdf.return_value = "OCR Text"
        mock_ocr_service_cls.return_value = mock_ocr_instance

        mock_config = MagicMock()
        mock_config.llm.default_model = "default"
        mock_get_config.return_value = mock_config

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()

            # Mock _try_llm_extraction
            with patch.object(service, "_try_llm_extraction", new_callable=AsyncMock) as mock_try:
                mock_try.side_effect = [ExtractedRubricModel(title="Success"), None]

                result = await service.parse_rubric(b"content", "application/pdf")

                assert result.title == "Success"
                mock_ocr_instance.extract_text_from_pdf.assert_called_once()
                mock_try.assert_called_with("OCR Text", "default")

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    async def test_parse_rubric_fallback_strategy_ocr_smart_success(
        self, mock_ocr_service_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test strategy 2: OCR succeeds, Default fails, Smart succeeds."""
        mock_ocr_instance = AsyncMock()
        mock_ocr_instance.extract_text_from_pdf.return_value = "OCR Text"
        mock_ocr_service_cls.return_value = mock_ocr_instance

        mock_config = MagicMock()
        mock_config.llm.default_model = "default"
        mock_config.llm.smart_model = "smart"
        mock_get_config.return_value = mock_config

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()

            with patch.object(service, "_try_llm_extraction", new_callable=AsyncMock) as mock_try:
                # First call returns None (Default), Second returns Success (Smart)
                mock_try.side_effect = [None, ExtractedRubricModel(title="Success")]

                result = await service.parse_rubric(b"content", "application/pdf")

                assert result.title == "Success"
                assert mock_try.call_count == 2
                mock_try.assert_any_call("OCR Text", "default")
                mock_try.assert_any_call("OCR Text", "smart")

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    @patch("src.service.rubric_service.PdfReader")
    async def test_parse_rubric_fallback_strategy_raw_smart_success(
        self, mock_pdf_reader: MagicMock, mock_ocr_service_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test strategy 3: OCR fails/skipped, Raw PDF + Smart succeeds."""
        mock_ocr_instance = AsyncMock()
        mock_ocr_instance.extract_text_from_pdf.return_value = None # OCR Fails
        mock_ocr_service_cls.return_value = mock_ocr_instance

        mock_config = MagicMock()
        mock_config.llm.smart_model = "smart"
        mock_get_config.return_value = mock_config

        # Mock PDF Reader for raw extraction
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Raw Text"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()

            with patch.object(service, "_try_llm_extraction", new_callable=AsyncMock) as mock_try:
                mock_try.return_value = ExtractedRubricModel(title="Success")

                result = await service.parse_rubric(b"content", "application/pdf")

                assert result.title == "Success"
                mock_ocr_instance.extract_text_from_pdf.assert_called_once()
                mock_try.assert_called_with("Raw Text", "smart")

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    @patch("src.service.rubric_service.PdfReader")
    async def test_parse_rubric_all_fail(
        self, mock_pdf_reader: MagicMock, mock_ocr_service_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test parsing when all strategies fail."""
        mock_ocr_instance = AsyncMock()
        mock_ocr_instance.extract_text_from_pdf.return_value = "OCR Text"
        mock_ocr_service_cls.return_value = mock_ocr_instance

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Raw Text"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()

            with patch.object(service, "_try_llm_extraction", new_callable=AsyncMock) as mock_try:
                mock_try.return_value = None # All LLM calls fail

                result = await service.parse_rubric(b"content", "application/pdf")

                # Should return a model with raw text (ocr text preferred if available, or raw)
                # In implementation: return ExtractedRubricModel(raw_text=ocr_text if ocr_text else raw_text)
                assert result.raw_text == "OCR Text"
                assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    def test_parse_llm_response_success(self, mock_ocr_service: MagicMock, mock_get_config: MagicMock) -> None:
        """Test successful parsing of LLM response."""
        json_content = """{
            "title": "Test Rubric",
            "total_points": 100,
            "criteria": [
                {"name": "Quality", "max_points": 50, "weight": 0.5}
            ]
        }"""

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response(json_content, "raw text")

            assert result.title == "Test Rubric"
            assert len(result.criteria) == 1
            assert result.criteria[0].name == "Quality"

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    def test_parse_llm_response_invalid_json(self, mock_ocr_service: MagicMock, mock_get_config: MagicMock) -> None:
        """Test parsing invalid JSON."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            # Use valid outer brackets but invalid inner content to trigger JSONDecodeError
            result = service._parse_llm_response('{"invalid json"}', "raw text")
            assert result.raw_text == "raw text"
            assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    def test_parse_llm_response_validation_error(self, mock_ocr_service: MagicMock, mock_get_config: MagicMock) -> None:
        """Test parsing JSON with schema validation error."""
        json_content = """{
            "title": "Test",
            "criteria": [{"name": "C1", "max_points": "invalid"}]
        }"""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response(json_content, "raw")
            # Should handle exception and continue parsing other criteria or return partial
            assert len(result.criteria) == 0

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.AsyncClient")
    @patch("src.service.rubric_service.OCRService")
    async def test_try_llm_extraction_api_failure(
        self, mock_ocr_cls: MagicMock, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test extraction when API returns validation error or bad status."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value.status_code = 400

        with patch.dict("os.environ", {"LLM_API_KEY": "key"}):
            service = RubricService()
            result = await service._try_llm_extraction("text", "model")
            assert result is None

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.AsyncClient")
    @patch("src.service.rubric_service.OCRService")
    async def test_try_llm_extraction_no_json(
        self, mock_ocr_cls: MagicMock, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test extraction when response has no JSON."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Just text, no json"}}]
        }
        mock_client.post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "key"}):
            service = RubricService()
            result = await service._try_llm_extraction("text", "model")
            assert result is None

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.AsyncClient")
    @patch("src.service.rubric_service.OCRService")
    async def test_try_llm_extraction_o_series_model(
        self, mock_ocr_cls: MagicMock, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test extraction using O-series model."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"title": "O-Series", "criteria": []}'}}]
        }
        mock_client.post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "key"}):
            service = RubricService()
            # Pass a model starting with 'o'
            result = await service._try_llm_extraction("text", "o1-preview")
            assert result is not None
            assert result.title == "O-Series"

            # Verify request payload used max_completion_tokens
            call_kwargs = mock_client.post.call_args.kwargs
            assert "max_completion_tokens" in call_kwargs["json"]
            assert "max_tokens" not in call_kwargs["json"]

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    @patch("src.service.rubric_service.PdfReader")
    def test_extract_text_from_pdf_raw_exception(
        self, mock_pdf_reader: MagicMock, mock_ocr_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test exception handling in raw PDF extraction."""
        mock_pdf_reader.side_effect = Exception("PDF Error")

        service = RubricService()
        result = service.extract_text_from_pdf_raw(b"bad content")
        assert result == ""

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    @patch("src.service.rubric_service.PdfReader")
    def test_extract_text_from_pdf_raw_page_exception(
        self, mock_pdf_reader: MagicMock, mock_ocr_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test exception handling during page extraction."""
        mock_page_ok = MagicMock()
        mock_page_ok.extract_text.return_value = "Page 1"

        mock_page_error = MagicMock()
        mock_page_error.extract_text.side_effect = Exception("Page Error")

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page_ok, mock_page_error]
        mock_pdf_reader.return_value = mock_reader

        service = RubricService()
        result = service.extract_text_from_pdf_raw(b"content")
        assert "Page 1" in result

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    def test_parse_llm_response_grade_parsing_error(self, mock_ocr_cls: MagicMock, mock_get_config: MagicMock) -> None:
        """Test partial parsing when some grades/criteria are invalid."""
        json_content = """{
            "title": "Partial",
            "criteria": [
                {
                    "name": "C1", "max_points": 10, "weight": 1.0,
                    "grades": [{"label": "A", "points": "invalid"}]
                },
                {
                    "name": "C2", "max_points": 10, "weight": 1.0,
                    "grades": [{"label": "A", "points": 10}]
                }
            ]
        }"""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response(json_content, "raw")
            # C1 will have empty grades list
            assert len(result.criteria) == 2
            assert len(result.criteria[0].grades) == 0
            assert len(result.criteria[1].grades) == 1

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    async def test_parse_rubric_unsupported_content_type(
        self, mock_ocr_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test early return for unsupported content type."""
        service = RubricService()
        result = await service.parse_rubric(b"content", "image/png")
        assert result.criteria == []
        assert result.title is None

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    async def test_try_llm_extraction_missing_api_key(
        self, mock_ocr_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test extraction returns None if API key missing."""
        with patch.dict("os.environ", {"LLM_API_KEY": ""}):
            service = RubricService()
            result = await service._try_llm_extraction("text", "model")
            assert result is None

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.AsyncClient")
    @patch("src.service.rubric_service.OCRService")
    async def test_try_llm_extraction_exception(
        self, mock_ocr_cls: MagicMock, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test general exception handling in extraction."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = Exception("Network Error")

        with patch.dict("os.environ", {"LLM_API_KEY": "key"}):
            service = RubricService()
            result = await service._try_llm_extraction("text", "model")
            assert result is None

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    def test_parse_llm_response_total_points_error(self, mock_ocr_cls: MagicMock, mock_get_config: MagicMock) -> None:
        """Test parsing when total_points is invalid."""
        json_content = """{
            "title": "Test",
            "total_points": "invalid",
            "criteria": []
        }"""
        with patch.dict("os.environ", {"LLM_API_KEY": "key"}):
            service = RubricService()
            result = service._parse_llm_response(json_content, "raw")
            assert result.total_points is None

    @pytest.mark.asyncio
    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.AsyncClient")
    @patch("src.service.rubric_service.OCRService")
    async def test_try_llm_extraction_empty_result(
        self, mock_ocr_cls: MagicMock, mock_client_cls: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test extraction when parsed result is empty (pass branch coverage)."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # Valid JSON but no title/criteria
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"other": "data"}'}}]
        }
        mock_client.post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "key"}):
            service = RubricService()
            result = await service._try_llm_extraction("text", "model")
            assert result is not None
            assert result.criteria == []
            assert result.title is None

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.OCRService")
    def test_parse_llm_response_no_json(self, mock_ocr_service: MagicMock, mock_get_config: MagicMock) -> None:
        """Test parsing when no JSON block is found."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response("Just plain text", "raw text")
            assert result.raw_text == "raw text"
