import base64
import hashlib
import hmac
import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import jwt
from cryptography.fernet import Fernet

from app.db.database import conectar_banco

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("OMEGA_ACCESS_TOKEN_MINUTES", "480"))
PASSWORD_ITERATIONS = 310_000


def _secret() -> str:
    secret = os.getenv("OMEGA_JWT_SECRET", "").strip()
    placeholder_markers = ("GERE_UMA_CHAVE", "CHANGE_ME", "CHANGEME", "YOUR_SECRET", "YOUR-SECRET")
    if len(secret) < 32 or any(marker in secret.upper() for marker in placeholder_markers):
        raise RuntimeError(
            "OMEGA_JWT_SECRET precisa ser uma chave aleatória própria com pelo menos 32 caracteres; "
            "não use o valor de exemplo do .env.example."
        )
    return secret


def validar_configuracao_producao() -> None:
    """Falha no startup em produção quando segredos ou o administrador inicial faltam."""
    if os.getenv("OMEGA_ENV", "development").strip().lower() != "production":
        return
    _secret()
    key = os.getenv("OMEGA_CERTIFICADO_MASTER_KEY", "").strip()
    if not key:
        raise RuntimeError("OMEGA_CERTIFICADO_MASTER_KEY é obrigatória em produção.")
    try:
        Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError("OMEGA_CERTIFICADO_MASTER_KEY não é uma chave Fernet válida.") from exc
    if not os.getenv("CORS_ORIGINS", "").strip():
        raise RuntimeError("Defina CORS_ORIGINS com as origens reais do frontend em produção.")
    with conectar_banco() as conn:
        admin = conn.execute("SELECT 1 FROM usuarios WHERE ativo=1 AND perfil='ADMIN' LIMIT 1").fetchone()
    if not admin:
        raise RuntimeError(
            "Não existe administrador ativo. Configure OMEGA_ADMIN_EMAIL e OMEGA_ADMIN_PASSWORD "
            "para criar o primeiro administrador."
        )


