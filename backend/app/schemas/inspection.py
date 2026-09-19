"""
Pydantic Schemas — Inspection, InspectionImage, Declaration, Violation
"""
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ─── Inspection ───────────────────────────────────────────────────────────────

class InspectionCreate(BaseModel):
    product_id: Optional[UUID] = None
    remarks: Optional[str] = None
    location: Optional[str] = None


class InspectionUpdate(BaseModel):
    status: Optional[str] = None
    overall_compliance_status: Optional[str] = None
    remarks: Optional[str] = None
    location: Optional[str] = None


class InspectionImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inspection_id: UUID
    image_path: str
    label: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    processing_status: str
    processed_at: Optional[datetime] = None
    created_at: datetime


class DeclarationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inspection_id: UUID
    image_id: Optional[UUID] = None
    field_name: str
    field_value: Optional[str] = None
    raw_text: Optional[str] = None
    confidence_score: Optional[float] = None
    bounding_box: Optional[Dict[str, Any]] = None
    extraction_method: Optional[str] = None
    is_verified: bool
    created_at: datetime


class OCRRegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inspection_id: UUID
    image_id: Optional[UUID] = None
    text: str
    confidence_score: Optional[float] = None
    bounding_box: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    created_at: datetime


class ViolationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inspection_id: UUID
    rule_id: Optional[UUID] = None
    declaration_id: Optional[UUID] = None
    severity: str
    status: str
    description: str
    legal_reference: Optional[str] = None
    evidence_region: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime


class InspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inspection_number: str
    status: str
    overall_compliance_status: str
    product_id: Optional[UUID] = None
    inspector_id: UUID
    ai_pipeline_status: str
    ai_confidence_score: Optional[float] = None
    remarks: Optional[str] = None
    location: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class InspectionDetailResponse(InspectionResponse):
    """Full inspection detail with nested relations."""
    images: List[InspectionImageResponse] = []
    declarations: List[DeclarationResponse] = []
    ocr_regions: List[OCRRegionResponse] = []
    violations: List[ViolationResponse] = []


class InspectionListResponse(BaseModel):
    items: List[InspectionResponse]
    total: int
    page: int
    size: int
    pages: int


# ─── AI Analysis Result (from pipeline, possibly stub) ────────────────────────

class AnalysisResult(BaseModel):
    """
    Result returned from the AI analysis pipeline.
    In Phase 1, this will always be a DEV_STUB result.
    In Phase 2+, this contains extracted declarations and OCR regions.
    """
    inspection_id: UUID
    pipeline_status: str  # DEV_STUB | COMPLETED | FAILED
    notice: Optional[str] = None  # Shown for DEV_STUB
    declarations: List[DeclarationResponse] = []
    ocr_regions: List[OCRRegionResponse] = []
    violations: List[ViolationResponse] = []
    overall_compliance_status: str = "NEEDS_REVIEW"
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
