from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.batches import router as batches_router
from app.api.v1.protected_routes import router as protected_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(batches_router)
api_v1_router.include_router(protected_router)
api_v1_router.include_router(audit_router)

__all__ = ["api_v1_router"]