def enviar_email_redefinicao(email_destino: str, nome: str, token: str) -> bool:
    """Entrega link de redefinição por SMTP. Não retorna o token quando SMTP não está configurado."""
    host = os.getenv("OMEGA_SMTP_HOST", "").strip()
    remetente = os.getenv("OMEGA_SMTP_FROM", "").strip()
    frontend_url = os.getenv("OMEGA_FRONTEND_URL", "").strip().rstrip("/")
    if not host or not remetente or not frontend_url:
        return False
    try:
        porta = int(os.getenv("OMEGA_SMTP_PORT", "587"))
    except ValueError as exc:
        raise RuntimeError("OMEGA_SMTP_PORT precisa ser numérica.") from exc
    link = f"{frontend_url}/redefinir-senha?token={quote(token)}"
    mensagem = EmailMessage()
    mensagem["Subject"] = "Redefinição de senha — Plataforma ÔMEGA"
    mensagem["From"] = remetente
    mensagem["To"] = email_destino
    mensagem.set_content(
        f"Olá, {nome or 'usuário'}.\n\n"
        f"Recebemos uma solicitação de redefinição de senha da Plataforma ÔMEGA.\n"
        f"Use o link abaixo para cadastrar uma nova senha (o link expira em "
        f"{RESET_TOKEN_MINUTES} minutos e só pode ser usado uma vez):\n\n{link}\n\n"
        "Se você não solicitou esta alteração, ignore esta mensagem."
    )
    usuario = os.getenv("OMEGA_SMTP_USER", "").strip()
    senha = os.getenv("OMEGA_SMTP_PASSWORD", "")
    usar_ssl = os.getenv("OMEGA_SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "sim", "yes"} or porta == 465
    contexto = ssl.create_default_context()
    if usar_ssl:
        with smtplib.SMTP_SSL(host, porta, timeout=20, context=contexto) as servidor:
            if usuario:
                servidor.login(usuario, senha)
            servidor.send_message(mensagem)
    else:
        with smtplib.SMTP(host, porta, timeout=20) as servidor:
            if os.getenv("OMEGA_SMTP_STARTTLS", "true").strip().lower() in {"1", "true", "sim", "yes"}:
                servidor.starttls(context=contexto)
            if usuario:
                servidor.login(usuario, senha)
            servidor.send_message(mensagem)
    return True


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations_s, salt_s, digest_s = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.urlsafe_b64decode(salt_s.encode())
        expected = base64.urlsafe_b64decode(digest_s.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user: dict[str, Any]) -> str:
    now = _utc_now()
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "perfil": user["perfil"],
        "ver": int(user.get("token_version", 0)),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ValueError("Sessão inválida ou expirada.") from exc


def ensure_admin_user() -> None:
    email = os.getenv("OMEGA_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("OMEGA_ADMIN_PASSWORD", "")
    name = os.getenv("OMEGA_ADMIN_NAME", "Administrador").strip() or "Administrador"
    if not email or not password:
        return
    with conectar_banco() as conn:
        row = conn.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone()
        if row:
            return
        conn.execute(
            """
            INSERT INTO usuarios(nome,email,senha_hash,perfil,ativo,token_version,deve_trocar_senha)
            VALUES(?,?,?,?,1,0,1)
            """,
            (name, email, hash_password(password), "ADMIN"),
        )
        conn.commit()


def autenticar(email: str, password: str) -> dict[str, Any]:
    email = email.strip().lower()
    with conectar_banco() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
        if not row or not row["ativo"] or not verify_password(password, row["senha_hash"]):
            raise ValueError("E-mail ou senha inválidos.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE usuarios SET ultimo_login=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (now, row["id"]))
        conn.execute(
            "INSERT INTO auditorias(entidade,entidade_id,acao,origem) VALUES(?,?,?,?)",
            ("usuarios", row["id"], "LOGIN", "AUTH"),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM usuarios WHERE id=?", (row["id"],)).fetchone())


def buscar_usuario_por_id(user_id: int) -> dict[str, Any] | None:
    with conectar_banco() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def validar_token_usuario(payload: dict[str, Any]) -> dict[str, Any]:
    user = buscar_usuario_por_id(int(payload["sub"]))
    if not user or not user["ativo"]:
        raise ValueError("Usuário não autorizado.")
    if int(user.get("token_version", 0)) != int(payload.get("ver", 0)):
        raise ValueError("Sessão revogada. Faça login novamente.")
    return user


def encerrar_sessoes(user_id: int) -> None:
    with conectar_banco() as conn:
        conn.execute("UPDATE usuarios SET token_version=token_version+1, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (user_id,))
        conn.execute(
            "INSERT INTO auditorias(entidade,entidade_id,acao,origem) VALUES(?,?,?,?)",
            ("usuarios", user_id, "LOGOUT", "AUTH"),
        )
        conn.commit()


def alterar_senha(user_id: int, nova_senha: str) -> None:
    password_hash = hash_password(nova_senha)
    with conectar_banco() as conn:
        conn.execute(
            "UPDATE usuarios SET senha_hash=?, deve_trocar_senha=0, token_version=token_version+1, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (password_hash, user_id),
        )
        conn.execute(
            "INSERT INTO auditorias(entidade,entidade_id,acao,origem) VALUES(?,?,?,?)",
            ("usuarios", user_id, "ALTERAR_SENHA", "AUTH"),
        )
        conn.commit()


def listar_usuarios() -> list[dict[str, Any]]:
    with conectar_banco() as conn:
        rows = conn.execute(
            "SELECT id,nome,email,perfil,ativo,deve_trocar_senha,ultimo_login,criado_em,atualizado_em FROM usuarios ORDER BY nome"
        ).fetchall()
        return [dict(r) for r in rows]


def criar_usuario(nome: str, email: str, password: str, perfil: str) -> dict[str, Any]:
    email = email.strip().lower()
    perfil = perfil.strip().upper()
    if perfil not in {"ADMIN", "USUARIO"}:
        raise ValueError("Perfil inválido. Use ADMIN ou USUARIO.")
    with conectar_banco() as conn:
        if conn.execute("SELECT 1 FROM usuarios WHERE email=?", (email,)).fetchone():
            raise ValueError("Já existe um usuário com este e-mail.")
        cur = conn.execute(
            """
            INSERT INTO usuarios(nome,email,senha_hash,perfil,ativo,token_version,deve_trocar_senha)
            VALUES(?,?,?,?,1,0,1)
            """,
            (nome.strip(), email, hash_password(password), perfil),
        )
        conn.execute(
            "INSERT INTO auditorias(entidade,entidade_id,acao,origem) VALUES(?,?,?,?)",
            ("usuarios", cur.lastrowid, "CRIAR", "AUTH"),
        )
        conn.commit()
        return dict(conn.execute("SELECT id,nome,email,perfil,ativo,deve_trocar_senha,ultimo_login,criado_em,atualizado_em FROM usuarios WHERE id=?", (cur.lastrowid,)).fetchone())


def alterar_status_usuario(user_id: int, ativo: bool) -> None:
    with conectar_banco() as conn:
        conn.execute("UPDATE usuarios SET ativo=?, token_version=token_version+1, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (1 if ativo else 0, user_id))
        conn.commit()


RESET_TOKEN_MINUTES = int(os.getenv("OMEGA_RESET_TOKEN_MINUTES", "30"))


def registrar_usuario(nome: str, email: str, password: str) -> dict[str, Any]:
    email = email.strip().lower()
    nome = nome.strip()
    if len(nome) < 2:
        raise ValueError("Informe seu nome completo.")
    if "@" not in email or len(email) < 5:
        raise ValueError("Informe um e-mail válido.")
    password_hash = hash_password(password)
    with conectar_banco() as conn:
        if conn.execute("SELECT 1 FROM usuarios WHERE email=?", (email,)).fetchone():
            raise ValueError("Já existe uma conta com este e-mail.")
        cur = conn.execute(
            """
            INSERT INTO usuarios(nome,email,senha_hash,perfil,ativo,token_version,deve_trocar_senha)
            VALUES(?,?,?,?,1,0,0)
            """,
            (nome, email, password_hash, "USUARIO"),
        )
        conn.execute(
            "INSERT INTO auditorias(entidade,entidade_id,acao,origem) VALUES(?,?,?,?)",
            ("usuarios", cur.lastrowid, "REGISTRO", "AUTH"),
        )
        conn.commit()
        return dict(conn.execute("SELECT id,nome,email,perfil,ativo,deve_trocar_senha,ultimo_login FROM usuarios WHERE id=?", (cur.lastrowid,)).fetchone())


def criar_token_redefinicao(email: str) -> tuple[str | None, dict[str, Any] | None]:
    email = email.strip().lower()
    token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expira = (_utc_now() + timedelta(minutes=RESET_TOKEN_MINUTES)).isoformat()
    with conectar_banco() as conn:
        user = conn.execute("SELECT * FROM usuarios WHERE email=? AND ativo=1", (email,)).fetchone()
        if not user:
            return None, None
        conn.execute("UPDATE tokens_redefinicao_senha SET usado_em=CURRENT_TIMESTAMP WHERE usuario_id=? AND usado_em IS NULL", (user["id"],))
        conn.execute("INSERT INTO tokens_redefinicao_senha(usuario_id,token_hash,expira_em) VALUES(?,?,?)", (user["id"], token_hash, expira))
        conn.execute(
            "INSERT INTO auditorias(entidade,entidade_id,acao,origem) VALUES(?,?,?,?)",
            ("usuarios", user["id"], "SOLICITAR_REDEFINICAO", "AUTH"),
        )
        conn.commit()
        return token, dict(user)


def redefinir_senha_com_token(token: str, nova_senha: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with conectar_banco() as conn:
        row = conn.execute(
            "SELECT * FROM tokens_redefinicao_senha WHERE token_hash=? AND usado_em IS NULL AND expira_em>? ORDER BY id DESC LIMIT 1",
            (token_hash, _utc_now().isoformat()),
        ).fetchone()
        if not row:
            raise ValueError("O link de redefinição é inválido ou expirou.")
        password_hash = hash_password(nova_senha)
        conn.execute(
            "UPDATE usuarios SET senha_hash=?, deve_trocar_senha=0, token_version=token_version+1, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (password_hash, row["usuario_id"]),
        )
        conn.execute("UPDATE tokens_redefinicao_senha SET usado_em=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        conn.execute(
            "INSERT INTO auditorias(entidade,entidade_id,acao,origem) VALUES(?,?,?,?)",
            ("usuarios", row["usuario_id"], "REDEFINIR_SENHA", "AUTH"),
        )
        conn.commit()
