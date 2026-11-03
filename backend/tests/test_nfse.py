import base64
import gzip
import hashlib
import json
import sqlite3
import uuid

from app.db.database import conectar_banco, STORAGE_BASE
from app.modules.nfse import service
from app.services.certificado_service import certificate_service


def _insert_pf(name="MARIA NFSE TESTE", cpf=None):
    cpf = cpf or str(52998224725 + uuid.uuid4().int % 1000).zfill(11)
    with conectar_banco() as conn:
        cur = conn.execute(
            "INSERT INTO pessoas_fisicas(cpf,nome,ativo) VALUES(?,?,1)",
            (cpf, name),
        )
        conn.commit()
        return cur.lastrowid, cpf


def _insert_a3_pj():
    thumb = hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest()
    with conectar_banco() as conn:
        cur = conn.execute(
            """INSERT INTO certificados
               (empresa_id,tipo,meio_armazenamento,titular_tipo,nome_titular,documento_titular,
                emissor,numero_serie,thumbprint_sha256,algoritmo,data_emissao,data_validade,status,apto_para_uso)
               VALUES(1,'A3','CARTAO','PJ','EMPRESA TESTE LTDA','50410847000112',?,?,?,?,?,?, 'ATIVO',1)""",
            ("AC TESTE", uuid.uuid4().hex[:16], thumb, "SHA256", "2026-01-01", "2030-01-01"),
        )
        conn.commit()
        return cur.lastrowid, thumb


def test_nfse_tables_exist():
    with conectar_banco() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('nfse_sync','nfse_documentos')"
            )
        }
    assert tables == {"nfse_sync", "nfse_documentos"}


def test_adn_url_uses_official_contributor_route(monkeypatch):
    monkeypatch.setenv("OMEGA_NFSE_ADN_URL", service.ADN_PROD)
    assert service._adn_url(123) == (
        "https://adn.nfse.gov.br/contribuintes/DFe/123?tipoNSU=DISTRIBUICAO&lote=true"
    )


def test_extract_items_and_gzip_document():
    xml = '<NFSe><infNFSe><nNFSe>123</nNFSe><chaveAcesso>12345678901234567890123456789012345678901234</chaveAcesso></infNFSe></NFSe>'
    packed = base64.b64encode(gzip.compress(xml.encode())).decode()
    payload = {"ultNSU": "10", "maxNSU": "20", "lote": [{"nsu": "10", "docZip": packed, "schema": "NFSe"}]}
    items, ult, max_nsu = service._extract_items(payload)
    assert (ult, max_nsu) == (10, 20)
    doc = service._parse_candidate_document(items[0], "PJ", 1)
    assert doc["nsu"] == 10
    assert doc["numero"] == "123"
    assert doc["chave_acesso"] == "12345678901234567890123456789012345678901234"
    assert doc["xml"].startswith("<NFSe>")


