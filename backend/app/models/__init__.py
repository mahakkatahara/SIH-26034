"""Models package — imports all ORM models so Alembic can detect them."""
from app.models.user import User
from app.models.product import Product
from app.models.inspection import Inspection, InspectionImage
from app.models.declaration import Declaration
from app.models.ocr_region import OCRRegion
from app.models.violation import Violation
from app.models.rule import Rule
from app.models.report import Report

__all__ = [
    "User",
    "Product",
    "Inspection",
    "InspectionImage",
    "Declaration",
    "OCRRegion",
    "Violation",
    "Rule",
    "Report",
]
