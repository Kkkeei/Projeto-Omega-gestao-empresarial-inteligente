from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.db import database
from app.modules.impostos import notificacoes_service, relatorio_service, repository, service
from app.modules.impostos.routes import marcar_pago


@pytest.fixture
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "omega.db"
    storage = tmp_path / "storage"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database, "STORAGE_BASE", storage)
    database.criar_tabelas()

    conn = database.conectar_banco()
    try:
        conn.execute(
            "INSERT INTO empresas (id,cnpj,razao_social,nome_fantasia,regime_tributario,ativo) VALUES (1,?,?,?,?,1)",
            ("50410847000112", "EMPRESA TESTE LTDA", "TESTE", "SIMPLES NACIONAL"),
        )
        conn.execute(
            "INSERT INTO tributos (id,nome,sigla,esfera,periodicidade,ativo) VALUES (1,'PIS','8109','Federal','Mensal',1)"
        )
        conn.commit()
    finally:
        conn.close()
    return tmp_path


def _vincular():
    return repository.vincular_tributo(
        1,
        {"tributo_id": 1, "obrigatorio": True, "vigencia_inicio": "2026-08-01"},
    )


def test_vigencia_preserva_historico_e_remove_competencia_posterior(isolated_db):
    vinculo = _vincular()
    atualizado = repository.atualizar_vinculo(
        vinculo["id"],
        {
            "status": "INATIVO",
            "vigencia_inicio": "2026-08-01",
            "vigencia_fim": "2026-08-31",
            "obrigatorio": True,
        },
    )
    assert atualizado["status"] == "INATIVO"

    agosto = repository.listar_empresas_impostos(None, None, None, 2026, 8)
    setembro = repository.listar_empresas_impostos(None, None, None, 2026, 9)
    assert agosto["empresas"][0]["tributos_vinculados"] == 1
    assert setembro["empresas"][0]["tributos_vinculados"] == 0


def test_registro_mensal_valida_status_e_mantem_um_registro(isolated_db):
    _vincular()
    primeiro = repository.salvar_mensal(
        1,
        {
            "tributo_id": 1,
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "status": "CREDOR",
            "valor": 0,
            "observacao": "Crédito no período.",
        },
        "REGISTRO_CREDOR",
    )
    segundo = repository.salvar_mensal(
        1,
        {
            "tributo_id": 1,
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "status": "SEM_MOVIMENTACAO",
            "valor": 0,
            "observacao": "Sem fato gerador.",
        },
        "CORRECAO_SITUACAO",
    )
    assert segundo["id"] == primeiro["id"]
    assert segundo["status"] == "SEM_MOVIMENTACAO"

    with pytest.raises(ValueError, match="Situação tributária inválida"):
        repository.salvar_mensal(
            1,
            {
                "tributo_id": 1,
                "competencia_ano": 2026,
                "competencia_mes": 8,
                "status": "QUALQUER_COISA",
            },
        )

    historico = repository.listar_historico_mensal(primeiro["id"])
    assert len(historico) == 2
    assert historico[0]["status_novo"] == "SEM_MOVIMENTACAO"
    assert historico[1]["status_novo"] == "CREDOR"


