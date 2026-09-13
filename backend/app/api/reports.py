"""
Reports API Routes — generate and download compliance reports
"""
from datetime import datetime, timezone
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.inspection import Inspection
from app.models.report import Report
from app.models.user import User
from app.schemas.rule import ReportGenerateRequest, ReportResponse

router = APIRouter()


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Report).order_by(Report.created_at.desc()))
    reports = result.scalars().all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.post("/generate", response_model=ReportResponse, status_code=201)
async def generate_report(
    data: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a compliance report for an inspection.

    ⚠ PHASE 1 DEV STUB: PDF/DOCX generation is not yet implemented.
    This will be integrated in Phase 8.
    """
    # Verify inspection exists
    result = await db.execute(select(Inspection).where(Inspection.id == data.inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    report = Report(
        inspection_id=data.inspection_id,
        report_type=data.report_type,
        generation_status="STUB",
        generated_by_id=current_user.id,
        generated_at=datetime.now(timezone.utc),
        # file_path will be set when actual generation is implemented in Phase 8
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    """
    ⚠ PHASE 1 DEV STUB: Download not yet available.
    Will return actual PDF/DOCX file in Phase 8.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "Report download not yet implemented (Phase 8 — Report Generation). "
            "PDF and DOCX generation will be available after Phase 8 implementation."
        ),
    )
