"""
AI Pipeline — Gemini Vision Extraction Pipeline (Phase 2+3)
============================================================
Real extraction pipeline utilizing Google Gemini Vision (google-genai SDK)
to read packaged commodity labels and extract mandatory Legal Metrology
declarations with bounding boxes, confidence scores, and OCR text regions.
"""
from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator

from ai.pipeline.base import (
    BasePipeline,
    PipelineResult,
    OCRTextRegion,
    ExtractedDeclaration,
    BoundingBox,
)

try:
    from app.core.config import settings
except Exception:
    settings = None


class PipelineError(Exception):
    """Raised when pipeline processing fails or malformed output persists after retry."""
    pass


# ─── Pydantic schemas for Gemini Structured Output ────────────────────────────

class FieldExtraction(BaseModel):
    """Extraction output for a single mandatory declaration field."""
    value: Optional[str] = Field(
        default=None,
        description="Extracted value of the declaration, or null if not found on the label."
    )
    raw_text: Optional[str] = Field(
        default=None,
        description="Exact raw text snippet as printed on the package label."
    )
    confidence: float = Field(
        default=0.0,
        description="Extraction confidence between 0.0 and 1.0. Must be 0.0 if field is missing."
    )
    bounding_box: List[int] = Field(
        default_factory=list,
        description="Bounding box [x1, y1, x2, y2] in pixel coordinates of source image, or empty list."
    )

    @field_validator("bounding_box", mode="before")
    def null_to_empty_bbox(cls, v: Any) -> Any:
        return [] if v is None else v


class OCRRegionExtraction(BaseModel):
    """Detected text region from package OCR."""
    text: str = Field(description="Detected text snippet.")
    bounding_box: List[int] = Field(
        default_factory=list,
        description="Bounding box [x1, y1, x2, y2] in pixel coordinates, or empty list."
    )
    confidence: float = Field(
        default=0.0,
        description="OCR detection confidence score between 0.0 and 1.0."
    )

    @field_validator("bounding_box", mode="before")
    def null_to_empty_bbox(cls, v: Any) -> Any:
        return [] if v is None else v


class PackageLabelAnalysis(BaseModel):
    """Constrained schema for Gemini vision structured response."""
    commodity_name: FieldExtraction = Field(default_factory=FieldExtraction)
    mrp: FieldExtraction = Field(default_factory=FieldExtraction)
    net_quantity: FieldExtraction = Field(default_factory=FieldExtraction)
    manufacturer_name: FieldExtraction = Field(default_factory=FieldExtraction)
    manufacturer_address: FieldExtraction = Field(default_factory=FieldExtraction)
    manufacturing_date: FieldExtraction = Field(default_factory=FieldExtraction)
    best_before_date: FieldExtraction = Field(default_factory=FieldExtraction)
    batch_number: FieldExtraction = Field(default_factory=FieldExtraction)
    consumer_care_info: FieldExtraction = Field(default_factory=FieldExtraction)
    country_of_origin: FieldExtraction = Field(default_factory=FieldExtraction)
    unit_sale_price: FieldExtraction = Field(default_factory=FieldExtraction)
    ocr_regions: List[OCRRegionExtraction] = Field(default_factory=list)


EXTRACTION_PROMPT = """
You are an expert Legal Metrology inspection vision model analyzing packaged commodity labels.
Analyze the provided package image and extract all mandatory legal declarations and readable text regions.

Rules:
1. Extract values for:
   - commodity_name
   - mrp
   - net_quantity
   - manufacturer_name
   - manufacturer_address
   - manufacturing_date
   - best_before_date
   - batch_number
   - consumer_care_info
   - country_of_origin
   - unit_sale_price
2. For each declaration field:
   - Provide value, raw_text, confidence (0.0 to 1.0), and bounding_box as [x1, y1, x2, y2] in integer pixel coordinates of the source image.
   - If a declaration is missing or not visible in the image, you MUST set value to null, raw_text to null, and confidence to 0.0. NEVER guess, assume, or hallucinate values.
3. In ocr_regions, list every distinct text segment/line detected on the image, with its text, bounding_box [x1, y1, x2, y2], and confidence.
4. Output must strictly conform to the JSON schema.
"""


# ─── Normalization Utilities ──────────────────────────────────────────────────

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