def test_guia_ocr_confirmacao_documento_historico_e_notificacoes(isolated_db, monkeypatch):
    _vincular()
    texto = """
    CNPJ: 50.410.847/0001-12
    Competência 08/2026
    Vencimento: 25/09/2026
    Valor: R$ 1.250,00
    Código da receita: 8109
    Período de apuração: 01/08/2026 a 31/08/2026
    """
    monkeypatch.setattr(service, "_texto_arquivo", lambda _path: texto)
    upload = UploadFile(
        file=BytesIO(b"PDF DE TESTE"),
        filename="DARF_PIS_082026.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )

    preparado = service.preparar_guia(1, 1, 2026, 8, upload, database.STORAGE_BASE, 1)
    assert preparado["texto_extraido_disponivel"] is True
    assert preparado["extracao"]["codigo_receita"] == "8109"
    assert preparado["extracao"]["valor_extraido"] == 1250.0

    detalhe = service.confirmar_guia(
        1,
        1,
        {
            "documento_id": preparado["documento"]["id"],
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "competencia_extraida": "08/2026",
            "valor": 1250.0,
            "vencimento": "2026-09-25",
            "codigo_receita": "8109",
            "cnpj": "50.410.847/0001-12",
            "data_pagamento": None,
            "periodo_apuracao_inicio": "2026-08-01",
            "periodo_apuracao_fim": "2026-08-31",
            "mensagem_cliente": "Guia PIS da competência 08/2026.",
            "observacao": "Conferida manualmente.",
        },
    )
    assert detalhe["mensal"]["status"] == "A_PAGAR"
    assert detalhe["documentos"][0]["status_documento"] == "CONFIRMADO"
    assert detalhe["documentos"][0]["periodo_apuracao_inicio"] == "2026-08-01"
    assert detalhe["documentos"][0]["periodo_apuracao_fim"] == "2026-08-31"
    assert len(detalhe["notificacoes"]) == 3

    # Uma segunda guia deve preservar a primeira como histórico e tornar a nova atual.
    segundo_upload = UploadFile(
        file=BytesIO(b"PDF DE TESTE 2"),
        filename="DARF_PIS_082026_CORRIGIDO.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )
    preparado2 = service.preparar_guia(1, 1, 2026, 8, segundo_upload, database.STORAGE_BASE, 1)
    service.confirmar_guia(
        1,
        1,
        {
            "documento_id": preparado2["documento"]["id"],
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "valor": 1300.0,
            "vencimento": "2026-09-25",
            "codigo_receita": "8109",
            "data_pagamento": None,
        },
    )
    detalhe2 = repository.obter_detalhe_imposto(1, 1, 2026, 8)
    assert len(detalhe2["documentos"]) == 2
    assert detalhe2["documentos"][0]["nome_arquivo"] == "DARF_PIS_082026_CORRIGIDO.pdf"
    assert detalhe2["documentos"][1]["nome_arquivo"] == "DARF_PIS_082026.pdf"




def test_notificacao_de_guia_nao_depende_de_vencimento(isolated_db):
    _vincular()
    mensal = repository.salvar_mensal(
        1,
        {
            "tributo_id": 1,
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "status": "A_PAGAR",
            "valor": 250,
        },
        "TESTE_GUIA_SEM_VENCIMENTO",
    )
    eventos = notificacoes_service.programar_notificacoes(
        1, mensal["id"], "PIS", "08/2026", None, 250, mensal["status"]
    )
    assert len(eventos) == 2
    assert {evento["tipo"] for evento in eventos} == {"GUIA_ENVIADA"}

def test_guia_paga_nao_agenda_alertas_de_vencimento(isolated_db):
    _vincular()
    mensal = repository.salvar_mensal(
        1,
        {
            "tributo_id": 1,
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "status": "PAGO",
            "valor": 500,
            "data_vencimento": "2026-09-25",
            "data_pagamento": "2026-09-10",
        },
        "TESTE_PAGO",
    )
    eventos = notificacoes_service.programar_notificacoes(
        1,
        mensal["id"],
        "PIS",
        "08/2026",
        "2026-09-25",
        500,
        mensal["status"],
    )
    assert len(eventos) == 2
    assert {e["tipo"] for e in eventos} == {"GUIA_ENVIADA"}


def test_mark_paid_only_allows_due_or_overdue(isolated_db):
    _vincular()
    mensal = repository.salvar_mensal(
        1,
        {
            "tributo_id": 1,
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "status": "A_PAGAR",
            "valor": 500,
            "data_vencimento": "2099-09-25",
        },
        "TESTE_PAGAR",
    )
    assert mensal["status"] == "A_PAGAR"
    with pytest.raises(HTTPException) as exc_info:
        marcar_pago(1, 1, 2026, 8)
    assert exc_info.value.status_code == 400

    repository.salvar_mensal(
        1,
        {
            "tributo_id": 1,
            "competencia_ano": 2026,
            "competencia_mes": 8,
            "status": "A_VENCER",
            "valor": 500,
            "data_vencimento": "2099-09-25",
        },
        "TESTE_A_VENCER",
    )
    pago = marcar_pago(1, 1, 2026, 8)
    assert pago["status"] == "PAGO"
    assert pago["data_pagamento"]


def test_relatorio_distingue_pendente_credor_sem_movimentacao_e_total(isolated_db):
    _vincular()
    repository.salvar_mensal(1, {"tributo_id": 1, "competencia_ano": 2026, "competencia_mes": 8, "status": "A_PAGAR", "valor": 100}, "GUIA")
    repository.salvar_mensal(1, {"tributo_id": 1, "competencia_ano": 2026, "competencia_mes": 9, "status": "CREDOR", "valor": 0}, "CREDOR")
    repository.salvar_mensal(1, {"tributo_id": 1, "competencia_ano": 2026, "competencia_mes": 10, "status": "SEM_MOVIMENTACAO", "valor": 0}, "SEM_MOVIMENTACAO")

    relatorio = relatorio_service.gerar_previa(1, 2026, 8, 2026, 10)
    assert relatorio["linhas"][0]["valores"][0] == 100
    assert relatorio["linhas"][1]["valores"][0] == "R$ 0,00 (Credor)"
    assert relatorio["linhas"][2]["valores"][0] == "R$ 0,00 (Sem movimentação)"
    assert relatorio["total_geral"] == 100
    assert relatorio_service.gerar_pdf(relatorio).startswith(b"%PDF")

    # Uma competência configurada sem registro é Pendente, nunca R$ 0,00.
    relatorio2 = relatorio_service.gerar_previa(1, 2026, 11, 2026, 11)
    assert relatorio2["linhas"][0]["valores"][0] == "Pendente"
