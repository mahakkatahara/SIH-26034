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
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, require_inspector_or_above
from app.database.session import get_db_session
from app.models.inspection import Inspection, InspectionImage
from app.models.declaration import Declaration
from app.models.ocr_region import OCRRegion
from app.models.violation import Violation
from app.models.rule import Rule
from app.models.user import User
from app.schemas.inspection import (
    InspectionCreate, InspectionUpdate, InspectionResponse,
    InspectionDetailResponse, InspectionListResponse,
    InspectionImageResponse, AnalysisResult, DeclarationResponse,
    OCRRegionResponse, ViolationResponse,
)
from ai.pipeline.stub_pipeline import get_pipeline, StubPipeline
from engine import get_rule_engine

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

    # Ensure re-analysis is idempotent: clean up previous analysis records in the same transaction
    await db.execute(delete(Violation).where(Violation.inspection_id == inspection_id))
    await db.execute(delete(Declaration).where(Declaration.inspection_id == inspection_id))
    await db.execute(delete(OCRRegion).where(OCRRegion.inspection_id == inspection_id))

    all_saved_declarations = []
    all_saved_ocr_regions = []

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
        try:
            pipeline_result = pipeline.analyze(resolved_path, str(img.id))
        except Exception as exc:
            inspection.ai_pipeline_status = "FAILED"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI pipeline analysis failed: {exc}",
            )

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
            decl_record.panel = img.label
            decl_record.extraction_status = getattr(decl, "extraction_status", "answered")
            db.add(decl_record)
            all_saved_declarations.append(decl_record)

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

    # Compute mean confidence score over extracted fields only (non-null and confidence > 0.0)
    extracted_confidences = [
        d.confidence_score
        for d in all_saved_declarations
        if d.field_value is not None and str(d.field_value).strip() and (d.confidence_score or 0.0) > 0.0
    ]
    mean_confidence = (
        float(sum(extracted_confidences) / len(extracted_confidences))
        if extracted_confidences
        else 0.0
    )

    # Flush to generate IDs for new declarations
    await db.flush()

    # Map image_id to image label (panel)
    img_label_map = {img.id: img.label for img in inspection.images}

    # Run deterministic rule engine
    rule_engine = get_rule_engine()
    decl_dicts = [
        {
            "id": str(d.id) if d.id else None,
            "declaration_id": str(d.id) if d.id else None,
            "image_id": str(d.image_id) if d.image_id else None,
            "panel": img_label_map.get(d.image_id),
            "field_name": d.field_name,
            "field_value": d.field_value,
            "raw_text": d.raw_text,
            "confidence": d.confidence_score,
            "bounding_box": d.bounding_box,
            "extraction_status": getattr(d, "extraction_status", "answered"),
        }
        for d in all_saved_declarations
    ]
    product_category = getattr(inspection.product, "category", None) if inspection.product else None
    product_pkg_type = getattr(inspection.product, "package_type", "retail") if inspection.product else "retail"

    PERISHABLE_CATEGORIES = {
        "food", "beverage", "grocery", "perishable",
        "confectionery", "snacks", "dairy", "bakery",
        "meat", "seafood", "produce", "edible oil", "sweets"
    }
    NON_PERISHABLE_CATEGORIES = {
        "electronics", "hardware", "textiles", "apparel",
        "stationery", "cosmetics", "toys", "footwear", "utensils"
    }

    is_perishable: Optional[bool] = None
    if inspection.product and getattr(inspection.product, "is_perishable", None) is not None:
        is_perishable = bool(inspection.product.is_perishable)
    elif product_category:
        cat_lower = str(product_category).strip().lower()
        if any(c in cat_lower for c in PERISHABLE_CATEGORIES):
            is_perishable = True
        elif any(c in cat_lower for c in NON_PERISHABLE_CATEGORIES):
            is_perishable = False
        else:
            is_perishable = None  # Unknown category => triggers NEEDS_REVIEW on DATE-002
    else:
        is_perishable = None  # Missing context => triggers NEEDS_REVIEW on DATE-002

    requires_usp = (product_pkg_type == "retail")
    is_imported = getattr(inspection.product, "is_imported", None) if inspection.product else None

    compliance_result = rule_engine.evaluate(
        declarations=decl_dicts,
        product_category=product_category,
        product_context={
            "package_type": product_pkg_type or "retail",
            "is_perishable": is_perishable,
            "requires_usp": requires_usp,
            "is_imported": is_imported,
        },
        overall_confidence=mean_confidence,
        confidence_threshold=settings.AI_CONFIDENCE_THRESHOLD,
        package_type=product_pkg_type or "retail",
    )

    # Fetch DB rules for mapping rule_id string (e.g. MRP-001) to rule UUID
    db_rules = (await db.execute(select(Rule))).scalars().all()
    rule_id_map = {r.rule_id: r.id for r in db_rules}

    all_saved_violations = []
    for issue in compliance_result.violations + compliance_result.warnings:
        target_decl_id = None
        if issue.declaration_id and str(issue.declaration_id) != "None":
            try:
                target_decl_id = UUID(str(issue.declaration_id))
            except (ValueError, TypeError):
                target_decl_id = None

        v_rec = Violation(
            inspection_id=inspection_id,
            rule_id=rule_id_map.get(issue.rule_id),
            declaration_id=target_decl_id,
            severity=issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
            status="OPEN",
            description=issue.description,
            legal_reference=issue.legal_reference,
            evidence_region=issue.evidence,
        )
        v_rec.citation_verified = getattr(issue, "citation_verified", False)
        db.add(v_rec)
        all_saved_violations.append(v_rec)

    inspection.ai_pipeline_status = "COMPLETED"
    inspection.status = "ANALYSIS_COMPLETE"
    inspection.overall_compliance_status = compliance_result.status.value
    inspection.ai_confidence_score = round(mean_confidence, 4)

    await db.commit()
    for d in all_saved_declarations:
        await db.refresh(d)
    for r in all_saved_ocr_regions:
        await db.refresh(r)
    for v in all_saved_violations:
        await db.refresh(v)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return AnalysisResult(
        inspection_id=inspection_id,
        pipeline_status="COMPLETED",
        notice=None,
        declarations=[DeclarationResponse.model_validate(d) for d in all_saved_declarations],
        ocr_regions=[OCRRegionResponse.model_validate(r) for r in all_saved_ocr_regions],
        violations=[ViolationResponse.model_validate(v) for v in all_saved_violations],
        overall_compliance_status=compliance_result.status.value,
        confidence_score=inspection.ai_confidence_score,
        processing_time_ms=elapsed_ms,
    )
