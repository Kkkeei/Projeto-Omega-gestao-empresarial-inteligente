import asyncio
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Carrega configuração antes dos módulos que leem variáveis de ambiente no import.
load_dotenv(Path(__file__).resolve().parent / ".env")

from app.core.cors import development_origin_regex, parse_cors_origins
from app.db.database import criar_tabelas
from app.api.v1.routes import router as api_router
from app.api.v1.auth.routes import router as auth_router
from app.services.sincronizacao_inicial import sincronizar_todas_ao_iniciar
from app.modules.nfse import service as nfse_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omega")


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()

    async def executar_agenda_nfse():
        # A agenda só processa titulares que habilitaram explicitamente a
        # sincronização na configuração da aba NFS-e. O A3 sempre aguarda o
        # Bridge local; o servidor nunca tenta acessar cartão/token físico.
        while True:
            try:
                await asyncio.to_thread(nfse_service.processar_rotinas_automaticas)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Falha no ciclo da agenda de NFS-e.")
            await asyncio.sleep(60)

    # Só inicia o agendador quando o serviço tiver uma implementação real.
    # Não cria uma rotina fictícia nem tenta consultar certificados/cartões A3 no servidor.
    processador_nfse = getattr(nfse_service, "processar_rotinas_automaticas", None)
    if callable(processador_nfse):
        tarefa_agenda_nfse = asyncio.create_task(executar_agenda_nfse())
        app.state.agenda_nfse = tarefa_agenda_nfse
    else:
        tarefa_agenda_nfse = None
        app.state.agenda_nfse = None
        logger.info(
            "Agenda automática de NFS-e indisponível nesta versão; "
            "as consultas continuam sendo iniciadas sob demanda."
        )

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
        if tarefa_agenda_nfse is not None and not tarefa_agenda_nfse.done():
            tarefa_agenda_nfse.cancel()
            try:
                await tarefa_agenda_nfse
            except asyncio.CancelledError:
                pass
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

_cors_origins = parse_cors_origins(
    os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=development_origin_regex(os.getenv("OMEGA_ENV", "development")),
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
