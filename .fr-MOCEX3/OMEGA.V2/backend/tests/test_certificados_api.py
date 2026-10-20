
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from uuid import uuid4

from main import app
from app.services.auth_service import criar_usuario

def _pfx():
    password="Senha@123"
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    now=datetime.now(timezone.utc)
    subject=x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,"BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,"EMPRESA TESTE LTDA"),
        x509.NameAttribute(NameOID.COMMON_NAME,"EMPRESA TESTE LTDA"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER,"CNPJ:50.410.847/0001-12"),
    ])
    cert=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(
        x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=365)
    ).sign(key,hashes.SHA256())
    data=pkcs12.serialize_key_and_certificates(b"omega",key,cert,None,serialization.BestAvailableEncryption(password.encode()))
    return data,password

def _login(client,email,password):
    r=client.post("/api/v1/auth/login",json={"email":email,"senha":password})
    assert r.status_code==200,r.text
    return {"Authorization":f"Bearer {r.json()['access_token']}"}

def test_certificate_api_permissions_and_a1():
    user_email = f"cert-user-{uuid4().hex}@omega.local"
    criar_usuario("Usuário Cert", user_email, "User@12345", "USUARIO")
    with TestClient(app) as client:
        user_headers=_login(client,user_email,"User@12345")
        forbidden=client.post("/api/v1/certificados/a1",headers=user_headers,data={"empresa_id":"1","senha":"x"},files={"arquivo":("x.pfx",b"abc","application/x-pkcs12")})
        assert forbidden.status_code==403

        admin_headers=_login(client,"admin@omega.local","Admin@123")
        data,password=_pfx()
        ok=client.post("/api/v1/certificados/a1",headers=admin_headers,data={"empresa_id":"1","senha":password},files={"arquivo":("teste.pfx",data,"application/x-pkcs12")})
        assert ok.status_code==201,ok.text
        body=ok.json()
        assert "storage_ref" not in body
        assert "senha" not in body
        assert body["tipo"]=="A1"

        download=client.get(f"/api/v1/certificados/{body['id']}/download",headers=admin_headers)
        assert download.status_code==200
        assert download.content==data

def test_a1_upload_limit():
    with TestClient(app) as client:
        headers=_login(client,"admin@omega.local","Admin@123")
        oversized=b"x"*(10*1024*1024+1)
        r=client.post("/api/v1/certificados/a1",headers=headers,data={"empresa_id":"1","senha":"x"},files={"arquivo":("grande.pfx",oversized,"application/x-pkcs12")})
        assert r.status_code==413


def test_a3_api_does_not_accept_pfx_or_pin_storage():
    with TestClient(app) as client:
        headers=_login(client,"admin@omega.local","Admin@123")
        r=client.post("/api/v1/certificados/a3",headers=headers,data={
            "empresa_id":"1","meio":"TOKEN","titular_tipo":"PJ",
            "documento_titular":"50410847000112","nome_titular":"EMPRESA TESTE LTDA",
            "emissor":"AC TESTE","numero_serie":"SERIE-01",
            "data_emissao":"2026-01-01","data_validade":"2027-01-01",
            "algoritmo":"SHA256withRSA","dispositivo_modelo":"Token Teste",
            "dispositivo_identificador":"slot-01","thumbprint_sha256":"a"*64,
        })
        assert r.status_code==201,r.text
        body=r.json()
        assert body["tipo"]=="A3"
        assert "pin" not in body
        assert "senha" not in body


def test_a1_password_api_allows_admin_and_rejects_common_user():
    user_email = f"cert-pass-user-{uuid4().hex}@omega.local"
    criar_usuario("Usuário Senha", user_email, "User@12345", "USUARIO")
    with TestClient(app) as client:
        admin_headers=_login(client,"admin@omega.local","Admin@123")
        data,password=_pfx()
        ok=client.post("/api/v1/certificados/a1",headers=admin_headers,data={"empresa_id":"1","senha":password},files={"arquivo":("senha.pfx",data,"application/x-pkcs12")})
        assert ok.status_code==201,ok.text
        cert_id=ok.json()["id"]
        r=client.get(f"/api/v1/certificados/{cert_id}/senha",headers=admin_headers)
        assert r.status_code==200
        assert r.json()["senha"]==password
        d=client.get(f"/api/v1/certificados/{cert_id}/senha/download",headers=admin_headers)
        assert d.status_code==200
        assert d.content==f"{password}\n".encode()

        user_headers=_login(client,user_email,"User@12345")
        forbidden=client.get(f"/api/v1/certificados/{cert_id}/senha",headers=user_headers)
        assert forbidden.status_code==403


def test_pf_api_create_a1_and_list_without_fake_company():
    with TestClient(app) as client:
        headers = _login(client, "admin@omega.local", "Admin@123")
        data, password = _pfx_pf_api()
        r = client.post("/api/v1/certificados/pf/a1", headers=headers,
                        data={"cpf":"52998224725","nome":"MARIA DA SILVA","senha":password},
                        files={"arquivo":("maria.pfx",data,"application/x-pkcs12")})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["origem"] == "PF"
        assert body.get("empresa_id") is None
        listed = client.get("/api/v1/certificados/pf", headers=headers)
        assert listed.status_code == 200
        assert any(c["id"] == body["id"] for c in listed.json()["certificados"])


def _pfx_pf_api(cpf="52998224725", password="SenhaPF@123"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.COMMON_NAME, "MARIA DA SILVA"),
        x509.NameAttribute(NameOID.SERIAL_NUMBER, f"CPF:{cpf}"),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(key.public_key()).serial_number(
        x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=365)).sign(key,hashes.SHA256())
    data = pkcs12.serialize_key_and_certificates(b"omega-pf",key,cert,None,serialization.BestAvailableEncryption(password.encode()))
    return data,password
