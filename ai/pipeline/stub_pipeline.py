"""
AI Pipeline — Development Stub
======================================================
⚠ THIS IS A PHASE 1 DEVELOPMENT STUB.

This stub returns a clearly-marked placeholder result.
It does NOT perform any actual OCR or image analysis.

Real implementations will replace this in Phase 2+:
  Phase 2: OpenCVPreprocessor + PaddleOCREngine
  Phase 3: DeclarationExtractor
  Phase 4: Rule Engine integration

DO NOT use stub results as real compliance decisions.
"""
import time
from typing import List

from ai.pipeline.base import (
    BasePipeline, PipelineResult, OCRTextRegion, ExtractedDeclaration,
    BoundingBox
)

# ─── Stub notice text ──────────────────────────────────────────────────────────
STUB_NOTICE = (
    "⚠ AI PIPELINE NOT IMPLEMENTED (Phase 1 — Development Stub). "
    "This result contains NO real OCR or declaration extraction. "
    "Real analysis using PaddleOCR and CV will be integrated in Phase 2+. "
    "All inspections in Phase 1 require HUMAN REVIEW."
)


class StubPipeline(BasePipeline):
    """
    Development stub for the AI pipeline.
    Returns a DEV_STUB result with zero declarations and a clear notice.
    Used in Phase 1 until real OCR/CV is integrated.
    """

    def analyze(self, image_path: str, image_id: str) -> PipelineResult:
        """
        Returns a stub result — no actual image processing performed.

        Args:
            image_path: Path to the image (not read in stub mode).
            image_id: UUID of the InspectionImage record.

        Returns:
            PipelineResult with pipeline_status="DEV_STUB"
        """
        start = time.time()

        # Simulate minimal processing time
        time.sleep(0.1)

        elapsed_ms = int((time.time() - start) * 1000)

        return PipelineResult(
            image_id=image_id,
            pipeline_status="DEV_STUB",
            ocr_regions=[],        # No real OCR performed
            declarations=[],       # No declarations extracted
            preprocessing_applied=[],
            confidence_score=0.0,
            notice=STUB_NOTICE,
            processing_time_ms=elapsed_ms,
            metadata={
                "stub": True,
                "phase": 1,
                "next_phase": "Phase 2 — PaddleOCR integration",
            },
        )


def get_pipeline(mode: str = "stub") -> BasePipeline:
    """
    Factory function to get the appropriate pipeline implementation.

    Args:
        mode: Pipeline mode from config.
              "stub" → StubPipeline (Phase 1)
              "paddleocr" → PaddleOCRPipeline (Phase 2, not yet implemented)
              "custom" → CustomPipeline (future)

    Returns:
        Pipeline instance.

    Raises:
        NotImplementedError: If the requested mode is not yet implemented.
    """
    if mode == "stub":
        return StubPipeline()
    elif mode == "paddleocr":
        raise NotImplementedError(
            "PaddleOCR pipeline not yet implemented. "
            "This will be available in Phase 2. "
            "Set AI_PIPELINE_MODE=stub to use the development stub."
        )
    elif mode == "custom":
        raise NotImplementedError(
            "Custom pipeline not yet implemented. "
            "Set AI_PIPELINE_MODE=stub to use the development stub."
        )
    else:
        raise ValueError(f"Unknown pipeline mode: {mode!r}. Use 'stub', 'paddleocr', or 'custom'.")
