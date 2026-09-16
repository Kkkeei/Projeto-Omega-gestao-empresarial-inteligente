from fastapi import APIRouter, Depends

from app.api.v1.auth.routes import current_user
from app.api.v1.certidoes.routes import router as certidoes_router
from app.api.v1.dashboard.routes import router as dashboard_router
from app.api.v1.empresas.routes import router as empresas_router
from app.api.v1.pendencias.routes import router as pendencias_router
from app.modules.documentacao.routes import router as documentacao_router

router = APIRouter(dependencies=[Depends(current_user)])
router.include_router(empresas_router)
router.include_router(certidoes_router)
router.include_router(pendencias_router)
router.include_router(dashboard_router)
router.include_router(documentacao_router)
