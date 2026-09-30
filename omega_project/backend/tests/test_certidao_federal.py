import pytest


def test_persistencia_certidao_federal_mock(monkeypatch):
    from app.services import receita_federal_service
    from app.db.database import conectar_banco

    async def fake_browser(cnpj):
        return {
            "situacao": "REGULAR",
            "status_processamento": "Sucesso",
            "mensagem": "Certidão obtida no portal da Receita Federal.",
            "numero_certidao": "ABC123456",
            "data_emissao": "2026-09-14",
            "data_validade": "2026-12-13",
            "pendencia": False,
            "texto_extraido": "Certidão Negativa de Débitos Relativos a Créditos Tributários Federais e à Dívida Ativa da União.",
        }

    monkeypatch.setattr(receita_federal_service, "_executar_browser", fake_browser)
    resultado = __import__("asyncio").run(receita_federal_service.consultar_federal(1))

    assert resultado["situacao"] == "REGULAR"
    assert resultado["consulta_id"]

    c = conectar_banco()
    try:
        assert c.execute("SELECT COUNT(*) n FROM certidoes WHERE empresa_id=1 AND tipo_certidao_id=1").fetchone()["n"] == 1
        assert c.execute("SELECT COUNT(*) n FROM consultas_certidoes WHERE empresa_id=1 AND tipo_certidao_id=1").fetchone()["n"] >= 1
        assert c.execute("SELECT COUNT(*) n FROM certidoes_historico WHERE empresa_id=1 AND tipo_certidao_id=1").fetchone()["n"] >= 1
        assert c.execute("SELECT COUNT(*) n FROM execucoes_automacao WHERE empresa_id=1 AND tipo='CONSULTA_CERTIDAO_FEDERAL'").fetchone()["n"] >= 1
    finally:
        c.close()
