import asyncio
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import criar_tabelas
from app.api.v1.routes import router as api_router
from app.api.v1.auth.routes import router as auth_router
from app.services.sincronizacao_inicial import sincronizar_todas_ao_iniciar

load_dotenv(Path(__file__).resolve().parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega")


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()

    # Por padrão, NÃO sincroniza todas as empresas na inicialização.
    # Isso evita rajadas de chamadas externas (ex.: BrasilAPI) e HTTP 429.
    # A sincronização em lote só é ativada explicitamente por ambiente.
    tarefa_sync = None
    sync_on_startup = os.getenv("OMEGA_SYNC_ON_STARTUP", "false").strip().lower() in {"1", "true", "sim", "yes"}
    if sync_on_startup:
        tarefa_sync = asyncio.create_task(sincronizar_todas_ao_iniciar())
        app.state.sincronizacao_inicial = tarefa_sync
        logger.warning("Sincronização inicial habilitada via OMEGA_SYNC_ON_STARTUP=true.")
    else:
        app.state.sincronizacao_inicial = None
        logger.info("Sincronização inicial automática desabilitada; empresas existentes serão mantidas como estão no banco.")

    try:
        yield
    finally:
        if tarefa_sync is not None and not tarefa_sync.done():
            tarefa_sync.cancel()
            try:
                await tarefa_sync
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="ÔMEGA - Gestão Empresarial",
    version="1.1.0",
    description="Backend MVP da Plataforma ÔMEGA de Gestão Empresarial.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://192.168.100.3:5173").split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok", "sistema": "ÔMEGA"}


@app.get("/", tags=["Sistema"])
def raiz():
    return {"sistema": "ÔMEGA - Gestão Empresarial", "status": "online", "versao": "1.1.0"}


app.include_router(auth_router)
app.include_router(api_router)
