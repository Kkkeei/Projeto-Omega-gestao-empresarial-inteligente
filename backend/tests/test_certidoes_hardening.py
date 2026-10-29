from pathlib import Path
from io import BytesIO

from reportlab.pdfgen import canvas

import pytest
from pypdf import PdfWriter

from app.services import receita_federal_service as federal
from app.services import sefaz_pe_service as sefaz
from app.services import certidoes_service as certidoes


@pytest.mark.parametrize(
    ("texto", "situacao", "pendencia"),
    [
        ("Consulta de Regularidade Fiscal", "NAO DISPONIVEL", False),
        ("CERTIDÃO NEGATIVA DE DÉBITOS TRIBUTÁRIOS", "REGULAR", False),
        ("CERTIDÃO POSITIVA COM EFEITOS DE NEGATIVA", "POSITIVA COM EFEITOS DE NEGATIVA", True),
        ("CERTIDÃO POSITIVA DE DÉBITOS", "IRREGULAR", True),
        ("SITUAÇÃO FISCAL IRREGULAR", "IRREGULAR", True),
        ("", "NAO DISPONIVEL", False),
    ],
)
def test_classificar_federal_exige_evidencia_explicita(texto, situacao, pendencia):
    atual, tem_pendencia, _ = federal._classificar(texto)
    assert atual == situacao
    assert tem_pendencia is pendencia


def test_classificar_federal_normaliza_acentos():
    atual, pendencia, _ = federal._classificar("CERTIDÃO NEGATIVA DE DÉBITOS")
    assert atual == "REGULAR"
    assert pendencia is False


@pytest.mark.parametrize(
    ("texto", "label", "esperado"),
    [
        ("Data de emissão: 29/10/2026", r"data\s+de\s+emiss[aã]o", "2026-10-29"),
        ("Validade: 2026-11-28", r"validade", "2026-11-28"),
        ("Validade: 31/02/2026", r"validade", None),
        ("sem data", r"validade", None),
    ],
)
def test_parse_date_valida_datas_reais(texto, label, esperado):
    assert federal._parse_date(texto, label) == esperado


def test_sefaz_classifier_distinguishes_certificate_outcomes():
    regular = sefaz.analisar_certidao("CERTIDÃO NEGATIVA DE DÉBITOS")
    positiva = sefaz.analisar_certidao("CERTIDÃO POSITIVA COM EFEITOS DE NEGATIVA")
    irregular = sefaz.analisar_certidao("CERTIDÃO POSITIVA DE DÉBITOS")
    filename_only = sefaz.analisar_certidao("Documento sem resultado legível", "INSCRITOREGULAR.pdf")

    assert regular["situacao"] == "REGULAR"
    assert positiva["situacao"] == "POSITIVA COM EFEITOS DE NEGATIVA"
    assert irregular["situacao"] == "IRREGULAR"
    assert irregular["pendencia"] is True
    assert filename_only["situacao"] == "NAO IDENTIFICADO"


def _create_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as target:
        writer.write(target)
    return path


def test_pdf_validator_rejects_html_disguised_as_pdf(tmp_path):
    from app.services.receita_federal_service import _pdf_valido

    html = tmp_path / "certidao.pdf"
    html.write_text("<html><body>Erro de sessão</body></html>", encoding="utf-8")
    assert _pdf_valido(html) is False


def test_pdf_validator_accepts_structurally_valid_pdf(tmp_path):
    from app.services.receita_federal_service import _pdf_valido

    pdf = _create_pdf(tmp_path / "certidao.pdf")
    assert _pdf_valido(pdf) is True


def test_certificate_pdf_path_allows_only_certificate_storage(tmp_path, monkeypatch):
    project = tmp_path / "project"
    legacy = project / "storage" / "certidoes"
    configured = tmp_path / "external-storage" / "certidoes"
    safe_pdf = _create_pdf(legacy / "estadual" / "certidao.pdf")
    external_pdf = _create_pdf(configured / "federal" / "certidao.pdf")
    outside_pdf = _create_pdf(project / "docs" / "privado.pdf")

    monkeypatch.setattr(certidoes, "PROJECT_ROOT", project.resolve())
    monkeypatch.setattr(certidoes, "LEGACY_CERTIDOES_ROOT", legacy.resolve())
    monkeypatch.setattr(certidoes, "STORAGE_BASE", configured.parent.resolve())

    assert certidoes.obter_pdf_path("storage/certidoes/estadual/certidao.pdf") == safe_pdf.resolve()
    assert certidoes.obter_pdf_path(str(external_pdf)) == external_pdf.resolve()
    with pytest.raises(ValueError, match="armazenamento de certidões"):
        certidoes.obter_pdf_path(str(outside_pdf))
    with pytest.raises(ValueError):
        certidoes.obter_pdf_path("../../docs/privado.pdf")


