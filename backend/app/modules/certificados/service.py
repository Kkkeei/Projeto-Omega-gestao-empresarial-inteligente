
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID

from app.db.database import conectar_banco, STORAGE_BASE

MAX_UPLOAD_MB = int(os.getenv("OMEGA_CERTIFICADO_MAX_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


def _master_key() -> bytes:
    configured = os.getenv("OMEGA_CERTIFICADO_MASTER_KEY", "").strip()
    if configured:
        try:
            key = configured.encode()
            Fernet(key)
            return key
        except Exception as exc:
            raise RuntimeError("OMEGA_CERTIFICADO_MASTER_KEY inválida. Gere uma chave Fernet válida.") from exc
    # Desenvolvimento: derivação determinística a partir de um segredo já obrigatório.
    # Produção deve sempre definir OMEGA_CERTIFICADO_MASTER_KEY separadamente.
    if os.getenv("OMEGA_ENV", "development").lower() == "production":
        raise RuntimeError("OMEGA_CERTIFICADO_MASTER_KEY é obrigatória em produção.")
    jwt_secret = os.getenv("OMEGA_JWT_SECRET", "").strip()
    if len(jwt_secret) < 32:
        raise RuntimeError("Defina OMEGA_CERTIFICADO_MASTER_KEY ou um OMEGA_JWT_SECRET com pelo menos 32 caracteres.")
    return base64.urlsafe_b64encode(hashlib.sha256(("OMEGA-CERTIFICADO-A1:" + jwt_secret).encode()).digest())


def _fernet() -> Fernet:
    return Fernet(_master_key())


def _encrypt(value: bytes) -> bytes:
    return _fernet().encrypt(value)


def _decrypt(value: bytes) -> bytes:
    try:
        return _fernet().decrypt(value)
    except InvalidToken as exc:
        raise ValueError("Não foi possível descriptografar a credencial do certificado.") from exc


def _storage_dir() -> Path:
    path = STORAGE_BASE / "certificados"
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def _normalizar_documento(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _subject_value(cert, oid) -> str | None:
    attrs = cert.subject.get_attributes_for_oid(oid)
    return attrs[0].value if attrs else None


def _issuer_value(cert, oid) -> str | None:
    attrs = cert.issuer.get_attributes_for_oid(oid)
    return attrs[0].value if attrs else None


def _extract_document(subject_text: str) -> tuple[str | None, str]:
    digits = _normalizar_documento(subject_text)
    # Prioriza CNPJ; depois CPF. O campo SERIALNUMBER de certificados ICP-Brasil
    # costuma carregar o identificador do titular.
    for match in re.findall(r"\d{14}", digits):
        return match, "PJ"
    for match in re.findall(r"\d{11}", digits):
        return match, "PF"
    return None, "NAO_IDENTIFICADO"


def _cert_metadata(data: bytes, password: str) -> dict[str, Any]:
    if not data:
        raise ValueError("O arquivo do certificado está vazio.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"O certificado excede o limite de {MAX_UPLOAD_MB} MB.")
    try:
        private_key, cert, extras = pkcs12.load_key_and_certificates(data, password.encode("utf-8"))
    except Exception as exc:
        raise ValueError("Arquivo PFX/P12 inválido ou senha incorreta.") from exc
    if cert is None:
        raise ValueError("O arquivo não contém um certificado X.509 válido.")
    if private_key is None:
        raise ValueError("O certificado não contém chave privada disponível.")
    subject = cert.subject.rfc4514_string()
    serial_attr = _subject_value(cert, NameOID.SERIAL_NUMBER) or ""
    document, titular_tipo = _extract_document(serial_attr)
    if not document:
        # Alguns emissores não usam SERIALNUMBER; nesse caso procuramos apenas
        # nos campos de identificação do titular, nunca no subject completo,
        # para evitar capturar números de OID/códigos de outros atributos.
        for value in (
            _subject_value(cert, NameOID.COMMON_NAME) or "",
            _subject_value(cert, NameOID.ORGANIZATION_NAME) or "",
        ):
            document, titular_tipo = _extract_document(value)
            if document:
                break
    common_name = _subject_value(cert, NameOID.COMMON_NAME)
    organization = _subject_value(cert, NameOID.ORGANIZATION_NAME)
    issuer = _issuer_value(cert, NameOID.COMMON_NAME) or cert.issuer.rfc4514_string()
    now = datetime.now(timezone.utc)
    not_before = cert.not_valid_before_utc
    not_after = cert.not_valid_after_utc
    if not_before > now:
        validity = "AINDA_NAO_VALIDO"
    elif not_after < now:
        validity = "EXPIRADO"
    else:
        validity = "ATIVO"
    return {
        "nome_titular": organization or common_name or subject,
        "documento_titular": document,
        "titular_tipo": titular_tipo,
        "emissor": issuer,
        "numero_serie": format(cert.serial_number, "x"),
        "thumbprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
        "algoritmo": cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else None,
        "data_emissao": not_before.isoformat(),
        "data_validade": not_after.isoformat(),
        "validity": validity,
        "subject": subject,
    }


def _empresa(empresa_id: int):
    with conectar_banco() as conn:
        row = conn.execute("SELECT id,cnpj,razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        return dict(row) if row else None


def _compatibilidade(empresa: dict, documento: str | None) -> tuple[bool, str]:
    if not documento:
        return False, "Não foi possível identificar CPF/CNPJ no certificado."
    cnpj = _normalizar_documento(empresa["cnpj"])
    if documento == cnpj:
        return True, "CNPJ compatível."
    return False, f"Certificado incompatível: o documento {documento} não corresponde ao CNPJ {cnpj} da empresa."


def _evento(conn, cert_id: int, tipo: str, user_id: int | None, descricao: str, dados: dict | None = None):
    conn.execute(
        "INSERT INTO certificado_eventos(certificado_id,tipo_evento,usuario_id,descricao,dados) VALUES(?,?,?,?,?)",
        (cert_id, tipo, user_id, descricao, json.dumps(dados or {}, ensure_ascii=False, default=str)),
    )


def _public(row: dict) -> dict:
    row = dict(row)
    row["origem"] = "PJ"
    row.pop("storage_ref", None)
    row.pop("arquivo_nome", None)
    row.pop("criado_por", None)
    row["apto_para_uso"] = bool(row.get("apto_para_uso"))
    return row


def listar(empresa_id: int | None = None, tipo: str | None = None):
    with conectar_banco() as conn:
        sql = """
        SELECT c.*, e.razao_social, e.cnpj
          FROM certificados c
          JOIN empresas e ON e.id=c.empresa_id
         WHERE 1=1
        """
        params: list[Any] = []
        if empresa_id is not None:
            sql += " AND c.empresa_id=?"; params.append(empresa_id)
        if tipo:
            sql += " AND c.tipo=?"; params.append(tipo)
        sql += " ORDER BY CASE c.status WHEN 'ATIVO' THEN 0 WHEN 'NAO_VINCULADO' THEN 1 WHEN 'EXPIRADO' THEN 2 ELSE 3 END, c.data_validade"
        return [_public(dict(r)) for r in conn.execute(sql, params).fetchall()]


def obter(cert_id: int):
    with conectar_banco() as conn:
        row = conn.execute(
            "SELECT c.*,e.razao_social,e.cnpj FROM certificados c JOIN empresas e ON e.id=c.empresa_id WHERE c.id=?",
            (cert_id,),
        ).fetchone()
        if not row:
            raise LookupError("Certificado não encontrado.")
        return _public(dict(row))


def eventos(cert_id: int):
    with conectar_banco() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT ce.id,ce.tipo_evento,ce.descricao,ce.dados,ce.criado_em,u.nome usuario
               FROM certificado_eventos ce LEFT JOIN usuarios u ON u.id=ce.usuario_id
              WHERE ce.certificado_id=? ORDER BY ce.id DESC""", (cert_id,)
        ).fetchall()]


def usos(cert_id: int):
    with conectar_banco() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT modulo,ultima_utilizacao,quantidade_usos,status FROM certificado_uso WHERE certificado_id=? ORDER BY modulo",
            (cert_id,)
        ).fetchall()]


def _check_replace(conn, empresa_id: int, tipo: str, ignore_id: int | None = None):
    sql = "SELECT id FROM certificados WHERE empresa_id=? AND tipo=? AND status='ATIVO'"
    params=[empresa_id,tipo]
    if ignore_id is not None:
        sql += " AND id<>?"; params.append(ignore_id)
    return conn.execute(sql,params).fetchone()


def cadastrar_a1(empresa_id: int, filename: str, data: bytes, password: str, user_id: int) -> dict:
    empresa = _empresa(empresa_id)
    if not empresa:
        raise LookupError("Empresa não encontrada.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"O arquivo excede o limite de {MAX_UPLOAD_MB} MB.")
    meta = _cert_metadata(data, password)
    ok, message = _compatibilidade(empresa, meta["documento_titular"])
    if not ok:
        raise ValueError(message)
    if meta["validity"] == "AINDA_NAO_VALIDO":
        raise ValueError("O certificado ainda não é válido.")
    status = "EXPIRADO" if meta["validity"] == "EXPIRADO" else "ATIVO"
    apto = status == "ATIVO"

    token = secrets.token_hex(24)
    rel = Path(str(empresa_id)) / f"{token}.p12.enc"
    target = _storage_dir() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _encrypt(data)
    temp = target.with_suffix(".tmp")
    temp.write_bytes(encrypted)
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    temp.replace(target)

    with conectar_banco() as conn:
        old = _check_replace(conn, empresa_id, "A1")
        if old:
            conn.execute("UPDATE certificados SET status='INATIVO', apto_para_uso=0, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (old["id"],))
            _evento(conn, old["id"], "SUBSTITUIDO", user_id, "Certificado substituído por um novo certificado A1.")
        cur = conn.execute(
            """INSERT INTO certificados
            (empresa_id,tipo,meio_armazenamento,titular_tipo,nome_titular,documento_titular,emissor,
             numero_serie,thumbprint_sha256,algoritmo,data_emissao,data_validade,status,apto_para_uso,
             storage_ref,arquivo_nome,criado_por)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id,"A1","PFX",meta["titular_tipo"],meta["nome_titular"],meta["documento_titular"],meta["emissor"],
             meta["numero_serie"],meta["thumbprint_sha256"],meta["algoritmo"],meta["data_emissao"],meta["data_validade"],
             status,1 if apto else 0,str(rel),filename,user_id)
        )
        cert_id=cur.lastrowid
        _evento(conn, cert_id, "CADASTRADO", user_id, "Certificado A1 cadastrado e validado.", {
            "arquivo": filename, "thumbprint_sha256": meta["thumbprint_sha256"]
        })
        # Senha cifrada separadamente. Não há coluna plaintext no banco.
        secret_ref = rel.with_suffix(".pwd.enc")
        secret_target = _storage_dir() / secret_ref
        secret_target.write_bytes(_encrypt(password.encode("utf-8")))
        try: os.chmod(secret_target,0o600)
        except OSError: pass
        conn.execute("UPDATE certificados SET storage_ref=? WHERE id=?", (str(rel), cert_id))
        conn.commit()
    return obter(cert_id)


def cadastrar_a3(empresa_id: int, meio: str, titular_tipo: str, documento: str | None, nome_titular: str | None,
                 emissor: str | None, numero_serie: str | None, data_emissao: str | None,
                 data_validade: str | None, algoritmo: str | None, thumbprint_sha256: str | None, dispositivo_modelo: str | None,
                 dispositivo_identificador: str | None, user_id: int) -> dict:
    empresa = _empresa(empresa_id)
    if not empresa:
        raise LookupError("Empresa não encontrada.")
    meio = meio.upper()
    if meio not in {"CARTAO","TOKEN"}:
        raise ValueError("Para A3, o meio deve ser CARTAO ou TOKEN.")
    titular_tipo = titular_tipo.upper()
    document = _normalizar_documento(documento)
    apto = False
    status = "NAO_VINCULADO"
    if titular_tipo == "PJ":
        ok, msg = _compatibilidade(empresa, document)
        if not ok:
            raise ValueError(msg)
        apto = True
        status = "ATIVO"
    elif titular_tipo == "PF":
        # O projeto ainda não possui relação formal de representação PF -> PJ.
        # O certificado pode ser cadastrado como metadado, mas não fica apto a uso.
        apto = False
        status = "NAO_VINCULADO"
    else:
        raise ValueError("Titular inválido. Informe PJ ou PF.")
    with conectar_banco() as conn:
        old = _check_replace(conn, empresa_id, "A3")
        if old:
            conn.execute("UPDATE certificados SET status='INATIVO', apto_para_uso=0, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (old["id"],))
            _evento(conn, old["id"], "SUBSTITUIDO", user_id, "Certificado substituído por um novo certificado A3.")
        cur=conn.execute(
            """INSERT INTO certificados
            (empresa_id,tipo,meio_armazenamento,titular_tipo,nome_titular,documento_titular,emissor,
             numero_serie,thumbprint_sha256,data_emissao,data_validade,algoritmo,status,apto_para_uso,dispositivo_modelo,
             dispositivo_identificador,criado_por)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (empresa_id,"A3",meio,titular_tipo,nome_titular,documento,emissor,numero_serie,thumbprint_sha256,data_emissao,data_validade,
             algoritmo,status,1 if apto else 0,dispositivo_modelo,dispositivo_identificador,user_id)
        )
        cert_id=cur.lastrowid
        _evento(conn,cert_id,"CADASTRADO",user_id,"Identidade A3 cadastrada. A chave privada permanece no dispositivo.",{
            "meio":meio,"titular_tipo":titular_tipo,"apto_para_uso":apto
        })
        conn.commit()
    return obter(cert_id)


def obter_senha_a1(cert_id: int, user_id: int | None = None) -> str:
    """Recover the encrypted A1 password for authorized administrative use.

    The password is never included in normal certificate payloads. This endpoint
    intentionally works for active, inactive and expired A1 certificates so
    archived certificates already registered in OMEGA remain recoverable.
    A3 PINs are never stored and therefore cannot be recovered.
    """
    with conectar_banco() as conn:
        row = conn.execute(
            "SELECT storage_ref, arquivo_nome, tipo, status FROM certificados WHERE id=?",
            (cert_id,),
        ).fetchone()
        if not row:
            raise LookupError("Certificado não encontrado.")
        if row["tipo"] != "A1":
            raise ValueError("Somente certificados A1 possuem senha armazenada.")
        ref = row["storage_ref"]
    if not ref:
        raise ValueError("A senha deste certificado não está disponível.")
    pwd_path = (_storage_dir() / Path(ref)).with_suffix(".pwd.enc")
    if not pwd_path.is_file():
        raise FileNotFoundError("Arquivo criptografado da senha não encontrado.")
    password = _decrypt(pwd_path.read_bytes()).decode("utf-8")
    with conectar_banco() as conn:
        _evento(conn, cert_id, "SENHA_ACESSADA", user_id, "Senha do certificado A1 recuperada por administrador.")
        conn.commit()
    return password


def baixar_a1(cert_id: int, user_id: int | None = None) -> tuple[bytes, str]:
    with conectar_banco() as conn:
        row=conn.execute("SELECT storage_ref,arquivo_nome,tipo FROM certificados WHERE id=?",(cert_id,)).fetchone()
        if not row: raise LookupError("Certificado não encontrado.")
        if row["tipo"]!="A1": raise ValueError("Somente certificados A1 possuem arquivo para download.")
        ref=row["storage_ref"]
    if not ref: raise ValueError("Arquivo do certificado não disponível.")
    path=_storage_dir()/Path(ref)
    if not path.is_file(): raise FileNotFoundError("Arquivo criptografado do certificado não encontrado.")
    data = _decrypt(path.read_bytes())
    with conectar_banco() as conn:
        _evento(conn, cert_id, "DOWNLOAD", user_id, "Arquivo A1 baixado por administrador.")
        conn.commit()
    return data, row["arquivo_nome"] or "certificado.p12"


def testar(cert_id: int, user_id: int | None = None) -> dict:
    with conectar_banco() as conn:
        row=conn.execute("SELECT * FROM certificados WHERE id=?",(cert_id,)).fetchone()
        if not row: raise LookupError("Certificado não encontrado.")
        data=dict(row)
    if data["tipo"]=="A3":
        return {
            "ok": False,
            "tipo":"A3",
            "status":"BRIDGE_NECESSARIO",
            "mensagem":"A3 depende do OMEGA Bridge, leitor/token e middleware PKCS#11. A chave privada não é enviada ao servidor."
        }
    ref=data["storage_ref"]
    path=_storage_dir()/Path(ref)
    pwd_path=path.with_suffix(".pwd.enc")
    if not path.is_file() or not pwd_path.is_file():
        raise ValueError("Credenciais físicas do certificado não estão disponíveis.")
    pfx=_decrypt(path.read_bytes())
    pwd=_decrypt(pwd_path.read_bytes()).decode("utf-8")
    meta=_cert_metadata(pfx,pwd)
    with conectar_banco() as conn:
        _evento(conn,cert_id,"TESTADO",user_id,"Certificado A1 testado com sucesso.")
        conn.commit()
    return {
        "ok": True, "tipo":"A1", "status":"PRONTO",
        "checks":{
            "arquivo_valido":True,"senha_correta":True,"chave_privada_disponivel":True,
            "nao_expirado":meta["validity"]=="ATIVO"
        }
    }


def desativar(cert_id: int, user_id: int):
    with conectar_banco() as conn:
        row=conn.execute("SELECT * FROM certificados WHERE id=?",(cert_id,)).fetchone()
        if not row: raise LookupError("Certificado não encontrado.")
        conn.execute("UPDATE certificados SET status='INATIVO',apto_para_uso=0,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",(cert_id,))
        _evento(conn,cert_id,"DESATIVADO",user_id,"Certificado desativado manualmente.")
        conn.commit()
    return obter(cert_id)


def solicitar_substituicao(cert_id:int,user_id:int):
    with conectar_banco() as conn:
        row=conn.execute("SELECT id FROM certificados WHERE id=?",(cert_id,)).fetchone()
        if not row: raise LookupError("Certificado não encontrado.")
        _evento(conn,cert_id,"SUBSTITUICAO_SOLICITADA",user_id,"Usuário solicitou substituição do certificado.")
        conn.commit()
    return {"ok":True,"mensagem":"Solicitação registrada no histórico."}


def resumo():
    from datetime import date
    hoje = date.today()
    d30 = hoje.toordinal() + 30
    d7 = hoje.toordinal() + 7
    with conectar_banco() as conn:
        total_empresas = conn.execute("SELECT COUNT(*) n FROM empresas WHERE ativo=1").fetchone()["n"]
        rows = conn.execute("SELECT empresa_id,status,data_validade,apto_para_uso FROM certificados").fetchall()
        rows_pf = conn.execute("SELECT pessoa_id,status,data_validade,apto_para_uso FROM certificados_pf").fetchall()
        por_empresa = {}
        por_pessoa = {}
        venc30 = venc7 = vencidos = ativos = 0
        normalized_rows = [dict(r) | {"pessoa_id": None} for r in rows] + [dict(r) | {"empresa_id": None} for r in rows_pf]
        for r in normalized_rows:
            if r["status"] == "INATIVO":
                continue
            try:
                dt = datetime.fromisoformat((r["data_validade"] or "").replace("Z", "+00:00")).date()
            except Exception:
                dt = None
            if dt and dt < hoje:
                vencidos += 1
            elif r["status"] == "ATIVO" and r["apto_para_uso"] and (dt is None or dt >= hoje):
                ativos += 1
            if dt and hoje <= dt <= date.fromordinal(d30):
                venc30 += 1
            if dt and hoje <= dt <= date.fromordinal(d7):
                venc7 += 1
            if r["status"] == "ATIVO" and r["apto_para_uso"] and (dt is None or dt >= hoje):
                if r["empresa_id"] is not None:
                    por_empresa[r["empresa_id"]] = True
                elif r["pessoa_id"] is not None:
                    por_pessoa[r["pessoa_id"]] = True
        sem = conn.execute(
            """SELECT COUNT(*) n FROM empresas e
               WHERE e.ativo=1 AND NOT EXISTS(
                 SELECT 1 FROM certificados c
                  WHERE c.empresa_id=e.id AND c.status='ATIVO' AND c.apto_para_uso=1
               )"""
        ).fetchone()["n"]
        pessoas_ativas = conn.execute("SELECT COUNT(*) n FROM pessoas_fisicas WHERE ativo=1").fetchone()["n"]
        pessoas_sem = conn.execute(
            """SELECT COUNT(*) n FROM pessoas_fisicas p WHERE p.ativo=1 AND NOT EXISTS(
                 SELECT 1 FROM certificados_pf c WHERE c.pessoa_id=p.id AND c.status='ATIVO' AND c.apto_para_uso=1)"""
        ).fetchone()["n"]
        return {"empresas_ativas":total_empresas,"pessoas_fisicas_ativas":pessoas_ativas,
                "certificados_ativos":ativos,"vencem_30_dias":venc30,"vencem_7_dias":venc7,"vencidos":vencidos,
                "empresas_sem_certificado":sem,"pessoas_fisicas_sem_certificado":pessoas_sem}


def registrar_uso(cert_id:int,modulo:str,status="ATIVO"):
    with conectar_banco() as conn:
        conn.execute(
            """INSERT INTO certificado_uso(certificado_id,modulo,ultima_utilizacao,quantidade_usos,status)
               VALUES(?,?,CURRENT_TIMESTAMP,1,?)
               ON CONFLICT(certificado_id,modulo) DO UPDATE SET
               ultima_utilizacao=CURRENT_TIMESTAMP, quantidade_usos=quantidade_usos+1, status=excluded.status""",
            (cert_id,modulo,status)
        )
        conn.commit()

# ---------------------------------------------------------------------------
# Pessoas físicas / certificados PF
# ---------------------------------------------------------------------------

def _pf_public(row: dict) -> dict:
    row = dict(row)
    row.pop("storage_ref", None)
    row.pop("arquivo_nome", None)
    row.pop("criado_por", None)
    row["apto_para_uso"] = bool(row.get("apto_para_uso"))
    row["origem"] = "PF"
    row["empresa_id"] = None
    row["pessoa_id"] = row.get("pessoa_id")
    return row


def _pf_evento(conn, cert_id: int, tipo: str, user_id: int | None, descricao: str, dados: dict | None = None):
    conn.execute(
        "INSERT INTO certificado_pf_eventos(certificado_id,tipo_evento,usuario_id,descricao,dados) VALUES(?,?,?,?,?)",
        (cert_id, tipo, user_id, descricao, json.dumps(dados or {}, ensure_ascii=False, default=str)),
    )


def _cpf(value: str | None) -> str:
    return _normalizar_documento(value)


def _validar_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    total = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (total * 10) % 11
    if d1 == 10:
        d1 = 0
    if d1 != int(cpf[9]):
        return False
    total = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (total * 10) % 11
    if d2 == 10:
        d2 = 0
    return d2 == int(cpf[10])


def _get_or_create_pf(conn, cpf: str, nome: str, email: str | None = None, telefone: str | None = None) -> int:
    cpf = _cpf(cpf)
    if not _validar_cpf(cpf):
        raise ValueError("CPF inválido.")
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome completo da pessoa física.")
    row = conn.execute("SELECT id FROM pessoas_fisicas WHERE cpf=?", (cpf,)).fetchone()
    if row:
        conn.execute(
            "UPDATE pessoas_fisicas SET nome=?, email=COALESCE(?,email), telefone=COALESCE(?,telefone), ativo=1, atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
            (nome, email, telefone, row["id"]),
        )
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO pessoas_fisicas(cpf,nome,email,telefone) VALUES(?,?,?,?)",
        (cpf, nome, email, telefone),
    )
    return int(cur.lastrowid)


def listar_pf():
    with conectar_banco() as conn:
        rows = conn.execute(
            """SELECT c.*, p.cpf, p.nome pessoa_nome, p.email pessoa_email, p.telefone pessoa_telefone
               FROM certificados_pf c JOIN pessoas_fisicas p ON p.id=c.pessoa_id
              WHERE p.ativo=1
              ORDER BY CASE c.status WHEN 'ATIVO' THEN 0 WHEN 'NAO_VINCULADO' THEN 1 WHEN 'EXPIRADO' THEN 2 ELSE 3 END,
                       c.data_validade"""
        ).fetchall()
        result = []
        for r in rows:
            item = _pf_public(dict(r))
            item.update({
                "razao_social": r["pessoa_nome"],
                "cnpj": None,
                "cpf": r["cpf"],
                "pessoa_nome": r["pessoa_nome"],
                "pessoa_email": r["pessoa_email"],
                "pessoa_telefone": r["pessoa_telefone"],
            })
            result.append(item)
        return result


def obter_pf(cert_id: int):
    with conectar_banco() as conn:
        row = conn.execute(
            """SELECT c.*,p.cpf,p.nome pessoa_nome,p.email pessoa_email,p.telefone pessoa_telefone
               FROM certificados_pf c JOIN pessoas_fisicas p ON p.id=c.pessoa_id WHERE c.id=?""",
            (cert_id,),
        ).fetchone()
        if not row:
            raise LookupError("Certificado PF não encontrado.")
        item = _pf_public(dict(row))
        item.update({"razao_social": row["pessoa_nome"], "cnpj": None, "cpf": row["cpf"], "pessoa_nome": row["pessoa_nome"]})
        return item


def eventos_pf(cert_id: int):
    with conectar_banco() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT ce.id,ce.tipo_evento,ce.descricao,ce.dados,ce.criado_em,u.nome usuario
               FROM certificado_pf_eventos ce LEFT JOIN usuarios u ON u.id=ce.usuario_id
              WHERE ce.certificado_id=? ORDER BY ce.id DESC""", (cert_id,)
        ).fetchall()]


def usos_pf(cert_id: int):
    with conectar_banco() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT modulo,ultima_utilizacao,quantidade_usos,status FROM certificado_pf_uso WHERE certificado_id=? ORDER BY modulo",
            (cert_id,)
        ).fetchall()]


def _check_replace_pf(conn, pessoa_id: int, tipo: str):
    return conn.execute(
        "SELECT id FROM certificados_pf WHERE pessoa_id=? AND tipo=? AND status='ATIVO'",
        (pessoa_id, tipo),
    ).fetchone()


def cadastrar_pf_a1(cpf: str, nome: str, filename: str, data: bytes, password: str, user_id: int,
                    email: str | None = None, telefone: str | None = None) -> dict:
    cpf = _cpf(cpf)
    if not _validar_cpf(cpf):
        raise ValueError("CPF inválido.")
    meta = _cert_metadata(data, password)
    if meta["documento_titular"] != cpf:
        raise ValueError(f"Certificado incompatível: o CPF {meta['documento_titular'] or 'não identificado'} não corresponde ao CPF informado {cpf}.")
    if meta["titular_tipo"] != "PF":
        raise ValueError("O arquivo informado não foi identificado como certificado de pessoa física.")
    if meta["validity"] == "AINDA_NAO_VALIDO":
        raise ValueError("O certificado ainda não é válido.")
    status = "EXPIRADO" if meta["validity"] == "EXPIRADO" else "ATIVO"
    apto = status == "ATIVO"

    token = secrets.token_hex(24)
    rel = Path("pf") / str(cpf) / f"{token}.p12.enc"
    target = _storage_dir() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_encrypt(data))
    try: os.chmod(target, 0o600)
    except OSError: pass
    pwd_target = (_storage_dir() / rel).with_suffix(".pwd.enc")
    pwd_target.write_bytes(_encrypt(password.encode("utf-8")))
    try: os.chmod(pwd_target, 0o600)
    except OSError: pass

    with conectar_banco() as conn:
        pessoa_id = _get_or_create_pf(conn, cpf, nome, email, telefone)
        old = _check_replace_pf(conn, pessoa_id, "A1")
        if old:
            conn.execute("UPDATE certificados_pf SET status='INATIVO',apto_para_uso=0,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (old["id"],))
            _pf_evento(conn, old["id"], "SUBSTITUIDO", user_id, "Certificado PF A1 substituído por novo certificado.")
        cur = conn.execute(
            """INSERT INTO certificados_pf
            (pessoa_id,tipo,meio_armazenamento,nome_titular,documento_titular,emissor,numero_serie,thumbprint_sha256,algoritmo,
             data_emissao,data_validade,status,apto_para_uso,storage_ref,arquivo_nome,criado_por)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pessoa_id,"A1","PFX",meta["nome_titular"] or nome,cpf,meta["emissor"],meta["numero_serie"],meta["thumbprint_sha256"],meta["algoritmo"],
             meta["data_emissao"],meta["data_validade"],status,1 if apto else 0,str(rel),filename,user_id),
        )
        cert_id = int(cur.lastrowid)
        _pf_evento(conn, cert_id, "CADASTRADO", user_id, "Certificado A1 de pessoa física cadastrado e validado.", {"thumbprint_sha256": meta["thumbprint_sha256"]})
        conn.commit()
    return obter_pf(cert_id)


def cadastrar_pf_a3(cpf: str, nome: str, meio: str, emissor: str | None, numero_serie: str | None,
                    data_emissao: str | None, data_validade: str | None, algoritmo: str | None,
                    thumbprint_sha256: str | None, dispositivo_modelo: str | None,
                    dispositivo_identificador: str | None, user_id: int,
                    email: str | None = None, telefone: str | None = None) -> dict:
    cpf = _cpf(cpf)
    if not _validar_cpf(cpf):
        raise ValueError("CPF inválido.")
    meio = meio.upper()
    if meio not in {"CARTAO", "TOKEN"}:
        raise ValueError("Para A3, o meio deve ser CARTAO ou TOKEN.")
    with conectar_banco() as conn:
        pessoa_id = _get_or_create_pf(conn, cpf, nome, email, telefone)
        old = _check_replace_pf(conn, pessoa_id, "A3")
        if old:
            conn.execute("UPDATE certificados_pf SET status='INATIVO',apto_para_uso=0,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (old["id"],))
            _pf_evento(conn, old["id"], "SUBSTITUIDO", user_id, "Certificado PF A3 substituído por novo certificado.")
        status = "ATIVO"
        apto = True
        if data_validade:
            try:
                dt = datetime.fromisoformat(data_validade.replace("Z", "+00:00"))
                if dt.date() < datetime.now(timezone.utc).date():
                    status, apto = "EXPIRADO", False
            except Exception:
                pass
        cur = conn.execute(
            """INSERT INTO certificados_pf
            (pessoa_id,tipo,meio_armazenamento,nome_titular,documento_titular,emissor,numero_serie,thumbprint_sha256,algoritmo,
             data_emissao,data_validade,status,apto_para_uso,dispositivo_modelo,dispositivo_identificador,criado_por)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pessoa_id,"A3",meio,nome,cpf,emissor,numero_serie,thumbprint_sha256,algoritmo,data_emissao,data_validade,status,1 if apto else 0,
             dispositivo_modelo,dispositivo_identificador,user_id),
        )
        cert_id = int(cur.lastrowid)
        _pf_evento(conn, cert_id, "CADASTRADO", user_id, "Identidade A3 de pessoa física cadastrada. A chave privada permanece no dispositivo.", {"meio": meio})
        conn.commit()
    return obter_pf(cert_id)


