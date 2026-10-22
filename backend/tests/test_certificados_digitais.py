
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.modules.certificados import service
from app.db.database import conectar_banco


@pytest.fixture(autouse=True)
def _clean_certificate_data():
    with conectar_banco() as conn:
        conn.execute('DELETE FROM certificado_eventos')
        conn.execute('DELETE FROM certificado_uso')
        conn.execute('DELETE FROM certificado_pf_eventos')
        conn.execute('DELETE FROM certificado_pf_uso')
        conn.execute('DELETE FROM certificados_pf')
        conn.execute('DELETE FROM pessoas_fisicas')
        conn.execute('DELETE FROM certificado_eventos')
        conn.execute('DELETE FROM certificado_uso')
        conn.execute('DELETE FROM certificados')
        conn.commit()
    yield


def _pfx(cnpj="50.410.847/0001-12", password="Senha@123", document_in_ou=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject_attrs = [
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EMPRESA TESTE LTDA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "EMPRESA TESTE LTDA"),
    ]
    if document_in_ou:
        subject_attrs.extend([
            x509.NameAttribute(NameOID.SERIAL_NUMBER, "SEM-DOCUMENTO"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, cnpj),
        ])
    else:
        subject_attrs.append(x509.NameAttribute(NameOID.SERIAL_NUMBER, f"CNPJ:{cnpj}"))
    subject = issuer = x509.Name(subject_attrs)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"omega", key, cert, None,
        serialization.BestAvailableEncryption(password.encode())
    ), password


def test_a1_parse_validate_store_and_replace():
    data, password = _pfx()
    first = service.cadastrar_a1(1, "certificado.pfx", data, password, 1)
    assert first["tipo"] == "A1"
    assert first["apto_para_uso"] is True
    raw, name = service.baixar_a1(first["id"], 1)
    assert raw == data
    assert name == "certificado.pfx"

    second = service.cadastrar_a1(1, "novo.p12", data, password, 1)
    assert second["status"] == "ATIVO"
    all_certs = service.listar(1)
    assert len(all_certs) == 2
    old = next(c for c in all_certs if c["id"] == first["id"])
    assert old["status"] == "INATIVO"
    assert any(e["tipo_evento"] == "SUBSTITUIDO" for e in service.eventos(first["id"]))


def test_extract_document_does_not_join_separated_number_fragments():
    assert service._extract_document("CNPJ: 43002824 430028") == (None, "NAO_IDENTIFICADO")
    assert service._extract_document("CNPJ: 50.410.847/0001-12") == ("50410847000112", "PJ")
    assert service._extract_document("CPF: 123.456.789-01") == ("12345678901", "PF")


def test_a1_extracts_cnpj_from_organizational_unit():
    data, password = _pfx("07112850000120", document_in_ou=True)
    meta = service._cert_metadata(data, password)
    assert meta["documento_titular"] == "07112850000120"
    assert meta["titular_tipo"] == "PJ"


def test_a1_prefers_icp_brasil_cnpj_oid_over_wrong_serial_and_ou():
    from cryptography.x509.oid import ObjectIdentifier

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EMPRESA TESTE LTDA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "EMPRESA TESTE LTDA"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, "22121066000172"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "22121066000172"),
        x509.NameAttribute(ObjectIdentifier("2.16.76.1.3.3"), "19167350000175"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    data = pkcs12.serialize_key_and_certificates(
        b"omega-icp", key, cert, None,
        serialization.BestAvailableEncryption(b"Senha@123")
    )
    meta = service._cert_metadata(data, "Senha@123")
    assert meta["documento_titular"] == "19167350000175"
    assert meta["titular_tipo"] == "PJ"


def test_serialnumber_digits_alone_are_not_mistaken_for_cnpj():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EMPRESA TESTE LTDA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "EMPRESA TESTE LTDA"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, "22121066000172"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    data = pkcs12.serialize_key_and_certificates(
        b"omega-serial", key, cert, None,
        serialization.BestAvailableEncryption(b"Senha@123")
    )
    meta = service._cert_metadata(data, "Senha@123")
    assert meta["documento_titular"] is None
    assert meta["titular_tipo"] == "NAO_IDENTIFICADO"


def test_a1_rejects_incompatible_cnpj():
    data, password = _pfx("12.345.678/0001-99")
    with pytest.raises(ValueError, match="incompatível"):
        service.cadastrar_a1(1, "ruim.pfx", data, password, 1)


def test_a1_rejects_wrong_password():
    data, _ = _pfx()
    with pytest.raises(ValueError, match="senha incorreta"):
        service.cadastrar_a1(1, "cert.pfx", data, "errada", 1)


def test_a3_never_creates_private_key_storage():
    c = service.cadastrar_a3(
        1, "TOKEN", "PJ", "50410847000112", "EMPRESA TESTE LTDA",
        "AC TESTE", "ABC123", "2026-01-01", "2027-01-01",
        "SHA256withRSA", "a" * 64, "Token Teste", "slot-1", 1
    )
    assert c["tipo"] == "A3"
    assert c["meio_armazenamento"] == "TOKEN"
    assert c["storage_ref"] if "storage_ref" in c else True
    assert c["apto_para_uso"] is True
    raw = service.listar(1)
    row = next(x for x in raw if x["id"] == c["id"])
    assert row.get("storage_ref") is None


def test_resumo_works_after_certificate_schema_is_present():
    # Regression: a legacy banco without apto_para_uso used to make /resumo return 500.
    from app.db.database import conectar_banco, criar_tabelas
    criar_tabelas()
    with conectar_banco() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(certificados)").fetchall()}
        assert "apto_para_uso" in cols
        conn.execute("SELECT empresa_id,status,data_validade,apto_para_uso FROM certificados").fetchall()


def test_certificate_migration_is_idempotent():
    from app.db.database import criar_tabelas, conectar_banco
    criar_tabelas()
    before = None
    with conectar_banco() as conn:
        before = {r[1] for r in conn.execute("PRAGMA table_info(certificados)").fetchall()}
    criar_tabelas()
    with conectar_banco() as conn:
        after = {r[1] for r in conn.execute("PRAGMA table_info(certificados)").fetchall()}
    assert after == before


def test_a1_password_is_recoverable_for_archived_and_expired_certificates():
    data, password = _pfx()
    first = service.cadastrar_a1(1, "antigo.pfx", data, password, 1)
    second = service.cadastrar_a1(1, "atual.pfx", data, password, 1)
    archived = service.obter(first["id"])
    assert archived["status"] == "INATIVO"
    assert service.obter_senha_a1(first["id"], 1) == password
    assert service.obter_senha_a1(second["id"], 1) == password
    assert any(e["tipo_evento"] == "SENHA_ACESSADA" for e in service.eventos(first["id"]))


def test_a3_pin_is_not_recoverable():
    c = service.cadastrar_a3(
        1, "TOKEN", "PJ", "50410847000112", "EMPRESA TESTE LTDA",
        "AC TESTE", "ABC123", "2026-01-01", "2027-01-01",
        "SHA256withRSA", "a" * 64, "Token Teste", "slot-1", 1
    )
    with pytest.raises(ValueError, match="Somente certificados A1"):
        service.obter_senha_a1(c["id"], 1)


def _pfx_pf(cpf="52998224725", password="SenhaPF@123"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.COMMON_NAME, "MARIA DA SILVA"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, f"CPF:{cpf}"),
    ])
    cert = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=365)).sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"omega-pf", key, cert, None, serialization.BestAvailableEncryption(password.encode())
    ), password


