"""Embedding service for generating vector embeddings from text."""

import logging
import os
import re
from typing import Any

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
        return self._merge_splits(good_splits)

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

    def _merge_splits(self, splits: list[str]) -> list[str]:
        """Merge small splits into chunks."""
        separator = " "
        docs: list[str] = []
        current_doc: list[str] = []
        total = 0

        for d in splits:
            _len = self._length_function(d)
            if self._should_start_new_chunk(total, _len, len(current_doc), len(separator)):
                doc = self._flush_current_doc(current_doc, separator, docs)
                if doc:
                    total, current_doc = self._apply_overlap(current_doc, _len, separator)

            current_doc.append(d)
            total += _len + (1 if len(current_doc) > 1 else 0)

        if current_doc:
            doc = separator.join(current_doc)
            if doc:
                docs.append(doc)
        return docs

    def _should_start_new_chunk(self, total: int, item_len: int, doc_len: int, sep_len: int) -> bool:
        """Check if we should start a new chunk."""
        return total + item_len + (doc_len * sep_len) > self._chunk_size

    def _flush_current_doc(self, current_doc: list[str], separator: str, docs: list[str]) -> str | None:
        """Flush current doc to docs list and log warning if oversized."""
        total = sum(self._length_function(s) for s in current_doc) + max(0, len(current_doc) - 1)
        if total > self._chunk_size:
            logger.warning(f"Created a chunk of size {total}, which is longer than the specified {self._chunk_size}")
        if current_doc:
            doc = separator.join(current_doc)
            docs.append(doc)
            return doc
        return None

    def _apply_overlap(self, current_doc: list[str], next_len: int, separator: str) -> tuple[int, list[str]]:
        """Apply overlap by removing items from the front of current_doc."""
        total = sum(self._length_function(s) for s in current_doc) + max(0, len(current_doc) - 1)
        while current_doc and (
            total > self._chunk_overlap
            or (total + next_len + (len(current_doc) * len(separator)) > self._chunk_size and total > 0)
        ):
            total -= self._length_function(current_doc[0]) + (1 if len(current_doc) > 1 else 0)
            current_doc.pop(0)
        return total, current_doc


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
            chunk_overlap=getattr(self.embedding_config, "chunk_overlap", 200),
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
            from io import BytesIO

            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            full_text_parts: list[str] = []
            ocr_tasks: list = []
            ocr_indices: list[int] = []

            for i, page in enumerate(reader.pages):
                result = self._process_pdf_page(page, i, ocr_tasks, ocr_indices)
                full_text_parts.append(result)

            # Run OCR tasks in parallel
            if ocr_tasks:
                await self._run_ocr_tasks(ocr_tasks, ocr_indices, full_text_parts)

            return "\n\n".join(full_text_parts)

        except Exception as e:
            logger.error(f"Failed to extract text from PDF robustly: {e}")
            return ""

    def _process_pdf_page(self, page: Any, index: int, ocr_tasks: list, ocr_indices: list[int]) -> str:
        """Process a single PDF page and queue for OCR if needed."""
        from io import BytesIO

        from pypdf import PdfWriter

        extracted_text = page.extract_text() or ""
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        area = width * height if width > 0 and height > 0 else 1.0
        density = len(extracted_text) / area if area > 0 else 0

        if density < 0.0005 or len(extracted_text.strip()) < 50:
            logger.info(f"Page {index + 1} low text density ({density:.6f}), queueing for OCR")
            writer = PdfWriter()
            writer.add_page(page)
            page_bytes_io = BytesIO()
            writer.write(page_bytes_io)
            page_bytes = page_bytes_io.getvalue()

            ocr_tasks.append(self.ocr_service.extract_text_from_pdf(page_bytes))
            ocr_indices.append(index)
            return ""  # Placeholder

        return extracted_text

    async def _run_ocr_tasks(self, ocr_tasks: list, ocr_indices: list[int], full_text_parts: list[str]) -> None:
        """Run OCR tasks in parallel and update text parts."""
        import asyncio

        logger.info(f"Running OCR on {len(ocr_tasks)} pages...")
        ocr_results = await asyncio.gather(*ocr_tasks)

        for idx, result in zip(ocr_indices, ocr_results, strict=False):
            if result:
                full_text_parts[idx] = result
            else:
                logger.warning(f"OCR failed for page {idx + 1}")
