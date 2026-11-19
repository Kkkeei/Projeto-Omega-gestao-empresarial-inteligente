from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.modules.nfse import routes


def test_gerar_pdf_cria_pdf_a_partir_do_xml_sem_alterar_original():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <CompNfse><Nfse><InfNfse><Numero>123</Numero><DataEmissao>2026-10-15</DataEmissao>
    <ValorServicos>150.00</ValorServicos></InfNfse></Nfse></CompNfse>'''
    with patch.object(routes.service, "detalhe", return_value={
        "id": 1, "numero": "123", "nsu": 7, "origem": "PJ",
        "data_emissao": "2026-10-15", "valor": 150.0,
        "chave_acesso": "CHAVE-TESTE", "situacao": "NORMAL", "xml": xml,
    }):
        response = routes.gerar_pdf(1, _user={"id": 1})
    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF-")
    assert b"attachment; filename=\"nfse-123.pdf\"" in response.headers["content-disposition"].encode()


def test_gerar_pdf_informa_quando_xml_nao_existe():
    with patch.object(routes.service, "detalhe", return_value={"id": 1, "xml": None}):
        with pytest.raises(HTTPException) as exc:
            routes.gerar_pdf(1, _user={"id": 1})
    assert exc.value.status_code == 404
