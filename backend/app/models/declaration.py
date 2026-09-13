"""
Declaration ORM Model — extracted declarations from package images
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.session import Base


class Declaration(Base):
    """
    A declaration is a piece of mandatory information extracted from
    a package label (e.g., MRP, net quantity, manufacturer name).
    """
    __tablename__ = "declarations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False
    )
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspection_images.id", ondelete="SET NULL"), nullable=True
    )
    # Field name: mrp, net_quantity, manufacturer_name, manufacturer_address,
    #             manufacturing_date, consumer_care_info, country_of_origin, etc.
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # JSON: {"x": 10, "y": 20, "width": 100, "height": 30, "page_width": 800}
    bounding_box: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extraction_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="declarations")
    image = relationship("InspectionImage", back_populates="declarations")
    violations = relationship("Violation", back_populates="declaration")

    def __repr__(self) -> str:
        return f"<Declaration id={self.id} field={self.field_name} value={self.field_value!r}>"