def test_relative_database_paths_are_resolved_against_backend(tmp_path):
    from app.db.database import _resolve_configured_path

    expected = (tmp_path / "omega.db").resolve()
    assert _resolve_configured_path("./omega.db", base_dir=tmp_path) == expected



def test_certificate_api_sanitizer_hides_paths_text_and_technical_exceptions(tmp_path, monkeypatch):
    from app.api.v1.certidoes import routes

    pdf = tmp_path / "certificate.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    monkeypatch.setattr(routes, "obter_pdf_path", lambda _path: pdf)
    payload = {
        "situacao": "ERRO",
        "status_processamento": "Erro técnico",
        "mensagem": "ValueError: /srv/omega/storage/certidoes/empresa/certidao.pdf",
        "pdf_path": "/srv/omega/storage/certidoes/empresa/certidao.pdf",
        "arquivo_pdf": "/tmp/certidao_federal_tmp_123.pdf",
        "texto_extraido": "CNPJ 00.000.000/0001-00 dados fiscais internos",
        "erro_tecnico": "traceback com caminho local",
        "situacao_detectada": "REGULAR",
        "consulta_id": 42,
    }
    safe = routes._sanitizar_resultado_certidao(payload)

    assert safe["pdf_disponivel"] is True
    assert safe["consulta_id"] == 42
    for key in ("pdf_path", "arquivo_pdf", "texto_extraido", "erro_tecnico", "situacao_detectada"):
        assert key not in safe
    assert "/srv/" not in safe["mensagem"]
    assert "traceback" not in safe["mensagem"]


def test_certificate_batch_sanitizer_sanitizes_nested_results(tmp_path, monkeypatch):
    from app.api.v1.certidoes import routes

    monkeypatch.setattr(routes, "obter_pdf_path", lambda _path: tmp_path / "missing.pdf")
    safe = routes._sanitizar_resultado_certidao({
        "resumo": {"total": 1, "erro": 1},
        "resultados": [{
            "situacao": "ERRO",
            "status_processamento": "Erro técnico",
            "mensagem": "RuntimeError: secret local path",
            "pdf_path": "/private/storage/certidoes/cnd.pdf",
            "consulta_id": 7,
            "erro_tecnico": "secret local path",
        }],
    })
    item = safe["resultados"][0]
    assert item["consulta_id"] == 7
    assert item["pdf_disponivel"] is False
    assert "pdf_path" not in item
    assert "erro_tecnico" not in item
    assert "secret local path" not in item["mensagem"]


def _create_text_pdf(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = BytesIO()
    pdf = canvas.Canvas(output)
    y = 780
    for line in text.splitlines():
        pdf.drawString(40, y, line)
        y -= 18
    pdf.save()
    path.write_bytes(output.getvalue())
    return path


def test_federal_pdf_must_identify_requested_cnpj(tmp_path):
    from app.services.receita_federal_service import _extrair_texto_pdf, _texto_contem_cnpj

    pdf = _create_text_pdf(
        tmp_path / "certidao-federal.pdf",
        "CERTIDAO NEGATIVA DE DEBITOS\nCNPJ: 50.410.847/0001-12",
    )
    text = _extrair_texto_pdf(pdf)
    assert _texto_contem_cnpj(text, "50410847000112") is True
    assert _texto_contem_cnpj(text, "11222333000181") is False


def test_federal_pdf_classification_uses_pdf_content(tmp_path):
    from app.services.receita_federal_service import _classificar, _extrair_texto_pdf

    pdf = _create_text_pdf(
        tmp_path / "certidao-federal.pdf",
        "CERTIDAO NEGATIVA DE DEBITOS\nCNPJ: 50.410.847/0001-12\nData de validade: 30/11/2026",
    )
    pdf_text = _extrair_texto_pdf(pdf)
    situacao, pendencia, _ = _classificar(pdf_text)
    assert situacao == "REGULAR"
    assert pendencia is False


def test_sefaz_pdf_must_match_requested_cnpj():
    assert sefaz.texto_contem_cnpj(
        "CERTIDAO NEGATIVA DE DEBITOS\nCNPJ: 50.410.847/0001-12",
        "50410847000112",
    ) is True
    assert sefaz.texto_contem_cnpj(
        "CERTIDAO NEGATIVA DE DEBITOS\nCNPJ: 12.345.678/0001-90",
        "50410847000112",
    ) is False
