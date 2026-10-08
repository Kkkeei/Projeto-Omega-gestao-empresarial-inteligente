
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.v1.auth.routes import current_user, admin_user
from app.modules.certificados import service

router = APIRouter(prefix="/api/v1/certificados", tags=["Certificados Digitais"])


def _get_cert(cert_id: int):
    try:
        return service.obter(cert_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/resumo")
def resumo(_user=Depends(current_user)):
    return service.resumo()


@router.get("")
def listar(empresa_id: int | None = None, tipo: str | None = None, _user=Depends(current_user)):
    return {"total": len(service.listar(empresa_id, tipo)), "certificados": service.listar(empresa_id, tipo)}


@router.get("/pf")
def listar_pf(_user=Depends(current_user)):
    certificados = service.listar_pf()
    return {"total": len(certificados), "certificados": certificados}


@router.get("/pf/{cert_id}")
def detalhe_pf(cert_id: int, _user=Depends(current_user)):
    try:
        return service.obter_pf(cert_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/pf/{cert_id}/eventos")
def historico_pf(cert_id: int, _user=Depends(current_user)):
    try:
        service.obter_pf(cert_id)
        eventos = service.eventos_pf(cert_id)
        return {"total": len(eventos), "eventos": eventos}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/pf/{cert_id}/usos")
def usos_pf(cert_id: int, _user=Depends(current_user)):
    try:
        service.obter_pf(cert_id)
        usos = service.usos_pf(cert_id)
        return {"total": len(usos), "usos": usos}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/pf/a1", status_code=201)
async def cadastrar_pf_a1(
    cpf: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    senha: Annotated[str, Form(min_length=1, max_length=200)],
    arquivo: Annotated[UploadFile, File()],
    email: Annotated[str | None, Form()] = None,
    telefone: Annotated[str | None, Form()] = None,
    admin=Depends(admin_user),
):
    filename = arquivo.filename or "certificado.p12"
    if not filename.lower().endswith((".pfx", ".p12")):
        raise HTTPException(400, "Envie um arquivo .PFX ou .P12.")
    max_bytes = service.MAX_UPLOAD_BYTES
    if arquivo.size is not None and arquivo.size > max_bytes:
        raise HTTPException(413, f"O arquivo excede o limite de {service.MAX_UPLOAD_MB} MB.")
    data = await arquivo.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"O arquivo excede o limite de {service.MAX_UPLOAD_MB} MB.")
    try:
        return service.cadastrar_pf_a1(cpf, nome, filename, data, senha, admin["id"], email, telefone)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pf/a3", status_code=201)
def cadastrar_pf_a3(
    cpf: Annotated[str, Form()],
    nome: Annotated[str, Form()],
    meio: Annotated[str, Form()],
    emissor: Annotated[str | None, Form()] = None,
    numero_serie: Annotated[str | None, Form()] = None,
    data_emissao: Annotated[str | None, Form()] = None,
    data_validade: Annotated[str | None, Form()] = None,
    algoritmo: Annotated[str | None, Form()] = None,
    thumbprint_sha256: Annotated[str | None, Form()] = None,
    dispositivo_modelo: Annotated[str | None, Form()] = None,
    dispositivo_identificador: Annotated[str | None, Form()] = None,
    email: Annotated[str | None, Form()] = None,
    telefone: Annotated[str | None, Form()] = None,
    admin=Depends(admin_user),
):
    try:
        return service.cadastrar_pf_a3(cpf, nome, meio, emissor, numero_serie, data_emissao, data_validade, algoritmo,
                                       thumbprint_sha256, dispositivo_modelo, dispositivo_identificador, admin["id"], email, telefone)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pf/{cert_id}/testar")
def testar_pf(cert_id: int, admin=Depends(admin_user)):
    try:
        result = service.testar_pf(cert_id, admin["id"])
        service.registrar_uso_pf(cert_id, "CERTIFICADOS", "ATIVO" if result.get("ok") else "AGUARDANDO_BRIDGE")
        return result
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/pf/{cert_id}/senha")
def senha_pf(cert_id: int, admin=Depends(admin_user)):
    try:
        password = service.obter_senha_pf_a1(cert_id, admin["id"])
        return {"certificado_id": cert_id, "senha": password, "mensagem": "Credencial recuperada. Trate esta informação como segredo."}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/pf/{cert_id}/senha/download")
def baixar_senha_pf(cert_id: int, admin=Depends(admin_user)):
    try:
        password = service.obter_senha_pf_a1(cert_id, admin["id"])
        return Response(content=(password + "\n").encode("utf-8"), media_type="text/plain; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="senha-certificado-pf-{cert_id}.txt"'})
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/pf/{cert_id}/download")
def download_pf(cert_id: int, admin=Depends(admin_user)):
    try:
        data, filename = service.baixar_pf_a1(cert_id, admin["id"])
        return Response(content=data, media_type="application/x-pkcs12", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/pf/{cert_id}/desativar")
def desativar_pf(cert_id: int, admin=Depends(admin_user)):
    try:
        return service.desativar_pf(cert_id, admin["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/pf/{cert_id}/solicitar-substituicao")
def solicitar_substituicao_pf(cert_id: int, user=Depends(current_user)):
    try:
        return service.solicitar_substituicao_pf(cert_id, user["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{cert_id}")
def detalhe(cert_id: int, _user=Depends(current_user)):
    return _get_cert(cert_id)


@router.get("/{cert_id}/eventos")
def historico(cert_id: int, _user=Depends(current_user)):
    _get_cert(cert_id)
    return {"total": len(service.eventos(cert_id)), "eventos": service.eventos(cert_id)}


@router.get("/{cert_id}/usos")
def usos(cert_id: int, _user=Depends(current_user)):
    _get_cert(cert_id)
    return {"total": len(service.usos(cert_id)), "usos": service.usos(cert_id)}


@router.post("/a1", status_code=201)
async def cadastrar_a1(
    empresa_id: Annotated[int, Form()],
    senha: Annotated[str, Form(min_length=1, max_length=200)],
    arquivo: Annotated[UploadFile, File()],
    admin=Depends(admin_user),
):
    filename = arquivo.filename or "certificado.p12"
    if not filename.lower().endswith((".pfx", ".p12")):
        raise HTTPException(400, "Envie um arquivo .PFX ou .P12.")
    # Limite de tamanho antes de materializar um upload excessivo.
    max_bytes = service.MAX_UPLOAD_BYTES
    if arquivo.size is not None and arquivo.size > max_bytes:
        raise HTTPException(413, f"O arquivo excede o limite de {service.MAX_UPLOAD_MB} MB.")
    data = await arquivo.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"O arquivo excede o limite de {service.MAX_UPLOAD_MB} MB.")
    try:
        return service.cadastrar_a1(empresa_id, filename, data, senha, admin["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/a3", status_code=201)
def cadastrar_a3(
    empresa_id: Annotated[int, Form()],
    meio: Annotated[str, Form()],
    titular_tipo: Annotated[str, Form()],
    documento_titular: Annotated[str | None, Form()] = None,
    nome_titular: Annotated[str | None, Form()] = None,
    emissor: Annotated[str | None, Form()] = None,
    numero_serie: Annotated[str | None, Form()] = None,
    data_emissao: Annotated[str | None, Form()] = None,
    data_validade: Annotated[str | None, Form()] = None,
    algoritmo: Annotated[str | None, Form()] = None,
    thumbprint_sha256: Annotated[str | None, Form()] = None,
    dispositivo_modelo: Annotated[str | None, Form()] = None,
    dispositivo_identificador: Annotated[str | None, Form()] = None,
    admin=Depends(admin_user),
):
    try:
        return service.cadastrar_a3(
            empresa_id, meio, titular_tipo, documento_titular, nome_titular,
            emissor, numero_serie, data_emissao, data_validade, algoritmo, thumbprint_sha256,
            dispositivo_modelo, dispositivo_identificador, admin["id"]
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{cert_id}/testar")
def testar(cert_id: int, admin=Depends(admin_user)):
    _get_cert(cert_id)
    try:
        result = service.testar(cert_id, admin['id'])
        service.registrar_uso(cert_id, "CERTIFICADOS", "ATIVO" if result.get("ok") else "AGUARDANDO_BRIDGE")
        return result
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{cert_id}/senha")
def senha(cert_id: int, admin=Depends(admin_user)):
    try:
        password = service.obter_senha_a1(cert_id, admin["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"certificado_id": cert_id, "senha": password, "mensagem": "Credencial recuperada. Trate esta informação como segredo."}


@router.get("/{cert_id}/senha/download")
def baixar_senha(cert_id: int, admin=Depends(admin_user)):
    try:
        password = service.obter_senha_a1(cert_id, admin["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return Response(
        content=(password + "\n").encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="senha-certificado-{cert_id}.txt"'},
    )


@router.get("/{cert_id}/download")
def download(cert_id: int, admin=Depends(admin_user)):
    _get_cert(cert_id)
    try:
        data, filename = service.baixar_a1(cert_id, admin['id'])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return Response(
        content=data,
        media_type="application/x-pkcs12",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{cert_id}/desativar")
def desativar(cert_id: int, admin=Depends(admin_user)):
    try:
        return service.desativar(cert_id, admin["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{cert_id}/solicitar-substituicao")
def solicitar_substituicao(cert_id: int, user=Depends(current_user)):
    try:
        return service.solicitar_substituicao(cert_id, user["id"])
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
