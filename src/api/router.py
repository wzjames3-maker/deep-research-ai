from fastapi import APIRouter
from src.api.auth.router import router as auth_router
from src.api.research.router import router as research_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router, prefix="/auth")
router.include_router(research_router, prefix="/research")
