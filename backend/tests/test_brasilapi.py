import pytest

from app.services import brasilapi


class FakeResponse:
    status_code = 200
    headers = {}

    def raise_for_status(self):
        return None

    def json(self):
        raise ValueError("resposta JSON inválida")


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        return FakeResponse()


@pytest.mark.asyncio
async def test_brasilapi_resposta_json_invalida_gera_erro_controlado(monkeypatch):
    monkeypatch.setattr(brasilapi.httpx, "AsyncClient", FakeClient)
    with pytest.raises(brasilapi.BrasilAPIError) as exc:
        await brasilapi.consultar_cnpj("11222333000181")
    assert exc.value.status_code == 502
    assert "resposta inválida" in str(exc.value)
