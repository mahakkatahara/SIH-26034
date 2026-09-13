"""
Dashboard API Routes — stats, trends, recent inspections
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.inspection import Inspection
from app.models.violation import Violation
from app.models.user import User
from app.schemas.rule import DashboardStats, ViolationTypeCount, TrendDataPoint

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return summary statistics for the dashboard."""
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)

    # Base query (inspectors see only their own)
    base_filter = []
    if current_user.role == "INSPECTOR":
        base_filter.append(Inspection.inspector_id == current_user.id)

    total = await db.scalar(
        select(func.count(Inspection.id)).where(*base_filter)
    ) or 0

    compliant = await db.scalar(
        select(func.count(Inspection.id)).where(
            *base_filter,
            Inspection.overall_compliance_status == "COMPLIANT"
        )
    ) or 0

    non_compliant = await db.scalar(
        select(func.count(Inspection.id)).where(
            *base_filter,
            Inspection.overall_compliance_status == "NON_COMPLIANT"
        )
    ) or 0

    needs_review = await db.scalar(
        select(func.count(Inspection.id)).where(
            *base_filter,
            Inspection.overall_compliance_status == "NEEDS_REVIEW"
        )
    ) or 0

    warning = await db.scalar(
        select(func.count(Inspection.id)).where(
            *base_filter,
            Inspection.overall_compliance_status == "WARNING"
        )
    ) or 0

    total_violations = await db.scalar(select(func.count(Violation.id))) or 0

    this_month = await db.scalar(
        select(func.count(Inspection.id)).where(
            *base_filter,
            Inspection.created_at >= start_of_month
        )
    ) or 0

    this_week = await db.scalar(
        select(func.count(Inspection.id)).where(
            *base_filter,
            Inspection.created_at >= start_of_week
        )
    ) or 0

    compliance_pct = round((compliant / total * 100), 1) if total > 0 else 0.0

    return DashboardStats(
        total_inspections=total,
        compliant=compliant,
        non_compliant=non_compliant,
        needs_review=needs_review,
        warning=warning,
        compliance_percentage=compliance_pct,
        total_violations=total_violations,
        inspections_this_month=this_month,
        inspections_this_week=this_week,
    )


@router.get("/recent")
async def get_recent_inspections(
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Return recent inspections for the dashboard table."""
    query = select(Inspection).order_by(Inspection.created_at.desc()).limit(limit)
    if current_user.role == "INSPECTOR":
        query = query.where(Inspection.inspector_id == current_user.id)

    result = await db.execute(query)
    inspections = result.scalars().all()

    return [
        {
            "id": str(i.id),
            "inspection_number": i.inspection_number,
            "status": i.status,
            "overall_compliance_status": i.overall_compliance_status,
            "product_id": str(i.product_id) if i.product_id else None,
            "created_at": i.created_at.isoformat(),
        }
        for i in inspections
    ]


@router.get("/trend")
async def get_inspection_trend(
    days: int = 30,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    """
    Return daily inspection counts for the past N days.
    Used for the dashboard trend chart.
    """
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", Inspection.created_at).label("date"),
            func.count(Inspection.id).label("total"),
            func.count(
                func.nullif(Inspection.overall_compliance_status != "COMPLIANT", True)
            ).label("compliant"),
        )
        .where(Inspection.created_at >= start_date)
        .group_by(func.date_trunc("day", Inspection.created_at))
        .order_by(func.date_trunc("day", Inspection.created_at))
    )
    rows = result.all()

    return [
        {
            "date": row.date.strftime("%Y-%m-%d") if row.date else "",
            "total": row.total,
            "compliant": row.compliant or 0,
            "non_compliant": (row.total - (row.compliant or 0)),
        }
        for row in rows
    ]


@router.get("/violations/top")
async def get_top_violations(
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    """Return most common violation types for the dashboard."""
    from app.models.rule import Rule
    from sqlalchemy.orm import aliased

    result = await db.execute(
        select(
            Violation.description,
            Violation.severity,
            func.count(Violation.id).label("count"),
        )
        .group_by(Violation.description, Violation.severity)
        .order_by(func.count(Violation.id).desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {"description": row.description, "severity": row.severity, "count": row.count}
        for row in rows
    ]
