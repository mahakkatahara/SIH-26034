"""
OCRRegion ORM Model — text regions detected by the OCR engine / vision pipeline
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database.session import Base


class OCRRegion(Base):
    """
    An OCR region represents a detected text area on an image,
    including text, bounding box coordinates, and confidence.
    """
    __tablename__ = "ocr_regions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspection_images.id", ondelete="SET NULL"), nullable=True, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # JSON: {"x": 10, "y": 20, "width": 100, "height": 30, "x1": 10, "y1": 20, "x2": 110, "y2": 50}
    bounding_box: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    inspection = relationship("Inspection", back_populates="ocr_regions")
    image = relationship("InspectionImage", back_populates="ocr_regions")

    def __repr__(self) -> str:
        return f"<OCRRegion id={self.id} text={self.text[:30]!r} confidence={self.confidence_score}>"
