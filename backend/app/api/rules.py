"""
Rules API Routes
"""
import math
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin
from app.database.session import get_db_session
from app.models.rule import Rule
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleUpdate, RuleResponse, RuleListResponse

router = APIRouter()


@router.get("", response_model=RuleListResponse)
async def list_rules(
    field: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    query = select(Rule)
    if field:
        query = query.where(Rule.field == field)
    if severity:
        query = query.where(Rule.severity == severity)
    if is_active is not None:
        query = query.where(Rule.is_active == is_active)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Rule.rule_id))
    rules = result.scalars().all()

    return RuleListResponse(
        items=[RuleResponse.model_validate(r) for r in rules],
        total=total or 0,
    )


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return RuleResponse.model_validate(rule)


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    data: RuleCreate,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    # Check for duplicate rule_id
    existing = await db.scalar(select(Rule).where(Rule.rule_id == data.rule_id))
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule {data.rule_id} already exists")

    rule = Rule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: UUID,
    data: RuleUpdate,
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)
