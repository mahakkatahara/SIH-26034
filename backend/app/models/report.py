"""
Report ORM Model — generated compliance reports
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.session import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(
        SAEnum("PDF", "DOCX", name="report_type"),
        nullable=False, default="PDF"
    )
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    generation_status: Mapped[str] = mapped_column(
        SAEnum("PENDING", "GENERATING", "COMPLETED", "FAILED", "STUB", name="report_status"),
        nullable=False, default="PENDING"
    )
    generated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="reports")
    generated_by = relationship("User", back_populates="reports", foreign_keys=[generated_by_id])

    def __repr__(self) -> str:
        return f"<Report id={self.id} type={self.report_type} status={self.generation_status}>"