def obter_senha_pf_a1(cert_id: int, user_id: int | None = None) -> str:
    with conectar_banco() as conn:
        row = conn.execute("SELECT storage_ref,tipo FROM certificados_pf WHERE id=?", (cert_id,)).fetchone()
        if not row:
            raise LookupError("Certificado PF não encontrado.")
        if row["tipo"] != "A1":
            raise ValueError("Somente certificados A1 possuem senha armazenada.")
        ref = row["storage_ref"]
    if not ref:
        raise ValueError("A senha deste certificado não está disponível.")
    path = (_storage_dir() / Path(ref)).with_suffix(".pwd.enc")
    if not path.is_file():
        raise FileNotFoundError("Arquivo criptografado da senha não encontrado.")
    password = _decrypt(path.read_bytes()).decode("utf-8")
    with conectar_banco() as conn:
        _pf_evento(conn, cert_id, "SENHA_ACESSADA", user_id, "Senha do certificado PF A1 recuperada por administrador.")
        conn.commit()
    return password


def baixar_pf_a1(cert_id: int, user_id: int | None = None) -> tuple[bytes, str]:
    with conectar_banco() as conn:
        row = conn.execute("SELECT storage_ref,arquivo_nome,tipo FROM certificados_pf WHERE id=?", (cert_id,)).fetchone()
        if not row:
            raise LookupError("Certificado PF não encontrado.")
        if row["tipo"] != "A1":
            raise ValueError("Somente certificados A1 possuem arquivo para download.")
        ref = row["storage_ref"]
    if not ref:
        raise ValueError("Arquivo do certificado não disponível.")
    path = _storage_dir() / Path(ref)
    if not path.is_file():
        raise FileNotFoundError("Arquivo criptografado do certificado não encontrado.")
    data = _decrypt(path.read_bytes())
    with conectar_banco() as conn:
        _pf_evento(conn, cert_id, "DOWNLOAD", user_id, "Arquivo A1 PF baixado por administrador.")
        conn.commit()
    return data, row["arquivo_nome"] or "certificado.p12"


