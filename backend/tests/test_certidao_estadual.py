from app.services.sefaz_pe_service import analisar_certidao, formatar_cnpj, validar_cnpj


def test_cnpj_estadual():
    assert validar_cnpj("50.410.847/0001-12")
    assert formatar_cnpj("50410847000112") == "50.410.847/0001-12"


def test_classificacao_conservadora():
    assert analisar_certidao("CERTIDAO NEGATIVA DE DEBITOS", "x.pdf")["situacao"] == "REGULAR"
    assert analisar_certidao("CERTIDAO POSITIVA COM EFEITOS DE NEGATIVA", "x.pdf")["situacao"] == "POSITIVA COM EFEITOS DE NEGATIVA"
    assert analisar_certidao("CERTIDAO POSITIVA DE DEBITOS", "x.pdf")["situacao"] == "IRREGULAR"
    assert analisar_certidao("CERTIDAO DE REGULARIDADE FISCAL", "x.pdf")["situacao"] == "NAO IDENTIFICADO"


def test_nome_arquivo_fallback():
    assert analisar_certidao("CERTIDAO DE REGULARIDADE FISCAL", "RelatorioCertidaoRegularidadeFiscalInscritoRegular.pdf")["situacao"] == "REGULAR"
    assert analisar_certidao("CERTIDAO DE REGULARIDADE FISCAL", "RelatorioCertidaoRegularidadeFiscalInscritoIrregular.pdf")["situacao"] == "IRREGULAR"


def test_leitura_conservadora_narrativa():
    from app.services.sefaz_narrativa_pyautogui import _classificar_documento, _extrair_data

    texto_negativa = "CERTIDÃO NEGATIVA DE DÉBITO FISCAL. Emissão: 14/09/2026. Validade: 13/12/2026."
    assert _classificar_documento(texto_negativa) == "REGULAR"
    assert _extrair_data(texto_negativa, ("emissão", "emissao")) == "2026-09-14"
    assert _extrair_data(texto_negativa, ("validade",)) == "2026-12-13"

    texto_positiva = "CERTIDÃO POSITIVA DE DÉBITOS FISCAIS."
    assert _classificar_documento(texto_positiva) == "IRREGULAR"

    texto_ambiguous = "Documento emitido pela SEFAZ-PE."
    assert _classificar_documento(texto_ambiguous) == "AGUARDANDO_INTERVENCAO"


def test_persistencia_narrativa_mock(monkeypatch):
    from app.services import certidoes_service
    from app.db.database import conectar_banco

    def fake_automation(cnpj, certificado_nome=None):
        return {
            "cnpj": cnpj,
            "tipo_certidao": "Narrativa de Débito Fiscal - SEFAZ",
            "situacao": "REGULAR",
            "status_processamento": "Sucesso",
            "mensagem": "Documento lido no navegador.",
            "texto_extraido": "CERTIDÃO NEGATIVA DE DÉBITO FISCAL. Emissão: 14/09/2026.",
            "data_emissao": "2026-09-14",
            "data_validade": "2026-12-13",
            "pendencia": False,
            "arquivo_pdf": None,
            "nome_original_arquivo": "CertidaoNarrativaDebitoFiscal.txt",
        }

    monkeypatch.setattr("app.services.sefaz_narrativa_pyautogui.executar_automacao_pyautogui", fake_automation)
    resultado = certidoes_service.consultar_narrativa_pyautogui(1)
    assert resultado["situacao"] == "REGULAR"
    assert "CERTIDÃO NEGATIVA" in (resultado.get("texto_extraido") or "")

    c = conectar_banco()
    try:
        row = c.execute(
            "SELECT texto_extraido FROM consultas_certidoes WHERE id=?",
            (resultado["consulta_id"],),
        ).fetchone()
        assert row and "CERTIDÃO NEGATIVA" in row["texto_extraido"]
        row2 = c.execute(
            "SELECT texto_extraido FROM certidoes_historico WHERE consulta_id=?",
            (resultado["consulta_id"],),
        ).fetchone()
        assert row2 and "CERTIDÃO NEGATIVA" in row2["texto_extraido"]
    finally:
        c.close()
