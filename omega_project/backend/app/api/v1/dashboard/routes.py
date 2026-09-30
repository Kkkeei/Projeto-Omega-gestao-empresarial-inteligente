from fastapi import APIRouter
from app.services.dashboard_service import resumo

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/resumo")
def dashboard_resumo():
    return resumo()
