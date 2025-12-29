"""Embedding service for generating vector embeddings from text."""

import logging
import os
import re

from openai import OpenAI

from config.config import get_config
from src.service.ocr_service import OCRService

logger = logging.getLogger(__name__)


class RecursiveCharacterTextSplitter:
    """Splits text recursively by separators to respect document structure."""

    def __init__(self, chunk_size: int, chunk_overlap: int, separators: list[str] | None = None):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separators = separators or ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks."""
        good_splits = self._split_text(text, self._separators)
        return self._merge_splits(good_splits, self._separators)

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Split text by separators."""

        separator = separators[-1]
        for _i, _s in enumerate(separators):
            if _s == "":
                separator = _s
                break
            if re.search(re.escape(_s), text):
                separator = _s
                break

        _separator = re.escape(separator) if separator else ""
        splits = re.split(_separator, text) if _separator else list(text)

        # Now keep splits that are good, merge others?
        # Simplified recursive logic primarily for basic structure preservation
        return [s for s in splits if s]

    def _length_function(self, text: str) -> int:
        return len(text)

    def _merge_splits(self, splits: list[str], separators: list[str]) -> list[str]:
        """Merge small splits into chunks."""
        separator = " " # Default joiner
        docs = []
        current_doc: list[str] = []
        total = 0
        for d in splits:
            _len = self._length_function(d)
            if total + _len + (len(current_doc) * len(separator)) > self._chunk_size:
                if total > self._chunk_size:
                    logger.warning(
                        f"Created a chunk of size {total}, which is longer than the specified {self._chunk_size}"
                    )
                if len(current_doc) > 0:
                    doc = separator.join(current_doc)
                    if doc is not None:
                        docs.append(doc)
                    while total > self._chunk_overlap or (
                        total + _len + (len(current_doc) * len(separator)) > self._chunk_size and total > 0
                    ):
                         # Simple overlap logic: remove first element
                         total -= self._length_function(current_doc[0]) + (1 if len(current_doc) > 1 else 0)
                         current_doc.pop(0)

            current_doc.append(d)
            total += _len + (1 if len(current_doc) > 1 else 0)

        if current_doc:
            doc = separator.join(current_doc)
            if doc:
                docs.append(doc)
        return docs


class EmbeddingService:
    """Service for generating text embeddings using OpenAI-compatible API."""

    def __init__(self) -> None:
        config = get_config()
        self.embedding_config = config.embedding
        self.llm_config = config.llm
        self.ocr_service = OCRService()

        # Initialize splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=getattr(self.embedding_config, "chunk_size", 1000),
            chunk_overlap=getattr(self.embedding_config, "chunk_overlap", 200)
        )

        api_key = os.environ.get("EMBEDDING_API_KEY")
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY environment variable is required")

        self.client = OpenAI(
            api_key=api_key,
            base_url=self.llm_config.base_url,
        )

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for the given text."""
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding, returning zero vector")
            return [0.0] * self.embedding_config.dimensions

        # Truncate text if too long (model has 8192 token limit)
        max_chars = 24000  # Conservative 24k chars (~6k tokens)
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
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks using recursive character splitter."""
        if not text:
            return []

        return self.text_splitter.split_text(text)

    async def extract_text_from_content(self, content: bytes, content_type: str) -> str:
        """Extract text from document content with smart OCR fallback."""
        if content_type == "application/pdf":
            return await self._extract_text_from_pdf_robust(content)
        elif content_type.startswith("text/"):
            return content.decode("utf-8", errors="ignore")
        else:
            logger.warning(f"Unsupported content type for text extraction: {content_type}")
            return ""

    async def _extract_text_from_pdf_robust(self, content: bytes) -> str:
        """Extract text from PDF pages, using OCR for low-density pages."""
        try:
            import asyncio
            from io import BytesIO

            from pypdf import PdfReader, PdfWriter

            reader = PdfReader(BytesIO(content))
            full_text_parts = []

            ocr_tasks = []
            ocr_indices = []

            for i, page in enumerate(reader.pages):
                extracted_text = page.extract_text() or ""

                # Check density
                # Page dimensions in points (1/72 inch)
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                area = width * height if width > 0 and height > 0 else 1.0
                density = len(extracted_text) / area if area > 0 else 0

                # Heuristic: < 0.001 chars per point sq is likely image-dominant or empty
                # e.g. A4 is ~595x842 = 500k points. 500 chars (short para) = 0.001 density.
                # Adjust threshold: 1 char per 1000 pixels

                if density < 0.0005 or len(extracted_text.strip()) < 50:
                    logger.info(f"Page {i+1} low text density ({density:.6f}), queueing for OCR")

                    # Prepare page bytes for OCR
                    writer = PdfWriter()
                    writer.add_page(page)
                    page_bytes_io = BytesIO()
                    writer.write(page_bytes_io)
                    page_bytes = page_bytes_io.getvalue()

                    # Add async task
                    ocr_tasks.append(self.ocr_service.extract_text_from_pdf(page_bytes))
                    ocr_indices.append(i)
                    full_text_parts.append("") # Placeholder
                else:
                    full_text_parts.append(extracted_text)

            # Run OCR tasks in parallel
            if ocr_tasks:
                logger.info(f"Running OCR on {len(ocr_tasks)} pages...")
                ocr_results = await asyncio.gather(*ocr_tasks)

                for idx, result in zip(ocr_indices, ocr_results, strict=False):
                    if result:
                         full_text_parts[idx] = result
                    else:
                         logger.warning(f"OCR failed for page {idx+1}")

            return "\n\n".join(full_text_parts)

        except Exception as e:
            logger.error(f"Failed to extract text from PDF robustly: {e}")
            return ""
