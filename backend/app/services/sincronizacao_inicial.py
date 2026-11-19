import asyncio
import logging
import os

from app.services.empresas_service import listar_empresas, sincronizar_empresa

logger = logging.getLogger("omega.sincronizacao")


async def sincronizar_todas_ao_iniciar(concorrencia: int = 1, intervalo_segundos: float | None = None) -> None:
    """Sincronização opcional e controlada para evitar 429 em provedores externos.

    Não é chamada automaticamente por padrão; consulte OMEGA_SYNC_ON_STARTUP.
    """
    empresas = listar_empresas(ativo=True)
    if not empresas:
        logger.info("Sincronização inicial: nenhuma empresa ativa encontrada.")
        return

    intervalo = float(os.getenv("BRASILAPI_INTERVAL_SECONDS", "2.0")) if intervalo_segundos is None else intervalo_segundos
    sem = asyncio.Semaphore(max(1, concorrencia))

    async def sincronizar_um(empresa):
        async with sem:
            try:
                _, alteracoes = await sincronizar_empresa(empresa["id"])
                logger.info("Sincronização inicial concluída: empresa_id=%s alteracoes=%s", empresa["id"], len(alteracoes))
                return True
            except Exception as exc:
                logger.error("Falha na sincronização inicial da empresa_id=%s: %s", empresa["id"], exc)
                return False
            finally:
                if intervalo > 0:
                    await asyncio.sleep(intervalo)

    resultados = []
    for empresa in empresas:
        resultados.append(await sincronizar_um(empresa))

    ok = sum(resultados)
    erros = len(resultados) - ok
    logger.info("Sincronização inicial finalizada: total=%s sucesso=%s erros=%s", len(resultados), ok, erros)
