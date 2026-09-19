"""Pipeline package containing base interfaces, stubs, and vision pipeline."""
from ai.pipeline.base import (
    BoundingBox,
    OCRTextRegion,
    ExtractedDeclaration,
    PipelineResult,
    BasePipeline,
    BaseOCREngine,
    BaseExtractor,
    BasePreprocessor,
)
from ai.pipeline.stub_pipeline import StubPipeline, get_pipeline

__all__ = [
    "BoundingBox",
    "OCRTextRegion",
    "ExtractedDeclaration",
    "PipelineResult",
    "BasePipeline",
    "BaseOCREngine",
    "BaseExtractor",
    "BasePreprocessor",
    "StubPipeline",
    "get_pipeline",
]
