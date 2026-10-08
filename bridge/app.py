
from __future__ import annotations

import base64
import hashlib
import os
import platform
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cryptography import x509
from cryptography.hazmat.primitives import hashes

APP_VERSION = "1.0.0"
TOKEN = os.getenv("OMEGA_BRIDGE_TOKEN", "").strip()
ALLOWED_ORIGINS = {
    item.strip() for item in os.getenv(
        "OMEGA_BRIDGE_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if item.strip()
}
PKCS11_MODULE = os.getenv("OMEGA_PKCS11_MODULE", "").strip()


def _pkcs11_candidates() -> list[str]:
    """Return likely PKCS#11 modules, prioritizing an explicit configuration."""
    if PKCS11_MODULE:
        return [PKCS11_MODULE]
    if platform.system().lower() == "windows":
        return [
            r"C:\Windows\System32\aetpkss1.dll",
            r"C:\Windows\SysWOW64\aetpkss1.dll",
            r"C:\Windows\System32\eTPKCS11.dll",
            r"C:\Windows\SysWOW64\eTPKCS11.dll",
        ]
    return [
        "/usr/lib/libaetpkss.so",
        "/usr/lib/x86_64-linux-gnu/libaetpkss.so",
        "/usr/lib/libeTPkcs11.so",
        "/usr/lib/x86_64-linux-gnu/libeTPkcs11.so",
    ]


def _resolve_pkcs11_module() -> str | None:
    for candidate in _pkcs11_candidates():
        if Path(candidate).is_file():
            return candidate
    return None

app = FastAPI(title="OMEGA Bridge", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _check_token(authorization: str | None):
    if not TOKEN:
        raise HTTPException(503, "OMEGA_BRIDGE_TOKEN não configurado.")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Autenticação do Bridge necessária.")
    if authorization[7:].strip() != TOKEN:
        raise HTTPException(401, "Token do Bridge inválido.")


def _check_origin(origin: str | None):
    if origin and origin not in ALLOWED_ORIGINS:
        raise HTTPException(403, "Origem não autorizada pelo OMEGA Bridge.")


def _readers():
    try:
        from smartcard.System import readers
    except ImportError:
        raise HTTPException(503, "PySCard/PCSC não está instalado neste computador.")
    try:
        return [str(reader) for reader in readers()]
    except Exception as exc:
        raise HTTPException(503, f"Não foi possível consultar os leitores PC/SC: {exc}") from exc


def _pkcs11():
    module_path = _resolve_pkcs11_module()
    if not module_path:
        if PKCS11_MODULE:
            raise HTTPException(503, f"Biblioteca PKCS#11 não encontrada: {PKCS11_MODULE}")
        raise HTTPException(503, "Biblioteca PKCS#11 não encontrada. Instale o gerenciador do cartão (SafeSign/SafeNet) ou configure OMEGA_PKCS11_MODULE.")
    try:
        import pkcs11
        return pkcs11, pkcs11.lib(module_path)
    except ImportError as exc:
        raise HTTPException(503, "python-pkcs11 não está instalado no Bridge.") from exc
    except Exception as exc:
        raise HTTPException(503, f"Não foi possível carregar o módulo PKCS#11: {exc}") from exc


def _cert_metadata(value: bytes) -> dict[str, Any]:
    cert = x509.load_der_x509_certificate(value)
    subject = cert.subject.rfc4514_string()
    issuer = cert.issuer.rfc4514_string()
    serial_attrs = cert.subject.get_attributes_for_oid(x509.oid.NameOID.SERIAL_NUMBER)
    serial_text = serial_attrs[0].value if serial_attrs else ""
    digits = "".join(ch for ch in serial_text if ch.isdigit())
    documento = next((x for x in __import__("re").findall(r"\d{14}", digits)), None)
    titular_tipo = "PJ" if documento else "NAO_IDENTIFICADO"
    if not documento:
        cpf = next((x for x in __import__("re").findall(r"\d{11}", digits)), None)
        documento = cpf
        titular_tipo = "PF" if cpf else "NAO_IDENTIFICADO"
    return {
        "subject": subject,
        "issuer": issuer,
        "serial": format(cert.serial_number, "x"),
        "thumbprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
        "valid_from": cert.not_valid_before_utc.isoformat(),
        "valid_to": cert.not_valid_after_utc.isoformat(),
        "documento_titular": documento,
        "titular_tipo": titular_tipo,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "bridge": "OMEGA Bridge",
        "version": APP_VERSION,
        "pcsc": _pcsc_available(),
        "pkcs11_configured": bool(_resolve_pkcs11_module()),
        "pkcs11_module": _resolve_pkcs11_module(),
    }


def _pcsc_available():
    try:
        from smartcard.System import readers
        readers()
        return True
    except Exception:
        return False


@app.get("/diagnostics")
def diagnostics(request: Request, authorization: str | None = Header(default=None)):
    _check_origin(request.headers.get("origin"))
    _check_token(authorization)
    reader_names: list[str] = []
    reader_error = None
    try:
        reader_names = _readers()
    except HTTPException as exc:
        reader_error = str(exc.detail)
    module = _resolve_pkcs11_module()
    return {
        "platform": platform.platform(),
        "pcsc": bool(reader_names),
        "readers": reader_names,
        "reader_error": reader_error,
        "pkcs11_configured": bool(module),
        "pkcs11_module": module,
        "hint": "No Windows, cartão VALID com SafeSign normalmente usa C:\\Windows\\System32\\aetpkss1.dll; se o middleware for SafeNet, use eTPKCS11.dll." if platform.system().lower() == "windows" else None,
    }


@app.get("/readers")
def readers_endpoint(request: Request, authorization: str | None = Header(default=None)):
    _check_origin(request.headers.get("origin"))
    _check_token(authorization)
    return {"readers": _readers()}


@app.get("/certificates")
def certificates_endpoint(
    request: Request,
    authorization: str | None = Header(default=None),
):
    _check_origin(request.headers.get("origin"))
    _check_token(authorization)
    pkcs11_mod, lib = _pkcs11()
    result = []
    try:
        for slot in lib.get_slots(token_present=True):
            token = slot.get_token()
            with token.open() as session:
                for obj in session.get_objects({pkcs11_mod.Attribute.CLASS: pkcs11_mod.ObjectClass.CERTIFICATE}):
                    value = obj[pkcs11_mod.Attribute.VALUE]
                    meta = _cert_metadata(bytes(value))
                    label = obj.get(pkcs11_mod.Attribute.LABEL)
                    obj_id = obj.get(pkcs11_mod.Attribute.ID)
                    result.append({
                        "slot": str(slot.slot_id),
                        "token_label": token.label,
                        "label": label,
                        "id": base64.b64encode(bytes(obj_id or b"")).decode(),
                        **meta,
                    })
    except Exception as exc:
        raise HTTPException(503, f"Não foi possível enumerar certificados PKCS#11: {exc}") from exc
    return {"total": len(result), "certificates": result}


class SignRequest(BaseModel):
    certificate_thumbprint: str
    data_b64: str = Field(min_length=1)
    pin: str = Field(min_length=1, max_length=200)
    algorithm: str = "AUTO"


@app.post("/sign")
def sign(
    request: Request,
    body: SignRequest,
    authorization: str | None = Header(default=None),
):
    _check_origin(request.headers.get("origin"))
    _check_token(authorization)
    pkcs11_mod, lib = _pkcs11()
    try:
        raw = base64.b64decode(body.data_b64, validate=True)
    except Exception as exc:
        raise HTTPException(400, "data_b64 inválido.") from exc
    mechanism_name = body.algorithm.upper()
    mechanism = getattr(pkcs11_mod.Mechanism, mechanism_name, None)
    if mechanism is None:
        raise HTTPException(400, f"Mecanismo PKCS#11 não suportado: {mechanism_name}")
    try:
        for slot in lib.get_slots(token_present=True):
            token = slot.get_token()
            with token.open(user_pin=body.pin) as session:
                certificates = list(session.get_objects({
                    pkcs11_mod.Attribute.CLASS: pkcs11_mod.ObjectClass.CERTIFICATE
                }))
                target = None
                for cert_obj in certificates:
                    value = bytes(cert_obj[pkcs11_mod.Attribute.VALUE])
                    meta = _cert_metadata(value)
                    if meta["thumbprint_sha256"].lower() == body.certificate_thumbprint.lower():
                        target = cert_obj
                        break
                if target is None:
                    continue
                cert_id = target[pkcs11_mod.Attribute.ID]
                keys = list(session.get_objects({
                    pkcs11_mod.Attribute.CLASS: pkcs11_mod.ObjectClass.PRIVATE_KEY,
                    pkcs11_mod.Attribute.ID: cert_id,
                }))
                if not keys:
                    raise HTTPException(400, "Chave privada correspondente ao certificado não encontrada.")
                key = keys[0]
                if mechanism_name == "AUTO":
                    key_type = key.get(pkcs11_mod.Attribute.KEY_TYPE)
                    if key_type == pkcs11_mod.KeyType.RSA:
                        mechanism = pkcs11_mod.Mechanism.SHA256_RSA_PKCS
                    elif key_type in {pkcs11_mod.KeyType.EC, getattr(pkcs11_mod.KeyType, "EC_EDWARDS", None)}:
                        mechanism = pkcs11_mod.Mechanism.SHA256_ECDSA
                    else:
                        raise HTTPException(400, f"Tipo de chave PKCS#11 não suportado: {key_type}")
                signature = key.sign(raw, mechanism=mechanism)
                # O PIN só existe nesta chamada e nunca é persistido/logado.
                return {
                    "ok": True,
                    "signature_b64": base64.b64encode(signature).decode(),
                    "certificate_thumbprint": meta["thumbprint_sha256"],
                }
        raise HTTPException(404, "Certificado A3 não encontrado no dispositivo.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Falha na assinatura A3: {exc}") from exc


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1008, reason="Origem não autorizada")
        return
    if not TOKEN:
        await websocket.close(code=1011, reason="Bridge sem token configurado")
        return
    offered = websocket.headers.get("sec-websocket-protocol", "")
    offered_parts = [p.strip() for p in offered.split(",") if p.strip()]
    # O cliente envia ['omega.v1', TOKEN]. O token não vai na URL.
    if TOKEN not in offered_parts or "omega.v1" not in offered_parts:
        await websocket.close(code=1008, reason="Autenticação inválida")
        return
    await websocket.accept(subprotocol="omega.v1")
    try:
        while True:
            message = await websocket.receive_json()
            command = message.get("command")
            if command == "ping":
                await websocket.send_json({"event":"pong"})
            elif command == "readers":
                try:
                    await websocket.send_json({"event":"readers","data":{"readers":_readers()}})
                except HTTPException as exc:
                    await websocket.send_json({"event":"error","status":exc.status_code,"message":exc.detail})
            elif command == "close":
                await websocket.close()
                return
            else:
                await websocket.send_json({"event":"error","status":400,"message":"Comando não suportado."})
    except WebSocketDisconnect:
        return
