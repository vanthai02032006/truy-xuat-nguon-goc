from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.batches import router as batches_router
from app.api.v1.farming import router as farming_router
from app.api.v1.finance import router as finance_router
from app.api.v1.handovers import router as handovers_router
from app.api.v1.hr import router as hr_router
from app.api.v1.land_plots import router as land_plots_router
from app.api.v1.materials import router as materials_router
from app.api.v1.protected_routes import router as protected_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(batches_router)
api_v1_router.include_router(handovers_router)
api_v1_router.include_router(land_plots_router)
api_v1_router.include_router(materials_router)
api_v1_router.include_router(hr_router)
api_v1_router.include_router(finance_router)
api_v1_router.include_router(farming_router)
api_v1_router.include_router(protected_router)
api_v1_router.include_router(audit_router)

__all__ = ["api_v1_router"]
