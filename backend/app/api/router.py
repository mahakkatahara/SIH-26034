"""
API Router — aggregates all route modules
"""
from fastapi import APIRouter

from app.api import auth, products, inspections, rules, reports, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(rules.router, prefix="/rules", tags=["Rules"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
