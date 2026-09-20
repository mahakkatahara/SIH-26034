"""
Violation ORM Model — compliance violations detected by the rule engine
"""
import uuid
from datetime import datetime, timezone
from typing import ClassVar
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.session import Base


class Violation(Base):
    """
    A violation is raised when the deterministic rule engine determines
    that a declaration is missing, incorrect, or non-compliant.
    """
    __tablename__ = "violations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"), nullable=True
    )
    declaration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("declarations.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[str] = mapped_column(
        SAEnum("HIGH", "MEDIUM", "LOW", "INFO", name="violation_severity"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        SAEnum("OPEN", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE", name="violation_status"),
        nullable=False, default="OPEN"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    legal_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON: {"x": 10, "y": 20, "width": 100, "height": 30, "image_id": "uuid"}
    evidence_region: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="violations")
    rule = relationship("Rule", back_populates="violations")
    declaration = relationship("Declaration", back_populates="violations")

    _citation_verified: ClassVar[bool | None] = None

    @property
    def citation_verified(self) -> bool:
        if self._citation_verified is not None:
            return self._citation_verified
        try:
            return bool(self.rule.citation_verified) if self.rule else False
        except Exception:
            return False

    @citation_verified.setter
    def citation_verified(self, value: bool) -> None:
        self._citation_verified = value

    def __repr__(self) -> str:
        return f"<Violation id={self.id} severity={self.severity} status={self.status}>"

