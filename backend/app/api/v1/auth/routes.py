import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.services.auth_service import (
    alterar_senha,
    alterar_status_usuario,
    autenticar,
    buscar_usuario_por_id,
    create_access_token,
    decode_access_token,
    encerrar_sessoes,
    listar_usuarios,
    criar_usuario,
    validar_token_usuario,
    verify_password,
    registrar_usuario,
    criar_token_redefinicao,
    redefinir_senha_com_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])
bearer = HTTPBearer(auto_error=False)


class LoginIn(BaseModel):
    email: str
    senha: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=200)


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str
    senha: str = Field(min_length=8, max_length=200)
    perfil: str = "USUARIO"


class StatusIn(BaseModel):
    ativo: bool


class RegisterIn(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: str
    senha: str = Field(min_length=8, max_length=200)
    confirmar_senha: str = Field(min_length=8, max_length=200)


class ForgotPasswordIn(BaseModel):
    email: str


class ResetPasswordIn(BaseModel):
    token: str
    nova_senha: str = Field(min_length=8, max_length=200)
    confirmar_senha: str = Field(min_length=8, max_length=200)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Autenticação necessária.")
    try:
        payload = decode_access_token(credentials.credentials)
        return validar_token_usuario(payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def admin_user(user=Depends(current_user)):
    if user["perfil"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador.")
    return user


@router.post("/registrar", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn):
    if data.senha != data.confirmar_senha:
        raise HTTPException(status_code=400, detail="As senhas não conferem.")
    try:
        user = registrar_usuario(data.nome, data.email, data.senha)
        return {"ok": True, "usuario": {
            "id": user["id"], "nome": user["nome"], "email": user["email"],
            "perfil": user["perfil"]
        }}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/esqueci-senha")
def forgot_password(data: ForgotPasswordIn):
    token, _user = criar_token_redefinicao(data.email)
    response = {"ok": True, "mensagem": "Se o e-mail estiver cadastrado, as instruções de redefinição serão disponibilizadas."}
    if token and os.getenv("OMEGA_RESET_EXPOSE_URL", "true").lower() == "true":
        response["reset_token"] = token
        response["reset_url"] = f"/redefinir-senha?token={token}"
    return response


@router.post("/redefinir-senha")
def reset_password(data: ResetPasswordIn):
    if data.nova_senha != data.confirmar_senha:
        raise HTTPException(status_code=400, detail="As senhas não conferem.")
    try:
        redefinir_senha_com_token(data.token, data.nova_senha)
        return {"ok": True, "mensagem": "Senha redefinida com sucesso. Faça login novamente."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login")
def login(data: LoginIn):
    try:
        user = autenticar(data.email, data.senha)
        token = create_access_token(user)
        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": {
                "id": user["id"],
                "nome": user["nome"],
                "email": user["email"],
                "perfil": user["perfil"],
                "deve_trocar_senha": bool(user["deve_trocar_senha"]),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me")
def me(user=Depends(current_user)):
    return {
        "id": user["id"],
        "nome": user["nome"],
        "email": user["email"],
        "perfil": user["perfil"],
        "deve_trocar_senha": bool(user["deve_trocar_senha"]),
        "ultimo_login": user["ultimo_login"],
    }


@router.post("/logout")
def logout(user=Depends(current_user)):
    encerrar_sessoes(user["id"])
    return {"ok": True}


@router.post("/alterar-senha")
def change_password(data: ChangePasswordIn, user=Depends(current_user)):
    if not verify_password(data.senha_atual, user["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual inválida.")
    alterar_senha(user["id"], data.nova_senha)
    return {"ok": True, "mensagem": "Senha alterada. Faça login novamente."}


@router.get("/usuarios")
def users(_admin=Depends(admin_user)):
    return {"total": len(listar_usuarios()), "usuarios": listar_usuarios()}


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
def create_user(data: UsuarioCreate, _admin=Depends(admin_user)):
    try:
        return criar_usuario(data.nome, data.email, data.senha, data.perfil)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/usuarios/{user_id}/status")
def update_user_status(user_id: int, data: StatusIn, admin=Depends(admin_user)):
    if user_id == admin["id"] and not data.ativo:
        raise HTTPException(status_code=400, detail="O administrador atual não pode desativar a própria conta.")
    if not buscar_usuario_por_id(user_id):
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    alterar_status_usuario(user_id, data.ativo)
    return {"ok": True}
