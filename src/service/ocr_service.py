import base64
import logging
import os

import httpx

from config.config import get_config

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR operations using Mistral API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OCR_API_KEY", "")
        config = get_config()
        self.base_url = config.ocr.base_url
        self.model = config.ocr.model
        self.provider = config.ocr.provider

    async def extract_text_from_pdf(self, content: bytes) -> str | None:
        """Extract text from PDF content using OCR.

        Args:
            content: The PDF content as bytes.

        Returns:
            The extracted text from the PDF, or None if OCR fails.
        """
        if not self.api_key or self.provider != "mistral":
            logger.warning("OCR API key not set or provider not Mistral. Skipping OCR.")
            return None

        try:
            # Encode PDF content to base64
            base64_content = base64.b64encode(content).decode("utf-8")
            data_url = f"data:application/pdf;base64,{base64_content}"

            url = f"{self.base_url}/ocr"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "document": {
                    "type": "document_url",
                    "document_url": data_url
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code != 200:
                    logger.error(f"OCR API request failed: {response.status_code} - {response.text}")
                    return None

                result = response.json()

                # Combine markdown from all pages
                extracted_text = ""
                if "pages" in result:
                    for page in result["pages"]:
                        extracted_text += page.get("markdown", "") + "\n\n"

                return extracted_text.strip()

        except Exception as e:
            logger.error(f"Failed to perform OCR: {e}")
            return None