def test_import_a3_response_requires_matching_active_certificate():
    cert_id, thumb = _insert_a3_pj()
    xml = '<NFSe><infNFSe><nNFSe>900</nNFSe></infNFSe></NFSe>'
    payload = {
        "ultNSU": 3,
        "maxNSU": 3,
        "lote": [{"nsu": 3, "docZip": base64.b64encode(gzip.compress(xml.encode())).decode(), "schema": "NFSe"}],
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    result = service.importar_resposta_a3("PJ", 1, thumb, "application/json", encoded)
    assert result["ok"] is True
    assert result["certificado_tipo"] == "A3"
    assert result["documentos_importados"] == 1

    with conectar_banco() as conn:
        row = conn.execute(
            "SELECT origem,entidade_id,provider,nsu,numero,xml_path FROM nfse_documentos WHERE origem='PJ' AND entidade_id=1 AND provider=? AND nsu=3",
            (service.PROVIDER_NAME,),
        ).fetchone()
    assert row is not None
    assert row[4] == "900"
    assert row[5]
    assert (STORAGE_BASE.parent / row[5]).is_file()

    try:
        service.importar_resposta_a3("PJ", 1, "0" * 64, "application/json", encoded)
    except ValueError as exc:
        assert "não corresponde" in str(exc)
    else:
        raise AssertionError("A3 com thumbprint diferente foi aceito")


def test_pf_context_uses_pf_certificate():
    pessoa_id, cpf = _insert_pf()
    thumb = hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest()
    with conectar_banco() as conn:
        conn.execute(
            """INSERT INTO certificados_pf
               (pessoa_id,tipo,meio_armazenamento,nome_titular,documento_titular,emissor,numero_serie,
                thumbprint_sha256,algoritmo,data_emissao,data_validade,status,apto_para_uso)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pessoa_id, "A3", "CARTAO", "MARIA NFSE TESTE", cpf, "AC TESTE", uuid.uuid4().hex[:12], thumb,
             "SHA256", "2026-01-01", "2030-01-01", "ATIVO", 1),
        )
        conn.commit()
    ctx = service.contexto("PF", pessoa_id)
    assert ctx["origem"] == "PF"
    assert ctx["certificado"]["tipo"] == "A3"
    assert ctx["certificado"]["documento"] == cpf


def test_certificate_service_a1_context_manager_rejects_non_a1():
    cert_id, _ = _insert_a3_pj()
    try:
        with certificate_service.a1_mtls_files(cert_id, "PJ"):
            pass
    except LookupError as exc:
        assert "A1" in str(exc)
    else:
        raise AssertionError("Um certificado A3 foi aceito como A1")


def test_parser_extracts_date_and_service_value_from_namespaced_adn_xml():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
      <infNFSe Id="NFS12345678901234567890123456789012345678901234">
        <nNFSe>123456</nNFSe>
        <dhProc>2026-10-09T10:45:00-03:00</dhProc>
        <DPS>
          <infDPS>
            <dhEmi>2026-10-08T09:00:00-03:00</dhEmi>
            <valores><vServPrest><vServ>1234.56</vServ></vServPrest></valores>
          </infDPS>
        </DPS>
      </infNFSe>
    </NFSe>'''
    packed = base64.b64encode(gzip.compress(xml.encode("utf-8"))).decode("ascii")
    doc = service._parse_candidate_document({"nsu": "77", "docZip": packed, "schema": "NFSe"}, "PJ", 1)

    assert doc["numero"] == "123456"
    assert doc["data_emissao"] == "2026-10-09T10:45:00-03:00"
    assert doc["valor"] == 1234.56
    assert doc["xml"].lstrip().startswith("<?xml")


def test_parser_falls_back_to_dhemi_and_brazilian_money_separator():
    xml = '''<NFSe>
      <infNFSe><nNFSe>654</nNFSe>
        <DPS><infDPS><dhEmi>20261008</dhEmi>
          <valores><vServPrest><vServ>1.234,56</vServ></vServPrest></valores>
        </infDPS></DPS>
      </infNFSe>
    </NFSe>'''
    doc = service._parse_candidate_document({"docZip": xml}, "PF", 9)
    assert doc["numero"] == "654"
    assert doc["data_emissao"] == "2026-10-08"
    assert doc["valor"] == 1234.56


def test_parser_accepts_text_values_from_adn_json_metadata():
    doc = service._parse_candidate_document(
        {"dataEmissao": "08/10/2026", "valor": "150.75", "numeroNfse": "987"},
        "PJ",
        1,
    )
    assert doc["data_emissao"] == "2026-10-08"
    assert doc["valor"] == 150.75
    assert doc["numero"] == "987"


def test_parser_handles_us_and_brazilian_money_formats():
    assert service._parse_xml_money("1.234,56") == 1234.56
    assert service._parse_xml_money("1,234.56") == 1234.56
    assert service._parse_xml_money("150.75") == 150.75
    assert service._parse_xml_money("150,75") == 150.75
    assert service._parse_xml_money("não é valor") is None


def test_extract_items_accepts_documento_payload_alias():
    items, _, _ = service._extract_items({"lote": [{"documento": "<NFSe />"}]})
    assert len(items) == 1
    assert service._parse_candidate_document(items[0], "PJ", 1)["xml"] == "<NFSe />"


def test_parser_extracted_date_and_value_are_persisted():
    xml = '''<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
      <infNFSe>
        <nNFSe>321654</nNFSe>
        <dhProc>2026-10-13T07:30:00-03:00</dhProc>
        <DPS><infDPS><valores><vServPrest><vServ>987.65</vServ></vServPrest></valores></infDPS></DPS>
      </infNFSe>
    </NFSe>'''
    unique_nsu = 700000 + (uuid.uuid4().int % 2000000000)
    parsed = service._parse_candidate_document({"nsu": unique_nsu, "docZip": xml}, "PJ", 1)

    inserted = service._save_documents("PJ", 1, [parsed], "{}")
    assert inserted == 1

    with conectar_banco() as conn:
        row = conn.execute(
            "SELECT data_emissao, valor, numero FROM nfse_documentos WHERE origem='PJ' AND entidade_id=1 AND provider=? AND nsu=?",
            (service.PROVIDER_NAME, unique_nsu),
        ).fetchone()
    assert row is not None
    assert row[0] == "2026-10-13T07:30:00-03:00"
    assert row[1] == 987.65
    assert row[2] == "321654"


def test_parser_rejects_invalid_encoded_xml_without_raising():
    assert service._decode_xml_candidate("!!!this-is-not-base64!!!") is None
    assert service._decode_xml_candidate(base64.b64encode(b"\x1f\x8bnot-gzip").decode("ascii")) is None
    doc = service._parse_candidate_document({"docZip": "!!!this-is-not-base64!!!"}, "PJ", 1)
    assert doc["xml"] is None
    assert doc["data_emissao"] is None
    assert doc["valor"] is None


def test_context_keeps_existing_documents_available_without_certificate():
    unique_cnpj = f"9{uuid.uuid4().int % 10**13:013d}"
    with conectar_banco() as conn:
        cur = conn.execute(
            "INSERT INTO empresas(cnpj,razao_social,ativo) VALUES(?,?,1)",
            (unique_cnpj, "EMPRESA SEM CERTIFICADO NFSE"),
        )
        empresa_id = int(cur.lastrowid)
        conn.commit()
    context = service.contexto("PJ", empresa_id)
    assert context["certificado"] is None
    assert context["mensagem_certificado"]
    assert context["entidade_id"] == empresa_id
    assert "ultimo_nsu" in context


def test_nfse_cursor_never_moves_backwards_or_loses_max_nsu():
    entity_id = 700000000 + (uuid.uuid4().int % 100000000)
    service._cursor("PJ", entity_id)
    service._update_cursor("PJ", entity_id, 90, 120, "DOCUMENTOS_IMPORTADOS")
    service._update_cursor("PJ", entity_id, 40, 75, "SEM_DOCUMENTOS")
    cursor = service._cursor("PJ", entity_id)
    assert cursor["ultimo_nsu"] == 90
    assert cursor["max_nsu"] == 120


def test_date_only_a3_expiry_is_valid_through_end_of_day():
    expiry = service._certificate_validity({"data_validade": "2099-12-31"})
    assert expiry is not None
    assert expiry.hour == 23 and expiry.minute == 59 and expiry.second == 59


def test_parser_ignores_invalid_json_key_and_recovers_key_from_xml():
    xml_key = "12345678901234567890123456789012345678901234"
    xml = f"<NFSe><infNFSe><nNFSe>4412</nNFSe><chaveAcesso>{xml_key}</chaveAcesso></infNFSe></NFSe>"
    parsed = service._parse_candidate_document({"chaveAcesso": "invalid", "nsu": "not-a-number", "docZip": xml}, "PJ", 1)
    assert parsed["chave_acesso"] == xml_key
    assert parsed["nsu"] is None
    assert parsed["numero"] == "4412"


def test_stale_nfse_sync_lock_can_be_recovered():
    entity_id = 600000000 + (uuid.uuid4().int % 100000000)
    cursor = service._cursor("PJ", entity_id)
    with conectar_banco() as conn:
        conn.execute(
            "UPDATE nfse_sync SET status='CONSULTANDO', atualizado_em='2020-01-01 00:00:00' WHERE origem='PJ' AND entidade_id=? AND provider=?",
            (entity_id, service.PROVIDER_NAME),
        )
        conn.commit()
    stale = service._cursor("PJ", entity_id)
    service._begin_sync("PJ", entity_id, stale)
    assert service._cursor("PJ", entity_id)["status"] == "CONSULTANDO"


def test_active_nfse_sync_lock_cannot_be_taken_over():
    entity_id = 500000000 + (uuid.uuid4().int % 100000000)
    service._cursor("PJ", entity_id)
    with conectar_banco() as conn:
        conn.execute(
            "UPDATE nfse_sync SET status='CONSULTANDO', atualizado_em=CURRENT_TIMESTAMP WHERE origem='PJ' AND entidade_id=? AND provider=?",
            (entity_id, service.PROVIDER_NAME),
        )
        conn.commit()
    current = service._cursor("PJ", entity_id)
    try:
        service._begin_sync("PJ", entity_id, current)
    except ValueError as exc:
        assert "em andamento" in str(exc)
    else:
        raise AssertionError("Uma consulta em andamento foi assumida por outra requisição")


def test_extract_items_accepts_official_adn_casing_and_arquivo_xml_alias():
    xml = '''<NFSe xmlns=\"http://www.sped.fazenda.gov.br/nfse\"><infNFSe><nNFSe>456</nNFSe><dhProc>2026-10-13T11:00:00-03:00</dhProc><vServ>321.90</vServ></infNFSe></NFSe>'''
    payload = {
        "ultNSU": "82",
        "maxNSU": "90",
        "LoteDFe": [{"NSU": "82", "Schema": "NFSe_v1.00.xsd", "ArquivoXml": base64.b64encode(gzip.compress(xml.encode())).decode()}],
    }
    items, ultimo, maximo = service._extract_items(payload)
    assert (ultimo, maximo) == (82, 90)
    assert len(items) == 1
    document = service._parse_candidate_document(items[0], "PJ", 1)
    assert document["nsu"] == 82
    assert document["schema"] == "NFSe_v1.00.xsd"
    assert document["numero"] == "456"
    assert document["data_emissao"] == "2026-10-13T11:00:00-03:00"
    assert document["valor"] == 321.90


def test_unrecognized_nonempty_adn_batch_is_not_mistaken_for_empty_response():
    payload = {"ultNSU": "88", "maxNSU": "99", "LoteDFe": [{"NSU": "89", "ConteudoFiscalV2": "payload"}]}
    items, ultimo, maximo = service._extract_items(payload)
    assert items == []
    assert (ultimo, maximo) == (88, 99)
    assert service._has_unparsed_document_batch(payload) is True
    assert service._has_unparsed_document_batch({"ultNSU": "88", "maxNSU": "99", "LoteDFe": []}) is False


def test_nfse_context_loads_existing_omega_a1_without_legacy_thumbprint():
    """Legacy A1 registrations without a stored thumbprint remain selectable.

    The PFX is still validated when opening the mTLS context; A3 continues to
    require a thumbprint to bind the selected card/token in the Bridge.
    """
    unique_cnpj = f"8{uuid.uuid4().int % 10**13:013d}"
    with conectar_banco() as conn:
        cur = conn.execute(
            "INSERT INTO empresas(cnpj,razao_social,ativo) VALUES(?,?,1)",
            (unique_cnpj, "EMPRESA A1 LEGADO NFSE"),
        )
        empresa_id = int(cur.lastrowid)
        conn.execute(
            """INSERT INTO certificados
               (empresa_id,tipo,meio_armazenamento,titular_tipo,nome_titular,documento_titular,
                data_emissao,data_validade,status,apto_para_uso,thumbprint_sha256)
               VALUES(?, 'A1', 'PFX', 'PJ', 'EMPRESA A1 LEGADO NFSE', ?,
                      '2026-01-01', '2035-12-31T23:59:59+00:00', 'ATIVO', 1, NULL)""",
            (empresa_id, unique_cnpj),
        )
        conn.commit()

    context = service.contexto("PJ", empresa_id)
    assert context["certificado"] is not None
    assert context["certificado"]["tipo"] == "A1"
    assert context["certificado"]["thumbprint_sha256"] is None


def test_active_a1_certificate_is_not_rejected_when_public_repository_hides_storage_ref(monkeypatch):
    # CertificateService intentionally exposes public metadata without storage_ref.
    # NFS-e must select the certificate and defer PFX availability validation to
    # certificate_service.a1_mtls_files(), otherwise every A1 can disappear.
    cert = {
        "id": 98765,
        "tipo": "A1",
        "status": "ATIVO",
        "apto_para_uso": True,
        "meio_armazenamento": "PFX",
        "data_validade": "2099-12-31T23:59:59+00:00",
        "thumbprint_sha256": "",
    }
    monkeypatch.setattr(service.certificate_service, "get_for_company", lambda _entity_id: [cert])
    selected = service._active_certificate("PJ", 1)
    assert selected["id"] == 98765
    assert selected["tipo"] == "A1"


def test_active_certificate_accepts_legacy_brazilian_date_format(monkeypatch):
    cert = {
        "id": 98766,
        "tipo": "A1",
        "status": "ATIVO",
        "apto_para_uso": 1,
        "meio_armazenamento": "PFX",
        "data_validade": "31/12/2099",
        "thumbprint_sha256": None,
    }
    monkeypatch.setattr(service.certificate_service, "get_for_company", lambda _entity_id: [cert])
    selected = service._active_certificate("PJ", 1)
    assert selected["id"] == 98766


def test_context_reports_existing_but_unusable_certificate_reason(monkeypatch):
    cert = {
        "id": 98767,
        "tipo": "A3",
        "status": "ATIVO",
        "apto_para_uso": True,
        "data_validade": "31/12/2099",
        "thumbprint_sha256": "bad-thumbprint",
        "nome_titular": "EMPRESA TESTE",
        "documento_titular": "50410847000112",
    }
    monkeypatch.setattr(service.certificate_service, "get_for_company", lambda _entity_id: [cert])
    monkeypatch.setattr(service, "_entity", lambda _origin, _entity_id: {
        "id": 1, "documento": "50410847000112", "nome": "EMPRESA TESTE",
        "municipio": None, "codigo_ibge": None, "uf": None,
    })
    monkeypatch.setattr(service, "_cursor", lambda _origin, _entity_id: {
        "ultimo_nsu": 0, "max_nsu": None, "ultimo_sync": None, "status": "PRONTO",
    })
    result = service.contexto("PJ", 1)
    assert result["certificado"] is None
    assert result["certificados_cadastrados"][0]["id"] == 98767
    assert "thumbprint" in result["certificados_cadastrados"][0]["motivo"].lower()
    assert "#98767" in result["mensagem_certificado"]


def test_nfse_office_panel_and_config_are_available_without_mutating_existing_docs():
    panel = service.painel("2026-10")
    assert panel["competencia"] == "2026-10"
    assert "resumo" in panel and "empresas" in panel
    assert any(row["origem"] == "PJ" and row["entidade_id"] == 1 for row in panel["empresas"])

    saved = service.salvar_config("PJ", 1, True, 24, "02:00", 1)
    assert saved["sincronizacao_automatica"] is True
    assert saved["frequencia_horas"] == 24
    disabled = service.salvar_config("PJ", 1, False, 24, "02:00", 1)
    assert disabled["sincronizacao_automatica"] is False
    assert disabled["proxima_execucao_em"] is None


def test_nfse_manual_xml_event_history_and_accounting_draft():
    key = str(uuid.uuid4().int % (10**44)).zfill(44)
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
    <NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
      <infNFSe Id="NFS{key}"><chaveAcesso>{key}</chaveAcesso><nNFSe>900777</nNFSe>
        <dhProc>2026-10-05T10:30:00-03:00</dhProc>
        <prest><CNPJ>50410847000112</CNPJ><xNome>EMPRESA TESTE LTDA</xNome></prest>
        <toma><CNPJ>11222333000181</CNPJ><xNome>CLIENTE TESTE</xNome></toma>
        <valores><vServPrest><vServ>1234.56</vServ></vServPrest><vRetIRRF>12.34</vRetIRRF></valores>
      </infNFSe>
    </NFSe>'''.encode("utf-8")
    result = service.importar_xml_manual("PJ", 1, "nfse-manual.xml", xml, 1)
    assert result["ok"] is True
    detail = service.detalhe(result["id"])
    assert detail["provider"] == "UPLOAD_XML"
    assert detail["numero"] == "900777"
    assert detail["valor"] == 1234.56
    assert detail["direcao"] == "PRESTADA"
    assert detail["irrf"] == 12.34

    service.registrar_evento(result["id"], "CANCELADA", "Cancelamento conferido", 1)
    assert service.detalhe(result["id"])["situacao"] == "CANCELADA"
    assert any(row["tipo_evento"] == "CANCELADA" for row in service.listar_eventos(result["id"]))

    draft = service.salvar_lancamento(result["id"], "2026-10-05", "Clientes", "Receita de serviços",
                                      "NFS-e 900777", 1234.56, "Rascunho de teste", 1)
    assert draft["lancamento"]["status"] == "RASCUNHO"
    assert draft["lancamento"]["conta_debito"] == "Clientes"

    xlsx = service.exportar_excel("2026-10", "PJ", 1)
    assert xlsx[:2] == b"PK"
    zipped = service.zip_xmls([result["id"]])
    assert zipped[:2] == b"PK"


def _insert_nfse_doc(chave=None, provider="ADN_NFSE"):
    chave = chave or ("9" * 44)
    with conectar_banco() as conn:
        cur = conn.execute(
            "INSERT INTO nfse_documentos(origem,entidade_id,provider,nsu,chave_acesso,numero,situacao) VALUES('PJ',1,?,NULL,?,'TESTE','IMPORTADA')",
            (provider, chave),
        )
        conn.commit()
        return cur.lastrowid


def test_import_email_eml_xml_attachment_keeps_email_source():
    from email.message import EmailMessage

    chave = "12345678901234567890123456789012345678901234"
    xml = f'<NFSe><infNFSe><chaveAcesso>{chave}</chaveAcesso><nNFSe>90001</nNFSe></infNFSe></NFSe>'
    message = EmailMessage()
    message["Subject"] = "NFS-e teste"
    message["From"] = "cliente@example.invalid"
    message["To"] = "contabilidade@example.invalid"
    message.set_content("Segue a nota fiscal em anexo.")
    message.add_attachment(xml.encode(), maintype="application", subtype="xml", filename="nota-teste.xml")

    result = service.importar_email_eml("PJ", 1, "mensagem.eml", message.as_bytes())
    assert result["ok"] is True
    assert result["importados"] == 1
    doc = service.detalhe(result["resultados"][0]["id"])
    assert doc["xml"].startswith("<NFSe>")
    assert doc["origem_documento"] == "E-mail (XML anexado)"


def test_import_email_eml_requires_xml_attachment():
    from email.message import EmailMessage

    message = EmailMessage()
    message["Subject"] = "Sem nota"
    message.set_content("Este e-mail não contém XML.")
    try:
        service.importar_email_eml("PJ", 1, "mensagem.eml", message.as_bytes())
    except ValueError as exc:
        assert "Não encontrei anexos XML" in str(exc)
    else:
        raise AssertionError("E-mail sem XML deveria ser rejeitado.")


def test_official_event_response_is_imported_and_deduplicated(monkeypatch):
    import json

    nfse_id = _insert_nfse_doc("98765432109876543210987654321098765432109876")
    event_xml = ('<procEventoNfse><evento><infEvento><tpEvento>101101</tpEvento>'
                 '<xMotivo>Cancelamento registrado</xMotivo>'
                 '<dhEvento>2026-10-01T10:00:00-03:00</dhEvento>'
                 '</infEvento></evento></procEventoNfse>')
    packed = base64.b64encode(gzip.compress(event_xml.encode())).decode()
    payload = {"lote": [{"docZip": packed, "schema": "procEventoNfse_v1.00.xsd"}]}
    monkeypatch.setattr(service, "_active_certificate", lambda origin, entity_id: {"tipo": "A1"})
    monkeypatch.setattr(service, "_request_a1_url", lambda origin, cert, url: (200, "application/json", json.dumps(payload)))

    first = service.consultar_eventos_adn(nfse_id)
    second = service.consultar_eventos_adn(nfse_id)
    assert first["eventos_encontrados"] == 1
    assert first["eventos_importados"] == 1
    assert second["eventos_importados"] == 0
    events = service.listar_eventos(nfse_id)
    assert len([item for item in events if item["origem"] == "ADN_NFSE"]) == 1
    assert "Cancelamento registrado" in events[0]["descricao"]


def test_a3_event_response_requires_matching_certificate_and_imports(monkeypatch):
    nfse_id = _insert_nfse_doc("11112222333344445555666677778888999900001111")
    _, thumb = _insert_a3_pj()
    monkeypatch.setattr(service, "_active_certificate", lambda origin, entity_id: {"tipo": "A3", "thumbprint_sha256": thumb})
    event_xml = ('<procEventoNfse><evento><infEvento><tpEvento>101101</tpEvento>'
                 '<xMotivo>Evento A3 teste</xMotivo></infEvento></evento></procEventoNfse>')
    payload = {"lote": [{"xmlEvento": event_xml, "schema": "evento.xsd"}]}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    result = service.importar_eventos_a3(nfse_id, thumb, "application/json", encoded)
    assert result["eventos_importados"] == 1
    events = service.listar_eventos(nfse_id)
    assert any(item["origem"] == "ADN_NFSE_A3_BRIDGE" for item in events)


def test_nfse_scheduler_runs_only_explicitly_enabled_due_a1(monkeypatch):
    from datetime import datetime, timedelta, timezone

    service.salvar_config("PJ", 1, True, 24, "02:00", 1)
    due = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    with conectar_banco() as conn:
        conn.execute(
            "UPDATE nfse_config SET proxima_execucao_em=? WHERE origem='PJ' AND entidade_id=1",
            (due,),
        )
        conn.commit()

    calls = []
    monkeypatch.setattr(service, "consultar_a1", lambda origin, entity_id: (
        calls.append((origin, entity_id)) or {
            "documentos_encontrados": 2, "documentos_importados": 1,
        }
    ))
    result = service.processar_rotinas_automaticas(datetime.now(timezone.utc))
    assert result["processadas"] == 1
    assert result["sucesso"] == 1
    assert calls == [("PJ", 1)]

    # A claim avança a próxima execução; o mesmo ciclo não pode disparar de novo.
    again = service.processar_rotinas_automaticas(datetime.now(timezone.utc))
    assert again["processadas"] == 0
    assert len(calls) == 1


def test_nfse_scheduler_ignores_disabled_or_not_due_configs(monkeypatch):
    from datetime import datetime, timedelta, timezone

    service.salvar_config("PJ", 1, False, 24, "02:00", 1)
    with conectar_banco() as conn:
        conn.execute(
            "UPDATE nfse_config SET proxima_execucao_em=? WHERE origem='PJ' AND entidade_id=1",
            ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),),
        )
        conn.commit()
    calls = []
    monkeypatch.setattr(service, "consultar_a1", lambda *args: calls.append(args))
    result = service.processar_rotinas_automaticas(datetime.now(timezone.utc))
    assert result["processadas"] == 0
    assert calls == []