UNIT_MAP = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "ml": "ml", "mls": "ml", "millilitre": "ml", "millilitres": "ml",
    "l": "l", "ltr": "l", "ltrs": "l", "litre": "l", "litres": "l",
    "cm": "cm", "m": "m", "mm": "mm",
    "nos": "nos", "no": "nos", "pcs": "nos", "pieces": "nos", "units": "nos", "n": "nos", "u": "nos"
}


def normalize_mrp(raw_text: Optional[str], value: Optional[str] = None) -> Optional[float]:
    """
    Strips currency symbols (Rs., ₹, INR, /-) and extracts a clean numeric MRP float.
    """
    target = value if value is not None else raw_text
    if not target or not target.strip():
        return None

    # Remove currency words and symbols
    cleaned = re.sub(r"(?i)(mrp|rs\.?|inr|₹|inclusive|incl\.?|of|all|taxes|tax|/-|/)", " ", target)
    cleaned = cleaned.replace(",", "")

    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def normalize_quantity(raw_text: Optional[str], value: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Parses net quantity into a structured dictionary: {amount: float, unit: str}.
    """
    target = value if value is not None else raw_text
    if not target or not target.strip():
        return None

    cleaned = re.sub(r"(?i)(net\s*wt\.?|net\s*quantity|net\s*qty\.?|wt\.?|quantity|qty\.?|:)", " ", target)
    match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", cleaned)
    if match:
        try:
            amount = float(match.group(1))
            unit_raw = match.group(2).lower()
            unit = UNIT_MAP.get(unit_raw, unit_raw)
            return {"amount": amount, "unit": unit}
        except ValueError:
            return None
    return None


def normalize_date(raw_text: Optional[str], value: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses manufacturing or expiry dates into ISO format where unambiguous.
    If ambiguous or complex, returns raw text with needs_review=True.
    """
    target = value if value is not None else raw_text
    if not target or not target.strip():
        return {"iso_date": None, "raw": None, "needs_review": False}

    cleaned = target.strip()
    # Strip common leading labels
    cleaned_text = re.sub(r"(?i)^(mfg|mfg\.?|mfd|pkd|packed|best\s*before|exp|expiry|date|use\s*by|use\s*before)[\s.:/-]*", "", cleaned).strip()

    # 1. ISO format: YYYY-MM-DD
    iso_match = re.search(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b", cleaned_text)
    if iso_match:
        y, m, d = iso_match.group(1), iso_match.group(2), iso_match.group(3)
        return {"iso_date": f"{y}-{m}-{d}", "raw": target, "needs_review": False}

    # 2. Numeric 3-part date: DD/MM/YYYY or MM/DD/YYYY
    dmy_match = re.search(r"(?<![/.\d])(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2}|\d{2})(?![/.\d])", cleaned_text)
    if dmy_match:
        p1 = int(dmy_match.group(1))
        p2 = int(dmy_match.group(2))
        yr_raw = dmy_match.group(3)
        yr = int(yr_raw) if len(yr_raw) == 4 else int("20" + yr_raw)

        # Unambiguous day > 12 -> DD/MM/YYYY
        if p1 > 12 and 1 <= p2 <= 12:
            return {"iso_date": f"{yr:04d}-{p2:02d}-{p1:02d}", "raw": target, "needs_review": False}
        # Unambiguous month first -> MM/DD/YYYY
        elif p2 > 12 and 1 <= p1 <= 12:
            return {"iso_date": f"{yr:04d}-{p1:02d}-{p2:02d}", "raw": target, "needs_review": False}
        # Equal day and month
        elif p1 == p2 and 1 <= p1 <= 12:
            return {"iso_date": f"{yr:04d}-{p1:02d}-{p2:02d}", "raw": target, "needs_review": False}
        else:
            # Ambiguous (e.g. 03/04/2024 or 04/05/2025 where both are <= 12)
            return {"iso_date": None, "raw": target, "needs_review": True}

    # 3. Named month format: e.g., 15 May 2024 or May 2024 or 15-May-2024
    named_match = re.search(r"\b(?:(\d{1,2})[\s/-]+)?([a-zA-Z]{3,9})[\s/-]+(20\d{2}|\d{2})\b", cleaned_text)
    if named_match:
        day_part = named_match.group(1)
        month_str = named_match.group(2).lower()
        year_str = named_match.group(3)
        year = int(year_str) if len(year_str) == 4 else int("20" + year_str)

        if month_str in MONTH_MAP:
            month = MONTH_MAP[month_str]
            if day_part:
                day = int(day_part)
                return {"iso_date": f"{year:04d}-{month:02d}-{day:02d}", "raw": target, "needs_review": False}
            else:
                return {"iso_date": f"{year:04d}-{month:02d}", "raw": target, "needs_review": False}

    # 4. Numeric Month/Year: MM/YYYY or MM-YYYY (only 2 parts)
    my_match = re.search(r"(?<![/.\d])(0[1-9]|1[0-2])[-/](20\d{2})(?![/.\d])", cleaned_text)
    if my_match:
        m = my_match.group(1)
        y = my_match.group(2)
        return {"iso_date": f"{y}-{m}", "raw": target, "needs_review": False}

    # Ambiguous or non-standard
    return {"iso_date": None, "raw": target, "needs_review": True}


def parse_bounding_box(
    bbox_coords: Optional[List[Union[int, float]]], conf: float = 0.0
) -> Optional[BoundingBox]:
    """
    Parses and validates bounding box coordinates from Gemini Vision output.
    Rejects degenerate bounding boxes (width <= 0 or height <= 0).
    Handles both [x1, y1, x2, y2] and [ymin, xmin, ymax, xmax] coordinate orders.
    """
    if not bbox_coords or len(bbox_coords) != 4:
        return None
    try:
        c1, c2, c3, c4 = [float(v) for v in bbox_coords]
        x1, x2 = min(c1, c3), max(c1, c3)
        y1, y2 = min(c2, c4), max(c2, c4)
        width = x2 - x1
        height = y2 - y1

        # Check if coordinates were [ymin, xmin, ymax, xmax]
        if width <= 0.0 or height <= 0.0:
            alt_x1, alt_x2 = min(c2, c4), max(c2, c4)
            alt_y1, alt_y2 = min(c1, c3), max(c1, c3)
            alt_width = alt_x2 - alt_x1
            alt_height = alt_y2 - alt_y1
            if alt_width > 0.0 and alt_height > 0.0:
                return BoundingBox(
                    x=alt_x1,
                    y=alt_y1,
                    width=alt_width,
                    height=alt_height,
                    confidence=conf,
                )
            # Truly degenerate (width <= 0 or height <= 0)
            return None

        return BoundingBox(
            x=x1,
            y=y1,
            width=width,
            height=height,
            confidence=conf,
        )
    except Exception:
        return None


# ─── Vision Pipeline Implementation ──────────────────────────────────────────

class VisionPipeline(BasePipeline):
    """
    Vision-based extraction pipeline using Google Gemini Vision (google-genai SDK).
    Extracts declarations and OCR regions, performs normalization, and retries on failure.
    """

    MANDATORY_FIELDS = [
        "commodity_name",
        "mrp",
        "net_quantity",
        "manufacturer_name",
        "manufacturer_address",
        "manufacturing_date",
        "best_before_date",
        "batch_number",
        "consumer_care_info",
        "country_of_origin",
        "unit_sale_price",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        """
        Initialize the VisionPipeline.

        Args:
            api_key: Gemini API key (defaults to settings/env GEMINI_API_KEY).
            model_name: Gemini model name (defaults to VISION_MODEL or gemini-2.5-flash).
            client: Optional pre-configured genai.Client instance (useful for mocking).
        """
        self.api_key = (
            api_key
            or (getattr(settings, "GEMINI_API_KEY", None) if settings else None)
            or os.getenv("GEMINI_API_KEY", "")
        )
        self.model_name = (
            model_name
            or (getattr(settings, "VISION_MODEL", None) if settings else None)
            or os.getenv("VISION_MODEL", "gemini-2.5-flash")
        )
        self._client = client

    def _get_client(self) -> Any:
        """Instantiates or returns the cached google-genai Client."""
        if self._client is not None:
            return self._client
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            return self._client
        except Exception as exc:
            raise PipelineError(f"Failed to initialize google-genai Client: {exc}") from exc

    def _call_gemini_vision(self, client: Any, image_bytes: bytes, mime_type: str) -> str:
        """
        Sends the image and extraction prompt to Gemini, asking for constrained JSON schema.
        """
        try:
            from google.genai import types

            part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PackageLabelAnalysis,
                temperature=0.0,
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=[part, EXTRACTION_PROMPT],
                config=config,
            )

            if not response or not getattr(response, "text", None):
                raise ValueError("Empty or invalid response received from Gemini model")
            return response.text
        except Exception as exc:
            if isinstance(exc, PipelineError):
                raise
            raise exc

    def analyze(self, image_path: str, image_id: str) -> PipelineResult:
        """
        Executes vision analysis on a single image file.

        Args:
            image_path: Path to the image file on disk.
            image_id: Unique identifier for the inspection image.

        Returns:
            PipelineResult containing extracted declarations, ocr regions, and normalized values.
        """
        start_time = time.time()

        if not os.path.exists(image_path):
            raise PipelineError(f"Image file not found at: {image_path}")

        # Read image bytes & identify MIME type
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        client = self._get_client()

        # Execute call with retry once on malformed JSON / validation error
        analysis_data: Optional[PackageLabelAnalysis] = None
        last_error: Optional[Exception] = None

        for attempt in range(2):
            try:
                response_text = self._call_gemini_vision(client, image_bytes, mime_type)
                analysis_data = PackageLabelAnalysis.model_validate_json(response_text)
                break
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                else:
                    raise PipelineError(f"Malformed JSON response from Gemini after retry: {last_error}") from last_error

        if analysis_data is None:
            raise PipelineError(f"Extraction failed after retry: {last_error}")

        # Convert extracted fields to declarations
        declarations: List[ExtractedDeclaration] = []
        confidences: List[float] = []
        normalized_data: Dict[str, Any] = {}

        for field_name in self.MANDATORY_FIELDS:
            field_data: FieldExtraction = getattr(analysis_data, field_name, FieldExtraction())

            # Missing field rule: value null => value None, confidence 0.0
            val = field_data.value
            raw = field_data.raw_text
            conf = float(field_data.confidence) if val is not None else 0.0
            bbox_coords = field_data.bounding_box

            bbox = parse_bounding_box(bbox_coords, conf)

            # Normalization per field type
            if field_name == "mrp":
                mrp_numeric = normalize_mrp(raw, val)
                normalized_data["mrp_value"] = mrp_numeric
                if mrp_numeric is not None and val is not None:
                    # Keep field_value as string of numeric mrp or raw
                    val = str(mrp_numeric)
            elif field_name == "net_quantity":
                qty_parsed = normalize_quantity(raw, val)
                normalized_data["net_quantity"] = qty_parsed
            elif field_name in ("manufacturing_date", "best_before_date"):
                date_parsed = normalize_date(raw, val)
                normalized_data[field_name] = date_parsed
                if date_parsed.get("iso_date"):
                    val = date_parsed["iso_date"]

            declaration = ExtractedDeclaration(
                field_name=field_name,
                field_value=val,
                raw_text=raw or "",
                confidence=conf,
                bounding_box=bbox,
                extraction_method="gemini_vision",
            )
            declarations.append(declaration)
            confidences.append(conf)

        # Convert OCR regions
        ocr_regions: List[OCRTextRegion] = []
        for region in analysis_data.ocr_regions:
            region_bbox = parse_bounding_box(region.bounding_box, float(region.confidence))
            ocr_regions.append(
                OCRTextRegion(
                    text=region.text,
                    bounding_box=region_bbox or BoundingBox(x=0.0, y=0.0, width=0.0, height=0.0),
                    confidence=float(region.confidence),
                )
            )

        extracted_confs = [c for c in confidences if c > 0.0]
        mean_confidence = float(sum(extracted_confs) / len(extracted_confs)) if extracted_confs else 0.0
        elapsed_ms = int((time.time() - start_time) * 1000)

        return PipelineResult(
            image_id=image_id,
            pipeline_status="COMPLETED",
            ocr_regions=ocr_regions,
            declarations=declarations,
            preprocessing_applied=["gemini_vision_pipeline"],
            confidence_score=mean_confidence,
            processing_time_ms=elapsed_ms,
            metadata={
                "model": self.model_name,
                "normalized": normalized_data,
            },
        )
