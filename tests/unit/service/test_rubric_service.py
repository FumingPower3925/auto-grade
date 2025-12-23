from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.service.rubric_service import RubricService


class TestRubricService:
    """Tests for RubricService."""

    @patch("src.service.rubric_service.get_config")
    def test_init(self, mock_get_config: MagicMock) -> None:
        """Test RubricService initialization."""
        mock_config = MagicMock()
        mock_config.llm.base_url = "https://api.test.com/v1"
        mock_config.llm.model = "test-model"
        mock_get_config.return_value = mock_config

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            assert service.llm_api_key == "test_key"
            assert service.llm_base_url == "https://api.test.com/v1"
            assert service.llm_model == "test-model"

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.PdfReader")
    def test_extract_text_from_pdf_success(self, mock_pdf_reader: MagicMock, mock_get_config: MagicMock) -> None:
        """Test successful PDF text extraction."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        service = RubricService()
        result = service.extract_text_from_pdf(b"pdf content")

        assert "Page 1 content" in result
        assert "Page 2 content" in result

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.PdfReader")
    def test_extract_text_from_pdf_page_error(
        self, mock_pdf_reader: MagicMock, mock_get_config: MagicMock
    ) -> None:
        """Test PDF extraction when a page fails."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.side_effect = Exception("Page error")
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader

        service = RubricService()
        result = service.extract_text_from_pdf(b"pdf content")

        assert "Page 2 content" in result

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.PdfReader")
    def test_extract_text_from_pdf_exception(self, mock_pdf_reader: MagicMock, mock_get_config: MagicMock) -> None:
        """Test PDF extraction when PdfReader fails."""
        mock_pdf_reader.side_effect = Exception("PDF error")

        service = RubricService()
        result = service.extract_text_from_pdf(b"invalid content")

        assert result == ""

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_extract_rubric_with_llm_success(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test successful LLM rubric extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """{
                            "title": "Test Rubric",
                            "total_points": 100,
                            "criteria": [
                                {"name": "Quality", "description": "Code quality", "max_points": 50, "weight": 0.5}
                            ]
                        }"""
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service.extract_rubric_with_llm("Rubric text")

            assert result.title == "Test Rubric"
            assert result.total_points == 100
            assert len(result.criteria) == 1
            assert result.criteria[0].name == "Quality"
            assert result.criteria[0].max_points == 50
            assert result.criteria[0].weight == 0.5

    @patch("src.service.rubric_service.get_config")
    def test_extract_rubric_with_llm_no_api_key(self, mock_get_config: MagicMock) -> None:
        """Test LLM extraction without API key."""
        with patch.dict("os.environ", {"LLM_API_KEY": ""}):
            service = RubricService()
            result = service.extract_rubric_with_llm("Rubric text")

            assert result.raw_text == "Rubric text"
            assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    def test_extract_rubric_with_llm_empty_text(self, mock_get_config: MagicMock) -> None:
        """Test LLM extraction with empty text."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service.extract_rubric_with_llm("")

            assert result.raw_text is None
            assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_extract_rubric_with_llm_non_200_status(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test LLM extraction with non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service.extract_rubric_with_llm("Rubric text")

            assert result.raw_text == "Rubric text"

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_extract_rubric_with_llm_timeout(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test LLM extraction with timeout."""
        mock_post.side_effect = httpx.TimeoutException("Timeout")

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service.extract_rubric_with_llm("Rubric text")

            assert result.raw_text == "Rubric text"

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_extract_rubric_with_llm_exception(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test LLM extraction with general exception."""
        mock_post.side_effect = Exception("API error")

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service.extract_rubric_with_llm("Rubric text")

            assert result.raw_text == "Rubric text"

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_extract_rubric_with_llm_invalid_json(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test LLM extraction with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "not valid json"}}]}
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service.extract_rubric_with_llm("Rubric text")

            assert result.raw_text == "Rubric text"

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_extract_rubric_with_llm_partial_criteria(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test LLM extraction with criteria missing required fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """{
                            "title": "Test",
                            "criteria": [
                                {"name": "Good", "max_points": 10},
                                {"description": "Missing name"}
                            ]
                        }"""
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service.extract_rubric_with_llm("Rubric text")

            assert len(result.criteria) == 2
            assert result.criteria[0].name == "Good"
            assert result.criteria[1].name == "Unnamed Criterion"

    @patch("src.service.rubric_service.get_config")
    def test_build_extraction_prompt(self, mock_get_config: MagicMock) -> None:
        """Test prompt building."""
        service = RubricService()
        prompt = service._build_extraction_prompt("Test rubric content")

        assert "Test rubric content" in prompt
        assert "JSON" in prompt

    @patch("src.service.rubric_service.get_config")
    def test_parse_rubric_pdf(self, mock_get_config: MagicMock) -> None:
        """Test parse_rubric with PDF content type."""
        service = RubricService()

        with patch.object(service, "extract_text_from_pdf", return_value="Rubric text") as mock_extract:
            with patch.object(service, "extract_rubric_with_llm") as mock_llm:
                mock_llm.return_value = MagicMock(criteria=[])
                service.parse_rubric(b"pdf content", "application/pdf")

                mock_extract.assert_called_once_with(b"pdf content")
                mock_llm.assert_called_once_with("Rubric text")

    @patch("src.service.rubric_service.get_config")
    def test_parse_rubric_unsupported_type(self, mock_get_config: MagicMock) -> None:
        """Test parse_rubric with unsupported content type."""
        service = RubricService()
        result = service.parse_rubric(b"content", "text/plain")

        assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    def test_parse_rubric_empty_text(self, mock_get_config: MagicMock) -> None:
        """Test parse_rubric when PDF has no text."""
        service = RubricService()

        with patch.object(service, "extract_text_from_pdf", return_value=""):
            result = service.parse_rubric(b"pdf content", "application/pdf")

            assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_parse_llm_response_no_json(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test parsing LLM response with no JSON block."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response("No JSON here", "raw text")

            assert result.raw_text == "raw text"

    @patch("src.service.rubric_service.get_config")
    def test_parse_llm_response_malformed_json(self, mock_get_config: MagicMock) -> None:
        """Test parsing LLM response with malformed JSON that triggers JSONDecodeError."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response('{"title": "Test", "criteria": [invalid]}', "raw text")

            assert result.raw_text == "raw text"
            assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_parse_llm_response_null_total_points(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test parsing LLM response with null total_points."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response('{"title": "Test", "total_points": null, "criteria": []}', "raw")

            assert result.total_points is None

    @patch("src.service.rubric_service.get_config")
    @patch("src.service.rubric_service.httpx.post")
    def test_parse_llm_response_invalid_total_points(self, mock_post: MagicMock, mock_get_config: MagicMock) -> None:
        """Test parsing LLM response with invalid total_points."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            result = service._parse_llm_response('{"title": "Test", "total_points": "invalid", "criteria": []}', "raw")

            assert result.total_points is None

    @patch("src.service.rubric_service.get_config")
    def test_parse_llm_response_criterion_with_invalid_weight(self, mock_get_config: MagicMock) -> None:
        """Test parsing criterion with invalid weight value that causes ValueError."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            json_content = '{"title": "Test", "criteria": [{"name": "C1", "max_points": 10, "weight": "invalid"}]}'
            result = service._parse_llm_response(json_content, "raw")

            assert len(result.criteria) == 0

    @patch("src.service.rubric_service.get_config")
    def test_parse_llm_response_criterion_with_invalid_max_points(self, mock_get_config: MagicMock) -> None:
        """Test parsing criterion with invalid max_points that causes ValueError."""
        with patch.dict("os.environ", {"LLM_API_KEY": "test_key"}):
            service = RubricService()
            json_content = '{"title": "Test", "criteria": [{"name": "C1", "max_points": "not_a_number"}]}'
            result = service._parse_llm_response(json_content, "raw")

            assert len(result.criteria) == 0

