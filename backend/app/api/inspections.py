"""
Inspections API Routes — CRUD + image upload + AI analysis stub
"""
import asyncio
import math
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, require_inspector_or_above
from app.database.session import get_db_session
from app.models.inspection import Inspection, InspectionImage
from app.models.declaration import Declaration
from app.models.ocr_region import OCRRegion
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate, InspectionUpdate, InspectionResponse,
    InspectionDetailResponse, InspectionListResponse,
    InspectionImageResponse, AnalysisResult, DeclarationResponse,
    OCRRegionResponse,
)
from ai.pipeline.stub_pipeline import get_pipeline, StubPipeline

router = APIRouter()


def generate_inspection_number() -> str:
    """Generate a unique inspection number like LMIS-20260913-XXXX."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = str(uuid.uuid4())[:4].upper()
    return f"LMIS-{date_part}-{suffix}"


@router.get("", response_model=InspectionListResponse, summary="List inspections")
async def list_inspections(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    compliance_status: Optional[str] = Query(default=None),
    product_id: Optional[UUID] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Inspection)

    if status:
        query = query.where(Inspection.status == status)
    if compliance_status:
        query = query.where(Inspection.overall_compliance_status == compliance_status)
    if product_id:
        query = query.where(Inspection.product_id == product_id)
    if search:
        query = query.where(Inspection.inspection_number.ilike(f"%{search}%"))

    # INSPECTOR role sees only their own inspections
    if current_user.role == "INSPECTOR":
        query = query.where(Inspection.inspector_id == current_user.id)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    query = query.offset((page - 1) * size).limit(size).order_by(Inspection.created_at.desc())
    result = await db.execute(query)
    inspections = result.scalars().all()

    return InspectionListResponse(
        items=[InspectionResponse.model_validate(i) for i in inspections],
        total=total or 0,
        page=page,
        size=size,
        pages=math.ceil((total or 0) / size) if total else 0,
    )


@router.post("", response_model=InspectionResponse, status_code=201)
async def create_inspection(
    data: InspectionCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_inspector_or_above),
):
    inspection = Inspection(
        inspection_number=generate_inspection_number(),
        product_id=data.product_id,
        inspector_id=current_user.id,
        remarks=data.remarks,
        location=data.location,
        started_at=datetime.now(timezone.utc),
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    return InspectionResponse.model_validate(inspection)


@router.get("/{inspection_id}", response_model=InspectionDetailResponse)
async def get_inspection(
    inspection_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Inspection)
        .options(
            selectinload(Inspection.images),
            selectinload(Inspection.declarations),
            selectinload(Inspection.ocr_regions),
            selectinload(Inspection.violations),
        )
        .where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return InspectionDetailResponse.model_validate(inspection)


@router.put("/{inspection_id}", response_model=InspectionResponse)
async def update_inspection(
    inspection_id: UUID,
    data: InspectionUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # Inspector can only edit their own inspections
    if current_user.role == "INSPECTOR" and inspection.inspector_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot edit another inspector's inspection")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(inspection, field, value)

    await db.commit()
    await db.refresh(inspection)
    return InspectionResponse.model_validate(inspection)


@router.post("/{inspection_id}/images", response_model=List[InspectionImageResponse])
async def upload_images(
    inspection_id: UUID,
    images: List[UploadFile] = File(...),
    label: str = Form(default="OTHER"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_inspector_or_above),
):
    """Upload one or more images for an inspection."""
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # Validate label
    valid_labels = {"FRONT", "BACK", "SIDE", "TOP", "BOTTOM", "OTHER"}
    if label.upper() not in valid_labels:
        raise HTTPException(status_code=400, detail=f"Invalid label. Must be one of: {valid_labels}")

    saved_images = []
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(inspection_id))
    os.makedirs(upload_dir, exist_ok=True)

    for image_file in images:
        # Validate MIME type
        if image_file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {image_file.content_type}. Allowed: {settings.ALLOWED_IMAGE_TYPES}",
            )

        # Generate unique filename
        ext = os.path.splitext(image_file.filename or "image.jpg")[1]
        filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(upload_dir, filename)
        relative_path = f"uploads/{inspection_id}/{filename}"

        # Save file
        contents = await image_file.read()
        file_size = len(contents)

        # Validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB",
            )

        with open(filepath, "wb") as f:
            f.write(contents)

        # Try to get image dimensions
        width, height = None, None
        try:
            from PIL import Image as PILImage
            import io
            with PILImage.open(io.BytesIO(contents)) as img:
                width, height = img.size
        except Exception:
            pass  # Dimensions are optional

        img_record = InspectionImage(
            inspection_id=inspection_id,
            image_path=relative_path,
            label=label.upper(),
            original_filename=image_file.filename,
            file_size=file_size,
            mime_type=image_file.content_type,
            width=width,
            height=height,
        )
        db.add(img_record)
        saved_images.append(img_record)

    # Update inspection status
    if inspection.status == "DRAFT":
        inspection.status = "IN_PROGRESS"

    await db.commit()
    for img in saved_images:
        await db.refresh(img)

    return [InspectionImageResponse.model_validate(img) for img in saved_images]


@router.post("/{inspection_id}/analyze", response_model=AnalysisResult)
async def analyze_inspection(
    inspection_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_inspector_or_above),
):
    """
    Trigger AI analysis pipeline on uploaded images.
    In stub mode, returns a DEV_STUB placeholder.
    In vision mode, runs VisionPipeline on each image and persists declarations and OCR regions.
    """
    result = await db.execute(
        select(Inspection)
        .options(selectinload(Inspection.images))
        .where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    pipeline = get_pipeline(settings.AI_PIPELINE_MODE)

    # If in development stub mode
    if isinstance(pipeline, StubPipeline) or settings.AI_PIPELINE_MODE == "stub":
        await asyncio.sleep(settings.AI_STUB_DELAY_SECONDS)
        inspection.ai_pipeline_status = "DEV_STUB"
        inspection.overall_compliance_status = "NEEDS_REVIEW"
        inspection.status = "ANALYSIS_COMPLETE"
        await db.commit()

        return AnalysisResult(
            inspection_id=inspection_id,
            pipeline_status="DEV_STUB",
            notice=(
                "⚠ AI pipeline not yet implemented (Phase 1 — Development Stub). "
                "Real OCR, declaration extraction, and rule engine analysis will be "
                "integrated in Phase 2 onwards. Human review is required for all inspections."
            ),
            declarations=[],
            ocr_regions=[],
            violations=[],
            overall_compliance_status="NEEDS_REVIEW",
            confidence_score=None,
            processing_time_ms=int(settings.AI_STUB_DELAY_SECONDS * 1000),
        )

    # Real Vision Pipeline Mode
    start_time = time.time()
    all_saved_declarations = []
    all_saved_ocr_regions = []
    all_field_confidences = []

    for img in inspection.images:
        # Resolve image file location
        candidates = [
            img.image_path,
            os.path.join(settings.UPLOAD_DIR, os.path.basename(img.image_path)),
            os.path.join(settings.UPLOAD_DIR, str(inspection_id), os.path.basename(img.image_path)),
            os.path.join(".", img.image_path),
        ]
        resolved_path = next((p for p in candidates if os.path.exists(p)), img.image_path)

        # Run pipeline
        pipeline_result = pipeline.analyze(resolved_path, str(img.id))

        # Persist Declarations
        for decl in pipeline_result.declarations:
            bbox_dict = decl.bounding_box.to_dict() if decl.bounding_box else None
            decl_record = Declaration(
                inspection_id=inspection_id,
                image_id=img.id,
                field_name=decl.field_name,
                field_value=decl.field_value,
                raw_text=decl.raw_text,
                confidence_score=decl.confidence,
                bounding_box=bbox_dict,
                extraction_method=decl.extraction_method or "gemini_vision",
            )
            db.add(decl_record)
            all_saved_declarations.append(decl_record)
            all_field_confidences.append(decl.confidence)

        # Persist OCR Regions
        for region in pipeline_result.ocr_regions:
            rbox_dict = region.bounding_box.to_dict() if region.bounding_box else None
            ocr_record = OCRRegion(
                inspection_id=inspection_id,
                image_id=img.id,
                text=region.text,
                confidence_score=region.confidence,
                bounding_box=rbox_dict,
                language=getattr(region, "language", None),
            )
            db.add(ocr_record)
            all_saved_ocr_regions.append(ocr_record)

        img.processing_status = "COMPLETED"
        img.processed_at = datetime.now(timezone.utc)

    # Compute mean confidence score
    mean_confidence = (
        float(sum(all_field_confidences) / len(all_field_confidences))
        if all_field_confidences
        else 0.0
    )

    inspection.ai_pipeline_status = "COMPLETED"
    inspection.status = "ANALYSIS_COMPLETE"
    inspection.overall_compliance_status = "NEEDS_REVIEW"
    inspection.ai_confidence_score = round(mean_confidence, 4)

    await db.commit()
    for d in all_saved_declarations:
        await db.refresh(d)
    for r in all_saved_ocr_regions:
        await db.refresh(r)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return AnalysisResult(
        inspection_id=inspection_id,
        pipeline_status="COMPLETED",
        notice=None,
        declarations=[DeclarationResponse.model_validate(d) for d in all_saved_declarations],
        ocr_regions=[OCRRegionResponse.model_validate(r) for r in all_saved_ocr_regions],
        violations=[],
        overall_compliance_status="NEEDS_REVIEW",
        confidence_score=inspection.ai_confidence_score,
        processing_time_ms=elapsed_ms,
    )
