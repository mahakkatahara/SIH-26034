"""
Pydantic Schemas — Rule and Report
"""
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ─── Rule ─────────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    rule_id: str = Field(..., pattern=r"^[A-Z]+-\d{3}$", description="e.g., MRP-001")
    field: str
    category: Optional[str] = None
    mandatory: bool = True
    severity: str = Field(default="HIGH", pattern="^(HIGH|MEDIUM|LOW|INFO)$")
    description: str
    validation_logic: Optional[Dict[str, Any]] = None
    legal_reference: Optional[str] = None
    rule_version: str = "1.0"


class RuleUpdate(BaseModel):
    description: Optional[str] = None
    mandatory: Optional[bool] = None
    severity: Optional[str] = None
    validation_logic: Optional[Dict[str, Any]] = None
    legal_reference: Optional[str] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: str
    field: str
    category: Optional[str] = None
    mandatory: bool
    severity: str
    description: str
    validation_logic: Optional[Dict[str, Any]] = None
    legal_reference: Optional[str] = None
    rule_version: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RuleListResponse(BaseModel):
    items: List[RuleResponse]
    total: int


# ─── Report ───────────────────────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    inspection_id: UUID
    report_type: str = Field(default="PDF", pattern="^(PDF|DOCX)$")


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inspection_id: UUID
    report_type: str
    file_path: Optional[str] = None
    generation_status: str
    generated_by_id: Optional[UUID] = None
    generated_at: Optional[datetime] = None
    created_at: datetime


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_inspections: int
    compliant: int
    non_compliant: int
    needs_review: int
    warning: int
    compliance_percentage: float
    total_violations: int
    inspections_this_month: int
    inspections_this_week: int


class ViolationTypeCount(BaseModel):
    field: str
    count: int
    severity: str


class TrendDataPoint(BaseModel):
    date: str
    total: int
    compliant: int
    non_compliant: int
