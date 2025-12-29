"""Tests for EmbeddingService."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import at module level so Python can find it
from src.service import embedding_service


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    def _create_mock_config(self) -> MagicMock:
        """Create a mock config."""
        mock_config = MagicMock()
        mock_config.embedding.model = "text-embedding-3-small"
        mock_config.embedding.dimensions = 1536
        mock_config.llm.base_url = "https://api.openai.com/v1"
        return mock_config

    def test_init_success(self) -> None:
        """Test successful initialization."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI") as mock_openai_class:
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()

                    assert service.embedding_config.model == "text-embedding-3-small"
                    mock_openai_class.assert_called_once()

    def test_init_missing_api_key(self) -> None:
        """Test initialization fails without API key."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "EMBEDDING_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            with patch.object(embedding_service, "get_config") as mock_get_config:
                mock_get_config.return_value = self._create_mock_config()

                with pytest.raises(ValueError, match="EMBEDDING_API_KEY environment variable is required"):
                    embedding_service.EmbeddingService()

    def test_generate_embedding_success(self) -> None:
        """Test successful embedding generation."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI") as mock_openai_class:
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
                    mock_client.embeddings.create.return_value = mock_response
                    mock_openai_class.return_value = mock_client

                    service = embedding_service.EmbeddingService()
                    result = service.generate_embedding("test text")

                    assert len(result) == 1536
                    mock_client.embeddings.create.assert_called_once()

    def test_generate_embedding_empty_text(self) -> None:
        """Test embedding generation with empty text returns zero vector."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    result = service.generate_embedding("")

                    assert len(result) == 1536
                    assert result == [pytest.approx(0.0)] * 1536

    def test_generate_embedding_whitespace_text(self) -> None:
        """Test embedding generation with whitespace-only text returns zero vector."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    result = service.generate_embedding("   ")

                    assert len(result) == 1536
                    assert result == [pytest.approx(0.0)] * 1536

    def test_generate_embedding_truncates_long_text(self) -> None:
        """Test embedding generation truncates very long text."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI") as mock_openai_class:
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
                    mock_client.embeddings.create.return_value = mock_response
                    mock_openai_class.return_value = mock_client

                    service = embedding_service.EmbeddingService()
                    long_text = "a" * 40000
                    result = service.generate_embedding(long_text)

                    assert len(result) == 1536
                    call_args = mock_client.embeddings.create.call_args
                    assert len(call_args.kwargs["input"]) == 24000

    def test_generate_embedding_api_error(self) -> None:
        """Test embedding generation handles API errors."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI") as mock_openai_class:
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    mock_client = MagicMock()
                    mock_client.embeddings.create.side_effect = Exception("API error")
                    mock_openai_class.return_value = mock_client

                    service = embedding_service.EmbeddingService()

                    with pytest.raises(Exception, match="API error"):
                        service.generate_embedding("test text")

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_success(self) -> None:
        """Test PDF text extraction."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()

                    with (
                        patch("pypdf.PdfReader") as mock_reader_class,
                        patch("pypdf.PdfWriter") as mock_writer_class,
                    ):  # Mock PdfWriter too
                        mock_page = MagicMock()
                        mock_page.extract_text.return_value = "page content " * 5  # > 50 chars to avoid OCR
                        mock_page.mediabox.width = 50
                        mock_page.mediabox.height = 50
                        mock_reader = MagicMock()
                        mock_reader.pages = [mock_page]
                        mock_reader_class.return_value = mock_reader

                        mock_writer = MagicMock()
                        mock_writer_class.return_value = mock_writer

                        text = await service._extract_text_from_pdf_robust(b"pdf content")

                    assert text == "page content " * 5

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_multiple_pages(self) -> None:
        """Test PDF text extraction with multiple pages."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()

                    with patch("pypdf.PdfReader") as mock_reader_class, patch("pypdf.PdfWriter") as mock_writer_class:
                        mock_page1 = MagicMock()
                        mock_page1.extract_text.return_value = "page 1 " * 10
                        mock_page1.mediabox.width = 50
                        mock_page1.mediabox.height = 50
                        mock_page2 = MagicMock()
                        mock_page2.extract_text.return_value = "page 2 " * 10
                        mock_page2.mediabox.width = 50
                        mock_page2.mediabox.height = 50
                        mock_reader = MagicMock()
                        mock_reader.pages = [mock_page1, mock_page2]
                        mock_reader_class.return_value = mock_reader

                        mock_writer = MagicMock()
                        mock_writer_class.return_value = mock_writer

                        text = await service._extract_text_from_pdf_robust(b"pdf content")

                    assert text == ("page 1 " * 10) + "\n\n" + ("page 2 " * 10)

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_empty_page(self) -> None:
        """Test PDF text extraction with empty pages."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()

                    with patch("pypdf.PdfReader") as mock_reader_class:
                        mock_page = MagicMock()
                        mock_page.extract_text.return_value = None
                        mock_page.mediabox.width = 500
                        mock_page.mediabox.height = 800
                        mock_reader = MagicMock()
                        mock_reader.pages = [mock_page]
                        mock_reader_class.return_value = mock_reader

                        text = await service._extract_text_from_pdf_robust(b"pdf content")

                    assert text == ""

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_error(self) -> None:
        """Test PDF text extraction handles errors."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    text = await service._extract_text_from_pdf_robust(b"not a pdf")

                    assert text == ""

    @pytest.mark.asyncio
    async def test_extract_text_from_content_pdf(self) -> None:
        """Test content extraction for PDF."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()

                    with patch.object(service, "_extract_text_from_pdf_robust", return_value="pdf text"):
                        text = await service.extract_text_from_content(b"pdf content", "application/pdf")

                    assert text == "pdf text"

    @pytest.mark.asyncio
    async def test_extract_text_from_content_text_plain(self) -> None:
        """Test content extraction for text/plain files."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    text = await service.extract_text_from_content(b"plain text content", "text/plain")

                    assert text == "plain text content"

    @pytest.mark.asyncio
    async def test_extract_text_from_content_text_html(self) -> None:
        """Test content extraction for text/html files."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    text = await service.extract_text_from_content(b"<html>content</html>", "text/html")

                    assert text == "<html>content</html>"

    @pytest.mark.asyncio
    async def test_extract_text_from_content_unsupported(self) -> None:
        """Test content extraction for unsupported types."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    text = await service.extract_text_from_content(b"image data", "image/png")

                    assert text == ""

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_low_density_triggers_ocr(self) -> None:
        """Test that low density text triggers OCR."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    service.ocr_service.extract_text_from_pdf = AsyncMock(return_value="OCR Text")

                    with patch("pypdf.PdfReader") as mock_reader_class, patch("pypdf.PdfWriter") as mock_writer_class:
                        mock_page = MagicMock()
                        # Short text with large area -> Low density
                        mock_page.extract_text.return_value = "Short text"
                        mock_page.mediabox.width = 1000
                        mock_page.mediabox.height = 1000

                        mock_reader = MagicMock()
                        mock_reader.pages = [mock_page]
                        mock_reader_class.return_value = mock_reader

                        mock_writer = MagicMock()
                        mock_writer_class.return_value = mock_writer

                        text = await service._extract_text_from_pdf_robust(b"pdf content")

                    # Should have triggered OCR
                    service.ocr_service.extract_text_from_pdf.assert_called_once()
                    assert text == "OCR Text"

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_ocr_failure(self) -> None:
        """Test OCR failure handling (returns empty string for that page)."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()
                    # OCR returns None or raises? Code handles `if result: ... else: warning`.
                    # Mock return value as None (failed/empty)
                    service.ocr_service.extract_text_from_pdf = AsyncMock(return_value=None)

                    with patch("pypdf.PdfReader") as mock_reader_class, patch("pypdf.PdfWriter") as mock_writer_class:
                        mock_page = MagicMock()
                        mock_page.extract_text.return_value = " "  # Empty/Low density
                        mock_page.mediabox.width = 1000
                        mock_page.mediabox.height = 1000

                        mock_reader = MagicMock()
                        mock_reader.pages = [mock_page]
                        mock_reader_class.return_value = mock_reader
                        mock_writer_class.return_value = MagicMock()

                        text = await service._extract_text_from_pdf_robust(b"pdf content")

                    assert text == ""

    def test_chunk_text(self) -> None:
        """Test chunk_text wrapper."""
        with patch.dict(os.environ, {"EMBEDDING_API_KEY": "test-key"}):
            with patch.object(embedding_service, "OpenAI"):
                with patch.object(embedding_service, "get_config") as mock_get_config:
                    mock_get_config.return_value = self._create_mock_config()

                    service = embedding_service.EmbeddingService()

                    # Test empty
                    assert service.chunk_text("") == []
                    assert service.chunk_text(None) == []

                    # Test with text (delegates to splitter)
                    service.text_splitter.split_text = MagicMock(return_value=["chunk1", "chunk2"])
                    assert service.chunk_text("some text") == ["chunk1", "chunk2"]
                    service.text_splitter.split_text.assert_called_with("some text")