def test_pf_a1_is_real_person_entity_and_password_is_recoverable():
    data, password = _pfx_pf()
    c = service.cadastrar_pf_a1("529.982.247-25", "MARIA DA SILVA", "maria.pfx", data, password, 1)
    assert c["origem"] == "PF"
    assert c["pessoa_id"] is not None
    assert c["empresa_id"] is None
    assert c["cpf"] == "52998224725"
    assert service.obter_senha_pf_a1(c["id"], 1) == password
    assert service.baixar_pf_a1(c["id"], 1)[0] == data


def test_pf_a1_rejects_wrong_cpf_and_replacement_preserves_history():
    data, password = _pfx_pf()
    with pytest.raises(ValueError, match="incompatível"):
        service.cadastrar_pf_a1("11144477735", "MARIA DA SILVA", "ruim.pfx", data, password, 1)
    first = service.cadastrar_pf_a1("52998224725", "MARIA DA SILVA", "1.pfx", data, password, 1)
    second = service.cadastrar_pf_a1("52998224725", "MARIA DA SILVA", "2.pfx", data, password, 1)
    assert service.obter_pf(first["id"])["status"] == "INATIVO"
    assert second["status"] == "ATIVO"
    assert any(e["tipo_evento"] == "SUBSTITUIDO" for e in service.eventos_pf(first["id"]))


def test_pf_a3_does_not_store_pin_or_private_key():
    c = service.cadastrar_pf_a3(
        "52998224725", "MARIA DA SILVA", "CARTAO", "AC TESTE", "SERIE-PF",
        "2026-01-01", "2027-01-01", "SHA256withRSA", "b" * 64, "Leitor A3", "slot-pf", 1
    )
    assert c["origem"] == "PF"
    assert c["tipo"] == "A3"
    assert c["apto_para_uso"] is True
    assert c.get("storage_ref") is None


def test_a3_without_thumbprint_is_registered_but_not_usable_until_bridge_link():
    cert = service.cadastrar_a3(
        1, "TOKEN", "PJ", "50410847000112", "EMPRESA TESTE LTDA",
        "AC TESTE", "ABC123", "2026-01-01", "2027-01-01",
        "SHA256withRSA", None, "Token Teste", "slot-1", 1
    )
    assert cert["tipo"] == "A3"
    assert cert["status"] == "NAO_VINCULADO"
    assert cert["thumbprint_sha256"] is None
    assert cert["apto_para_uso"] is False


def test_pf_a3_requires_validity_from_bridge():
    with pytest.raises(ValueError, match="validade"):
        service.cadastrar_pf_a3(
            "52998224725", "MARIA TESTE", "CARTAO", "AC TESTE", "ABC123",
            "2026-01-01", None, "SHA256withRSA", "a" * 64,
            "Token Teste", "slot-1", 1,
        )


def test_pf_a3_expired_certificate_is_saved_as_not_usable():
    expired_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    cert = service.cadastrar_pf_a3(
        "52998224725", "MARIA DA SILVA", "CARTAO", "AC TESTE", "SERIE-EXP",
        "2024-01-01", expired_at, "SHA256withRSA", "c" * 64, "Leitor A3", "slot-exp", 1,
    )
    assert cert["status"] == "EXPIRADO"
    assert cert["apto_para_uso"] is False


def test_a3_date_only_validity_last_day_is_not_treated_as_midnight_expiry():
    today = datetime.now(timezone.utc).date().isoformat()
    parsed = service._parse_a3_validity(today)
    assert parsed.date().isoformat() == today
    assert parsed.hour == 23 and parsed.minute == 59 and parsed.second == 59
