import asyncio
import os

import httpx


BASE_URL = "https://brasilapi.com.br/api/cnpj/v1"
DEFAULT_TIMEOUT = float(os.getenv("BRASILAPI_TIMEOUT", "20"))
MAX_RETRIES = int(os.getenv("BRASILAPI_MAX_RETRIES", "3"))


class BrasilAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _digits(cnpj: str) -> str:
    return "".join(ch for ch in str(cnpj) if ch.isdigit())


async def consultar_cnpj(cnpj: str) -> dict:
    digits = _digits(cnpj)
    if len(digits) != 14:
        raise BrasilAPIError("CNPJ inválido para consulta na BrasilAPI.")

    headers = {"User-Agent": "OMEGA-Gestao/1.0"}
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as client:
        ultimo_erro: Exception | None = None
        for tentativa in range(MAX_RETRIES + 1):
            try:
                response = await client.get(f"{BASE_URL}/{digits}")
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        espera = min(60.0, max(1.0, float(retry_after))) if retry_after else min(30.0, 2 ** tentativa)
                    except ValueError:
                        espera = min(30.0, 2 ** tentativa)
                    if tentativa >= MAX_RETRIES:
                        raise BrasilAPIError("BrasilAPI atingiu o limite de requisições. Tente novamente mais tarde.", 429)
                    await asyncio.sleep(espera)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                ultimo_erro = exc
                if tentativa >= MAX_RETRIES:
                    raise BrasilAPIError("Tempo esgotado ao consultar a BrasilAPI.") from exc
                await asyncio.sleep(min(15.0, 2 ** tentativa))
            except httpx.HTTPStatusError as exc:
                ultimo_erro = exc
                if tentativa >= MAX_RETRIES or exc.response.status_code < 500:
                    raise BrasilAPIError(f"BrasilAPI respondeu HTTP {exc.response.status_code}.", exc.response.status_code) from exc
                await asyncio.sleep(min(15.0, 2 ** tentativa))
            except httpx.HTTPError as exc:
                ultimo_erro = exc
                if tentativa >= MAX_RETRIES:
                    raise BrasilAPIError(f"Falha de comunicação com a BrasilAPI: {exc}") from exc
                await asyncio.sleep(min(15.0, 2 ** tentativa))
        raise BrasilAPIError("Falha desconhecida na consulta da BrasilAPI.") from ultimo_erro


def mapear_brasilapi(d: dict) -> dict:
    return {
      'razao_social':d.get('razao_social'),'nome_fantasia':d.get('nome_fantasia'),'data_abertura':d.get('data_inicio_atividade'),
      'natureza_juridica':d.get('natureza_juridica'),'porte':d.get('porte'),'capital_social':d.get('capital_social'),
      'cnae_principal':str(d.get('cnae_fiscal')) if d.get('cnae_fiscal') is not None else None,
      'logradouro':d.get('logradouro'),'numero':d.get('numero'),'complemento':d.get('complemento'),'bairro':d.get('bairro'),
      'municipio':d.get('municipio'),'codigo_ibge':str(d.get('codigo_municipio')) if d.get('codigo_municipio') is not None else None,
      'uf':d.get('uf'),'cep':d.get('cep'),'telefone':d.get('ddd_telefone_1') or d.get('ddd_telefone_2')
    }
