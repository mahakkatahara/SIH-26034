"""
Rule ORM Model — compliance rule definitions (data-driven)
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.session import Base


class Rule(Base):
    """
    A compliance rule definition from Legal Metrology (Packaged Commodities) Rules, 2011.
    Rules are data-driven (stored in DB and rules.json) — not hard-coded in application logic.
    """
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Human-readable rule code, e.g., "MRP-001"
    rule_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # NULL category means the rule applies to all product categories
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    severity: Mapped[str] = mapped_column(
        SAEnum("HIGH", "MEDIUM", "LOW", "INFO", name="violation_severity"),
        nullable=False, default="HIGH"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON validation logic descriptor (interpreted by the rule engine)
    validation_logic: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    legal_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    package_type: Mapped[str] = mapped_column(String(20), nullable=False, default="retail")
    citation_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    violations = relationship("Violation", back_populates="rule")

    def __repr__(self) -> str:
        return f"<Rule rule_id={self.rule_id} field={self.field} severity={self.severity}>"
