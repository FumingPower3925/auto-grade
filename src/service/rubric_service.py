import io
import json
import logging
import os
import re
from typing import Any

import httpx
from pypdf import PdfReader

from config.config import get_config
from src.repository.db.models import ExtractedRubricModel, RubricCriterionModel

logger = logging.getLogger(__name__)


class RubricService:
    """Service for extracting structured information from rubrics."""

    def __init__(self) -> None:
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        config = get_config()
        self.llm_base_url = config.llm.base_url
        self.llm_model = config.llm.model

    def extract_text_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF content.

        Args:
            content: The PDF content as bytes.

        Returns:
            The extracted text from the PDF.
        """
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PdfReader(pdf_file)

            extracted_text = ""
            for page in pdf_reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"Failed to extract text from page: {e}")
                    continue

            return extracted_text.strip()
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            return ""

    def extract_rubric_with_llm(self, text: str) -> ExtractedRubricModel:
        """Extract structured rubric information using LLM.

        Args:
            text: The raw text extracted from the rubric PDF.

        Returns:
            An ExtractedRubricModel with the parsed information.
        """
        if not self.llm_api_key or not text:
            return ExtractedRubricModel(raw_text=text if text else None)

        try:
            url = f"{self.llm_base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}

            prompt = self._build_extraction_prompt(text)

            data: dict[str, Any] = {
                "model": self.llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert at analyzing grading rubrics. "
                            "Extract structured information from rubrics and return valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": 2000,
            }

            response = httpx.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                return self._parse_llm_response(content, text)
            else:
                logger.warning(f"LLM API returned status {response.status_code}")

        except httpx.TimeoutException:
            logger.warning("LLM API request timed out")
        except Exception as e:
            logger.error(f"Failed to extract rubric with LLM: {e}")

        return ExtractedRubricModel(raw_text=text)

    def _build_extraction_prompt(self, text: str) -> str:
        """Build the prompt for LLM extraction.

        Args:
            text: The rubric text to analyze.

        Returns:
            The formatted prompt string.
        """
        return f"""Analyze the following grading rubric and extract structured information.

Return a JSON object with this exact structure:
{{
    "title": "rubric title or null if not found",
    "total_points": total points as a number or null if not found,
    "criteria": [
        {{
            "name": "criterion name",
            "description": "what this criterion evaluates",
            "max_points": points as a number,
            "weight": weight as decimal (0.0-1.0) or null if not specified
        }}
    ]
}}

Important:
- Extract ALL grading criteria you can find
- If points are not specified, estimate based on context or use 0
- Return ONLY valid JSON, no other text

Rubric text:
{text[:4000]}"""

    def _parse_llm_response(self, content: str, raw_text: str) -> ExtractedRubricModel:
        """Parse the LLM response into an ExtractedRubricModel.

        Args:
            content: The LLM response content.
            raw_text: The original raw text for fallback.

        Returns:
            An ExtractedRubricModel with the parsed data.
        """
        try:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return ExtractedRubricModel(raw_text=raw_text)

            parsed = json.loads(json_match.group())

            criteria = []
            for criterion_data in parsed.get("criteria", []):
                try:
                    criterion = RubricCriterionModel(
                        name=criterion_data.get("name", "Unnamed Criterion"),
                        description=criterion_data.get("description", ""),
                        max_points=float(criterion_data.get("max_points", 0)),
                        weight=float(criterion_data["weight"]) if criterion_data.get("weight") is not None else None,
                    )
                    criteria.append(criterion)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse criterion: {e}")
                    continue

            total_points = parsed.get("total_points")
            if total_points is not None:
                try:
                    total_points = float(total_points)
                except (ValueError, TypeError):
                    total_points = None

            return ExtractedRubricModel(
                title=parsed.get("title"),
                total_points=total_points,
                criteria=criteria,
                raw_text=raw_text,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return ExtractedRubricModel(raw_text=raw_text)

    def parse_rubric(self, content: bytes, content_type: str) -> ExtractedRubricModel:
        """Parse a rubric file and extract structured information.

        Args:
            content: The file content as bytes.
            content_type: The MIME type of the file.

        Returns:
            An ExtractedRubricModel with the extracted information.
        """
        if content_type != "application/pdf":
            logger.info(f"Unsupported content type for rubric extraction: {content_type}")
            return ExtractedRubricModel()

        text = self.extract_text_from_pdf(content)
        if not text:
            return ExtractedRubricModel()

        return self.extract_rubric_with_llm(text)
