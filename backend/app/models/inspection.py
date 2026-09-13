"""
Inspection and InspectionImage ORM Models
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Text, Float, Integer, BigInteger,
    ForeignKey, DateTime, Enum as SAEnum, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.session import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(
            "DRAFT", "IN_PROGRESS", "ANALYSIS_PENDING",
            "ANALYSIS_COMPLETE", "COMPLETED", "CANCELLED",
            name="inspection_status"
        ),
        nullable=False, default="DRAFT"
    )
    overall_compliance_status: Mapped[str] = mapped_column(
        SAEnum(
            "COMPLIANT", "NON_COMPLIANT", "WARNING", "NEEDS_REVIEW", "PENDING",
            name="compliance_status"
        ),
        nullable=False, default="PENDING"
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=True
    )
    inspector_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    ai_pipeline_status: Mapped[str] = mapped_column(
        SAEnum(
            "NOT_STARTED", "PREPROCESSING", "OCR", "EXTRACTION",
            "RULE_CHECK", "COMPLETED", "FAILED", "DEV_STUB",
            name="pipeline_status"
        ),
        nullable=False, default="NOT_STARTED"
    )
    ai_confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    product = relationship("Product", back_populates="inspections")
    inspector = relationship("User", back_populates="inspections", foreign_keys=[inspector_id])
    images = relationship("InspectionImage", back_populates="inspection", cascade="all, delete-orphan")
    declarations = relationship("Declaration", back_populates="inspection", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="inspection", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="inspection", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Inspection id={self.id} number={self.inspection_number}>"


class InspectionImage(Base):
    __tablename__ = "inspection_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    image_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    label: Mapped[str] = mapped_column(
        SAEnum("FRONT", "BACK", "SIDE", "TOP", "BOTTOM", "OTHER", name="image_label"),
        nullable=False, default="OTHER"
    )
    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_status: Mapped[str] = mapped_column(
        SAEnum("PENDING", "PROCESSING", "COMPLETED", "FAILED", "STUB", name="processing_status"),
        nullable=False, default="PENDING"
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="images")
    declarations = relationship("Declaration", back_populates="image")

    def __repr__(self) -> str:
        return f"<InspectionImage id={self.id} label={self.label}>"
