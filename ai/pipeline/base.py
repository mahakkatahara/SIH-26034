"""
AI Pipeline — Abstract Base Classes
=========================================
These interfaces define the contract for all AI pipeline components.
Concrete implementations are swapped in without changing the rest of the system.

Phase 1: StubPipeline (clearly marked as dev stub)
Phase 2: PaddleOCREngine
Phase 3: DeclarationExtractor
Phase 4+: Full pipeline
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore


@dataclass
class BoundingBox:
    """A rectangular region on an image."""
    x: float
    y: float
    width: float
    height: float
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class OCRTextRegion:
    """A text region detected by the OCR engine."""
    text: str
    bounding_box: BoundingBox
    confidence: float
    language: Optional[str] = None


@dataclass
class ExtractedDeclaration:
    """A structured declaration extracted from OCR text regions."""
    field_name: str         # e.g., "mrp", "net_quantity", "manufacturer_name"
    field_value: str        # e.g., "Rs. 50", "500g", "ABC Ltd"
    raw_text: str           # Raw OCR text before normalization
    confidence: float       # Extraction confidence 0.0–1.0
    bounding_box: Optional[BoundingBox] = None
    extraction_method: str = "unknown"


@dataclass
class PipelineResult:
    """
    The complete result from the AI pipeline for a single image.
    This is the output passed to the rule engine.
    """
    image_id: str
    pipeline_status: str            # DEV_STUB | COMPLETED | FAILED
    ocr_regions: List[OCRTextRegion] = field(default_factory=list)
    declarations: List[ExtractedDeclaration] = field(default_factory=list)
    preprocessing_applied: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    notice: Optional[str] = None    # Shown for DEV_STUB
    error: Optional[str] = None
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BasePreprocessor(ABC):
    """
    Abstract interface for image preprocessing.

    Implementations:
    - Phase 2: OpenCVPreprocessor (noise reduction, deskewing, contrast enhancement)
    """

    @abstractmethod
    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, List[str]]:
        """
        Preprocess an image for OCR.

        Args:
            image: Input image as numpy array (BGR format from OpenCV).

        Returns:
            Tuple of (processed_image, list_of_applied_operations)
        """
        pass


class BaseOCREngine(ABC):
    """
    Abstract interface for OCR engines.

    Implementations:
    - Phase 2: PaddleOCREngine (using PaddleOCR)
    - Future: TesseractEngine, EasyOCREngine
    """

    @abstractmethod
    def recognize(self, image: np.ndarray) -> List[OCRTextRegion]:
        """
        Perform OCR on a preprocessed image.

        Args:
            image: Preprocessed image as numpy array.

        Returns:
            List of detected text regions with bounding boxes and confidence.
        """
        pass


class BaseExtractor(ABC):
    """
    Abstract interface for declaration extractors.

    The extractor takes raw OCR text regions and maps them to structured
    Legal Metrology declarations (MRP, net quantity, manufacturer, etc.).

    Implementations:
    - Phase 3: RegexExtractor (pattern matching for standard declaration formats)
    - Future: NLPExtractor (NER-based extraction)
    """

    @abstractmethod
    def extract(self, ocr_regions: List[OCRTextRegion]) -> List[ExtractedDeclaration]:
        """
        Extract structured declarations from OCR text regions.

        Args:
            ocr_regions: List of OCR-detected text regions.

        Returns:
            List of extracted and normalized declarations.
        """
        pass


class BasePipeline(ABC):
    """
    Abstract interface for the complete AI analysis pipeline.

    The pipeline orchestrates: preprocessing -> OCR -> extraction.
    The rule engine is called separately (in the backend service layer).
    """

    @abstractmethod
    def analyze(self, image_path: str, image_id: str) -> PipelineResult:
        """
        Run the full analysis pipeline on a single image.

        Args:
            image_path: Path to the image file.
            image_id: UUID of the InspectionImage record.

        Returns:
            PipelineResult with declarations and OCR data.
        """
        pass