def testar_pf(cert_id: int, user_id: int | None = None) -> dict:
    with conectar_banco() as conn:
        row = conn.execute("SELECT * FROM certificados_pf WHERE id=?", (cert_id,)).fetchone()
        if not row:
            raise LookupError("Certificado PF não encontrado.")
        data = dict(row)
    if data["tipo"] == "A3":
        return {"ok": False, "tipo": "A3", "status": "BRIDGE_NECESSARIO", "mensagem": "A3 depende do OMEGA Bridge, leitor/token e middleware PKCS#11."}
    ref = data["storage_ref"]
    path = _storage_dir() / Path(ref)
    pwd_path = path.with_suffix(".pwd.enc")
    if not path.is_file() or not pwd_path.is_file():
        raise ValueError("Credenciais físicas do certificado PF não estão disponíveis.")
    _cert_metadata(_decrypt(path.read_bytes()), _decrypt(pwd_path.read_bytes()).decode("utf-8"))
    with conectar_banco() as conn:
        _pf_evento(conn, cert_id, "TESTADO", user_id, "Certificado PF A1 testado com sucesso.")
        conn.commit()
    return {"ok": True, "tipo": "A1", "status": "PRONTO"}


def desativar_pf(cert_id: int, user_id: int):
    with conectar_banco() as conn:
        row = conn.execute("SELECT id FROM certificados_pf WHERE id=?", (cert_id,)).fetchone()
        if not row:
            raise LookupError("Certificado PF não encontrado.")
        conn.execute("UPDATE certificados_pf SET status='INATIVO',apto_para_uso=0,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (cert_id,))
        _pf_evento(conn, cert_id, "DESATIVADO", user_id, "Certificado PF desativado manualmente.")
        conn.commit()
    return obter_pf(cert_id)


def solicitar_substituicao_pf(cert_id: int, user_id: int):
    with conectar_banco() as conn:
        row = conn.execute("SELECT id FROM certificados_pf WHERE id=?", (cert_id,)).fetchone()
        if not row:
            raise LookupError("Certificado PF não encontrado.")
        _pf_evento(conn, cert_id, "SUBSTITUICAO_SOLICITADA", user_id, "Usuário solicitou substituição do certificado PF.")
        conn.commit()
    return {"ok": True, "mensagem": "Solicitação registrada no histórico."}


def registrar_uso_pf(cert_id: int, modulo: str, status: str = "ATIVO"):
    with conectar_banco() as conn:
        conn.execute(
            """INSERT INTO certificado_pf_uso(certificado_id,modulo,ultima_utilizacao,quantidade_usos,status)
               VALUES(?,?,CURRENT_TIMESTAMP,1,?)
               ON CONFLICT(certificado_id,modulo) DO UPDATE SET
               ultima_utilizacao=CURRENT_TIMESTAMP,quantidade_usos=quantidade_usos+1,status=excluded.status""",
            (cert_id, modulo, status),
        )
        conn.commit()
