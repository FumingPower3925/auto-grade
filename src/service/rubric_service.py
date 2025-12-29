import io
import json
import logging
import os
import re
from typing import Any

import httpx
from pypdf import PdfReader

from config.config import get_config
from src.repository.db.models import ExtractedRubricModel, GradeLevel, RubricCriterionModel
from src.service.ocr_service import OCRService

logger = logging.getLogger(__name__)


class RubricService:
    """Service for extracting structured information from rubrics."""

    def __init__(self) -> None:
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        config = get_config()
        self.llm_base_url = config.llm.base_url
        self.default_model = config.llm.default_model
        self.smart_model = config.llm.smart_model

        # Initialize OCR service
        self.ocr_service = OCRService()

    def extract_text_from_pdf_raw(self, content: bytes) -> str:
        """Extract text from PDF content using raw pypdf (fallback).

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

    async def _try_llm_extraction(self, text: str, model: str) -> ExtractedRubricModel | None:
        """Try to extract rubric using a specific LLM model.

        Args:
            text: The text to analyze.
            model: The model to use.

        Returns:
            ExtractedRubricModel if extraction succeeds (has JSON), None otherwise.
        """
        if not self.llm_api_key or not text:
            return None

        try:
            url = f"{self.llm_base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}

            prompt = self._build_extraction_prompt(text)

            data: dict[str, Any] = {
                "model": model,
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
            }

            # O-series models (o1, o4, etc.) use max_completion_tokens
            if model.startswith("o"):
                data["max_completion_tokens"] = 4000
            else:
                data["max_tokens"] = 4000
                data["temperature"] = 0

            # Use async client
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=data)

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()

                # Check if JSON is present before parsing
                if not re.search(r"\{.*\}", content, re.DOTALL):
                    logger.warning(f"No JSON found in response from model {model}")
                    return None

                parsed_model = self._parse_llm_response(content, text)

                # If parsing returned default raw text model (meaning JSON decode fail or empty), treat as fail
                if not parsed_model.criteria and not parsed_model.title:
                     # Check if it really failed or just empty rubric
                     # _parse_llm_response returns valid model if parse fails, with just raw_text
                     # We might want to check if it actually parsed something
                     pass

                return parsed_model
            else:
                logger.warning(f"LLM API returned status {response.status_code} for model {model}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract rubric with LLM model {model}: {e}")
            return None

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
            "max_points": maximum points as a number,
            "weight": weight as decimal (0.0-1.0) or null if not specified,
            "grades": [
                {{
                    "label": "grade label (e.g., Excellent, Good, Satisfactory, Poor)",
                    "points": points for this grade level,
                    "description": "what achievement looks like at this level"
                }}
            ]
        }}
    ]
}}

Important:
- Extract ALL grading criteria you can find
- For each criterion, extract 2-5 grade levels (performance levels) from highest to lowest
- If grade levels are not explicit, infer them from the rubric context
- If points are not specified, distribute them evenly across grade levels
- Return ONLY valid JSON, no other text

Rubric text:
{text[:15000]}"""

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
                    # Parse grades for this criterion
                    grades = []
                    for grade_data in criterion_data.get("grades", []):
                        try:
                            grade = GradeLevel(
                                label=grade_data.get("label", "Unnamed"),
                                points=float(grade_data.get("points", 0)),
                                description=grade_data.get("description", ""),
                            )
                            grades.append(grade)
                        except (ValueError, KeyError) as e:
                            logger.warning(f"Failed to parse grade: {e}")
                            continue

                    criterion = RubricCriterionModel(
                        name=criterion_data.get("name", "Unnamed Criterion"),
                        max_points=float(criterion_data.get("max_points", 0)),
                        weight=float(criterion_data["weight"]) if criterion_data.get("weight") is not None else None,
                        grades=grades,
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

    async def parse_rubric(self, content: bytes, content_type: str) -> ExtractedRubricModel:
        """Parse a rubric file and extract structured information using fallback strategy.

        Strategy:
        1. OCR + Default Model
        2. OCR + Smart Model
        3. Raw RAW (pypdf) + Smart Model

        Args:
            content: The file content as bytes.
            content_type: The MIME type of the file.

        Returns:
            An ExtractedRubricModel with the extracted information.
        """
        if content_type != "application/pdf":
            logger.info(f"Unsupported content type for rubric extraction: {content_type}")
            return ExtractedRubricModel()

        # Step 1 & 2: Try OCR
        ocr_text = await self.ocr_service.extract_text_from_pdf(content)

        if ocr_text:
            logger.info("OCR extraction successful. Extending attempts with OCR text.")

            # Attempt 1: OCR + Default Model
            logger.info(f"Attempt 1: OCR + Default Model ({self.default_model})")
            result = await self._try_llm_extraction(ocr_text, self.default_model)
            if result:
                return result

            # Attempt 2: OCR + Smart Model
            logger.info(f"Attempt 2: OCR + Smart Model ({self.smart_model})")
            result = await self._try_llm_extraction(ocr_text, self.smart_model)
            if result:
                return result
        else:
            logger.warning("OCR extraction failed or skipped. Proceeding to raw PDF fallback.")

        # Step 3: Raw PDF + Smart Model
        logger.info(f"Attempt 3: Raw PDF + Smart Model ({self.smart_model})")
        raw_text = self.extract_text_from_pdf_raw(content)

        if raw_text:
            result = await self._try_llm_extraction(raw_text, self.smart_model)
            if result:
                return result

        logger.error("All rubric extraction attempts failed.")
        return ExtractedRubricModel(raw_text=ocr_text if ocr_text else raw_text)
