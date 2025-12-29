"""Embedding service for generating vector embeddings from text."""

import logging
import os

from openai import OpenAI

from config.config import get_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI-compatible API.

    Supports any embedding provider with an OpenAI-compatible API, including:
    - OpenAI
    - Azure OpenAI
    - Ollama
    - Local inference servers (vLLM, text-generation-inference, etc.)
    """

    def __init__(self) -> None:
        config = get_config()
        self.embedding_config = config.embedding
        self.llm_config = config.llm

        api_key = os.environ.get("EMBEDDING_API_KEY")
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY environment variable is required")

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.llm_config.base_url,
        )

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for the given text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, returning zero vector")
            return [0.0] * self.embedding_config.dimensions

        # Truncate text if too long (OpenAI has token limits)
        max_chars = 8000 * 4  # Rough estimate: 4 chars per token, 8000 token limit
        if len(text) > max_chars:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_chars}")
            text = text[:max_chars]

        try:
            response = self.client.embeddings.create(
                model=self.embedding_config.model,
                input=text,
                dimensions=self.embedding_config.dimensions,
            )
            embedding: list[float] = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def extract_text_from_content(self, content: bytes, content_type: str) -> str:
        """Extract text from document content.

        Args:
            content: The raw document bytes.
            content_type: The MIME type of the document.

        Returns:
            Extracted text content.
        """
        if content_type == "application/pdf":
            return self._extract_text_from_pdf(content)
        elif content_type.startswith("text/"):
            return content.decode("utf-8", errors="ignore")
        else:
            logger.warning(f"Unsupported content type for text extraction: {content_type}")
            return ""

    def _extract_text_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF content using pypdf.

        Args:
            content: PDF file bytes.

        Returns:
            Extracted text.
        """
        try:
            from io import BytesIO

            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return ""
