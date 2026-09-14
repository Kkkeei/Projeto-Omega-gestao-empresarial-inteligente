import asyncio
import hashlib
import json
import os
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.db.database import conectar_banco, backup_banco_permanente
from app.services.sefaz_pe_service import executar_consulta_playwright, limpar_cnpj, formatar_cnpj

BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR.parent / "storage" / "certidoes" / "estadual"


def _tipo_estadual_id(conexao):
    row = conexao.execute(
        "SELECT id FROM tipos_certidao WHERE nome = ? AND ativo = 1",
        ("Estadual - SEFAZ",),
    ).fetchone()
    if not row:
        raise LookupError("Tipo de certidão Estadual - SEFAZ não cadastrado.")
    return row["id"]


def _validade_status(data_validade: str | None) -> str | None:
    if not data_validade:
        return None
    try:
        validade = date.fromisoformat(data_validade)
    except (TypeError, ValueError):
        return None
    hoje = date.today()
    if validade < hoje:
        return "VENCIDA"
    if (validade - hoje).days <= 30:
        return "PRÓXIMA DO VENCIMENTO"
    return "VÁLIDA"


def listar(empresa_id: int | None = None):
    conexao = conectar_banco()
    try:
        sql = """
            SELECT c.*, t.nome AS tipo_certidao, e.cnpj, e.razao_social,
                   (SELECT cc.pdf_path FROM consultas_certidoes cc
                      WHERE cc.certidao_id = c.id ORDER BY cc.id DESC LIMIT 1) AS pdf_path,
                   (SELECT cc.pendencia FROM consultas_certidoes cc
                      WHERE cc.certidao_id = c.id ORDER BY cc.id DESC LIMIT 1) AS pendencia,
                   (SELECT cc.pendencia_detalhes FROM consultas_certidoes cc
                      WHERE cc.certidao_id = c.id ORDER BY cc.id DESC LIMIT 1) AS pendencia_detalhes,
                   (SELECT cc.nome_arquivo_original FROM consultas_certidoes cc
                      WHERE cc.certidao_id = c.id ORDER BY cc.id DESC LIMIT 1) AS nome_arquivo_original,
                   (SELECT cc.texto_extraido FROM consultas_certidoes cc
                      WHERE cc.certidao_id = c.id ORDER BY cc.id DESC LIMIT 1) AS texto_extraido
            FROM certidoes c
            JOIN tipos_certidao t ON t.id = c.tipo_certidao_id
            JOIN empresas e ON e.id = c.empresa_id
            WHERE 1=1
        """
        params = []
        if empresa_id is not None:
            sql += " AND c.empresa_id = ?"
            params.append(empresa_id)
        sql += " ORDER BY c.atualizada_em DESC, c.id DESC"
        resultado = []
        for row in conexao.execute(sql, params).fetchall():
            item = dict(row)
            item["status_validade"] = _validade_status(item.get("data_validade"))
            item["situacao_calculada"] = item["situacao"]
            resultado.append(item)
        return resultado
    finally:
        conexao.close()


def tipos():
    conexao = conectar_banco()
    try:
        return [dict(r) for r in conexao.execute(
            "SELECT * FROM tipos_certidao WHERE ativo = 1 ORDER BY nome"
        ).fetchall()]
    finally:
        conexao.close()


def historico(empresa_id: int, tipo_certidao_id: int | None = None):
    """Lê exclusivamente o livro histórico imutável das certidões."""
    conexao = conectar_banco()
    try:
        sql = """
            SELECT ch.*, t.nome AS tipo_certidao, e.cnpj, e.razao_social
              FROM certidoes_historico ch
              JOIN tipos_certidao t ON t.id = ch.tipo_certidao_id
              JOIN empresas e ON e.id = ch.empresa_id
             WHERE ch.empresa_id = ?
        """
        params = [empresa_id]
        if tipo_certidao_id is not None:
            sql += " AND ch.tipo_certidao_id = ?"
            params.append(tipo_certidao_id)
        sql += " ORDER BY ch.id DESC"
        resultado = []
        for row in conexao.execute(sql, params).fetchall():
            item = dict(row)
            item["status_validade"] = _validade_status(item.get("data_validade"))
            resultado.append(item)
        return resultado
    finally:
        conexao.close()


def _salvar_documento(conexao, empresa_id: int, pdf_origem: str, nome_original: str, *, subpasta: str = "estadual", documento_tipo: str = "CERTIDAO_ESTADUAL_SEFAZ_PE", descricao: str = "Certidão de Regularidade Fiscal da SEFAZ Pernambuco", origem: str = "SEFAZ-PE") -> tuple[int, str]:
    empresa = conexao.execute(
        "SELECT cnpj FROM empresas WHERE id = ?", (empresa_id,)
    ).fetchone()
    if not empresa:
        raise LookupError("Empresa não encontrada ao salvar a certidão.")

    agora = datetime.now()
    cnpj = limpar_cnpj(empresa["cnpj"])
    pasta = BASE_DIR.parent / "storage" / "certidoes" / subpasta / cnpj / str(agora.year)
    pasta.mkdir(parents=True, exist_ok=True)

    # Inclui microssegundos para impedir colisão quando várias consultas
    # terminarem no mesmo segundo.
    destino = pasta / f"certidao_{agora.strftime('%Y-%m-%d_%H%M%S_%f')}.pdf"
    caminho_relativo = str(destino.resolve().relative_to(BASE_DIR.parent.resolve()))
    try:
        shutil.copyfile(pdf_origem, destino)
        tamanho = destino.stat().st_size
        digest = hashlib.sha256(destino.read_bytes()).hexdigest()
    except Exception:
        try:
            destino.unlink(missing_ok=True)
        except Exception:
            pass
        raise

    doc = conexao.execute(
        "SELECT id FROM documentos WHERE empresa_id = ? AND tipo = ? ORDER BY id DESC LIMIT 1",
        (empresa_id, documento_tipo),
    ).fetchone()
    if doc:
        documento_id = doc["id"]
        row = conexao.execute(
            "SELECT COALESCE(MAX(versao), 0) + 1 AS v FROM documento_versoes WHERE documento_id = ?",
            (documento_id,),
        ).fetchone()
        versao = row["v"]
    else:
        cur = conexao.execute(
            "INSERT INTO documentos (empresa_id,tipo,nome,descricao,categoria,origem) VALUES (?,?,?,?,?,?)",
            (
                empresa_id,
                documento_tipo,
                documento_tipo,
                descricao,
                "CERTIDOES",
                origem,
            ),
        )
        documento_id = cur.lastrowid
        versao = 1

    conexao.execute(
        """
        INSERT INTO documento_versoes
        (documento_id,versao,nome_arquivo,caminho_arquivo,extensao,tamanho,hash_arquivo,origem)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            documento_id,
            versao,
            nome_original,
            caminho_relativo,
            ".pdf",
            tamanho,
            digest,
            origem,
        ),
    )
    return documento_id, caminho_relativo


def _registrar_resultado(conexao, empresa_id: int, tipo_id: int, resultado: dict, *, origem: str = "SEFAZ-PE"):
    situacao = resultado.get("situacao") or "ERRO"
    pdf_path = resultado.get("pdf_path")
    documento_id = resultado.get("documento_id")

    # O registro ATUAL da certidão deve existir para toda consulta concluída
    # e também para falhas técnicas. Ele representa o último estado conhecido.
    # O histórico permanente fica separado em certidoes_historico e nunca é
    # atualizado. Portanto, uma nova consulta atualiza apenas esta fotografia.
    atual = conexao.execute(
        "SELECT id FROM certidoes WHERE empresa_id = ? AND tipo_certidao_id = ?",
        (empresa_id, tipo_id),
    ).fetchone()
    cert_id = atual["id"] if atual else None

    if atual:
        conexao.execute(
            """
            UPDATE certidoes
               SET situacao=?, numero_certidao=?, data_emissao=?, data_validade=?,
                   documento_id=COALESCE(?, documento_id), origem=?, observacao=?,
                   atualizada_em=CURRENT_TIMESTAMP
             WHERE id=?
            """,
            (
                situacao,
                resultado.get("numero_certidao"),
                resultado.get("data_emissao"),
                resultado.get("data_validade"),
                documento_id,
                origem,
                resultado.get("pendencia_detalhes") or resultado.get("mensagem"),
                cert_id,
            ),
        )
    else:
        cur = conexao.execute(
            """
            INSERT INTO certidoes
            (empresa_id,tipo_certidao_id,situacao,numero_certidao,data_emissao,data_validade,documento_id,origem,observacao)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                empresa_id,
                tipo_id,
                situacao,
                resultado.get("numero_certidao"),
                resultado.get("data_emissao"),
                resultado.get("data_validade"),
                documento_id,
                origem,
                resultado.get("pendencia_detalhes") or resultado.get("mensagem"),
            ),
        )
        cert_id = cur.lastrowid

    cur_consulta = conexao.execute(
        """
        INSERT INTO consultas_certidoes
        (empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,data_emissao,data_validade,
         pdf_path,origem,mensagem,pendencia,pendencia_detalhes,nome_arquivo_original,status_processamento,erro_tecnico,texto_extraido)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            empresa_id,
            tipo_id,
            cert_id,
            situacao,
            resultado.get("numero_certidao"),
            resultado.get("data_emissao"),
            resultado.get("data_validade"),
            pdf_path,
            origem,
            resultado.get("mensagem"),
            1 if resultado.get("pendencia") else 0,
            resultado.get("pendencia_detalhes"),
            resultado.get("nome_original_arquivo"),
            resultado.get("status_processamento"),
            resultado.get("erro_tecnico") or (resultado.get("mensagem") if situacao == "ERRO" else None),
            resultado.get("texto_extraido"),
        ),
    )
    consulta_id = cur_consulta.lastrowid

    # Snapshot permanente: a certidão atual pode mudar, mas esta fotografia
    # nunca é atualizada nem substituída.
    hash_arquivo = None
    if documento_id:
        row_hash = conexao.execute(
            "SELECT hash_arquivo FROM documento_versoes WHERE documento_id=? ORDER BY versao DESC LIMIT 1",
            (documento_id,),
        ).fetchone()
        hash_arquivo = row_hash["hash_arquivo"] if row_hash else None
    conexao.execute(
        """
        INSERT INTO certidoes_historico
        (consulta_id,empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,
         data_emissao,data_validade,pdf_path,documento_id,hash_arquivo,nome_arquivo_original,
         status_processamento,erro_tecnico,mensagem,texto_extraido,consultado_em)
        SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,consultado_em
          FROM consultas_certidoes
         WHERE id=?
        """,
        (
            consulta_id, empresa_id, tipo_id, cert_id, situacao,
            resultado.get("numero_certidao"), resultado.get("data_emissao"),
            resultado.get("data_validade"), pdf_path, documento_id, hash_arquivo,
            resultado.get("nome_original_arquivo"), resultado.get("status_processamento"),
            resultado.get("erro_tecnico") or (resultado.get("mensagem") if situacao == "ERRO" else None),
            resultado.get("mensagem"), resultado.get("texto_extraido"), consulta_id,
        ),
    )
    resultado["consulta_id"] = consulta_id
    return cert_id


def _registrar_pendencia(conexao, empresa_id: int, resultado: dict) -> None:
    situacao = resultado.get("situacao")
    tipo = "CERTIDAO_ESTADUAL"
    titulo = "Irregularidade fiscal estadual - SEFAZ-PE"

    if situacao == "IRREGULAR":
        descricao = resultado.get("pendencia_detalhes") or (
            "A Certidão Estadual da SEFAZ-PE indica irregularidade. "
            "Consulte o PDF armazenado para os detalhes."
        )
        aberta = conexao.execute(
            """
            SELECT id FROM pendencias
             WHERE empresa_id=? AND tipo=? AND titulo=? AND status <> 'RESOLVIDA'
             ORDER BY id DESC LIMIT 1
            """,
            (empresa_id, tipo, titulo),
        ).fetchone()
        if aberta:
            conexao.execute(
                "UPDATE pendencias SET descricao=?, prioridade='ALTA', atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                (descricao, aberta["id"]),
            )
        else:
            conexao.execute(
                """
                INSERT INTO pendencias
                (empresa_id,tipo,origem,titulo,descricao,status,prioridade,data_identificacao)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (empresa_id, tipo, "SEFAZ-PE", titulo, descricao, "ABERTA", "ALTA", date.today().isoformat()),
            )
    elif situacao in {"REGULAR", "POSITIVA COM EFEITOS DE NEGATIVA"}:
        conexao.execute(
            """
            UPDATE pendencias
               SET status='RESOLVIDA', data_resolucao=?, atualizado_em=CURRENT_TIMESTAMP
             WHERE empresa_id=? AND tipo=? AND status <> 'RESOLVIDA'
            """,
            (date.today().isoformat(), empresa_id, tipo),
        )


def _registrar_execucao(conexao, empresa_id: int, resultado: dict) -> None:
    automacao = conexao.execute(
        "SELECT id FROM automacoes WHERE tipo='CONSULTA_CERTIDAO_ESTADUAL' AND ativo=1 ORDER BY id LIMIT 1"
    ).fetchone()
    conexao.execute(
        """
        INSERT INTO execucoes_automacao
        (automacao_id,empresa_id,tipo,status,fim,mensagem,erro_tecnico,resultado,origem)
        VALUES (?,?,?,?,CURRENT_TIMESTAMP,?,?,?,?)
        """,
        (
            automacao["id"] if automacao else None,
            empresa_id,
            "CONSULTA_CERTIDAO_ESTADUAL",
            resultado.get("status_processamento") or "ERRO",
            resultado.get("mensagem"),
            resultado.get("erro_tecnico") or (resultado.get("mensagem") if resultado.get("situacao") == "ERRO" else None),
            json.dumps(
                {
                    "situacao": resultado.get("situacao"),
                    "pdf_path": resultado.get("pdf_path"),
                    "pendencia": resultado.get("pendencia", False),
                    "pendencia_detalhes": resultado.get("pendencia_detalhes"),
                },
                ensure_ascii=False,
            ),
            "SEFAZ-PE",
        ),
    )


def _normalizar_resultado_final(resultado: dict) -> dict:
    resultado = dict(resultado or {})
    if resultado.get("situacao") == "NAO IDENTIFICADO":
        resultado["situacao"] = "AGUARDANDO_INTERVENCAO"
        resultado["status_processamento"] = "Aguardando intervenção"
        resultado.setdefault("mensagem", "PDF obtido, mas a situação fiscal não pôde ser identificada com segurança.")
    else:
        msg = (resultado.get("mensagem") or "").upper()
        if resultado.get("status_processamento") != "Sucesso" and any(
            x in msg for x in ("BOTÃO EMITIR", "LAYOUT", "CAPTCHA", "BLOQUEIO", "PDF INVÁLIDO", "PDF NÃO")
        ):
            resultado["situacao"] = "AGUARDANDO_INTERVENCAO"
            resultado["status_processamento"] = "Aguardando intervenção"
    return resultado


def _registrar_falha_empresa(empresa_id: int, mensagem: str) -> dict:
    """Registra falha estrutural mesmo quando a consulta não chegou ao fluxo normal."""
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT cnpj, razao_social FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        tipo_id = _tipo_estadual_id(conexao)
        resultado = {
            "cnpj": empresa["cnpj"],
            "empresa": empresa["razao_social"],
            "situacao": "ERRO",
            "tipo_certidao": "Estadual - SEFAZ",
            "status_processamento": "Erro",
            "mensagem": mensagem,
            "erro_tecnico": mensagem,
            "pendencia": False,
            "pendencia_detalhes": None,
            "pdf_path": None,
            "documento_id": None,
        }
        cert_id = _registrar_resultado(conexao, empresa_id, tipo_id, resultado)
        _registrar_execucao(conexao, empresa_id, resultado)
        conexao.commit()
        backup_banco_permanente()
        return {
            "empresa_id": empresa_id,
            "empresa": empresa["razao_social"],
            "cnpj": formatar_cnpj(empresa["cnpj"]),
            "situacao": "ERRO",
            "tipo_certidao": "Estadual - SEFAZ",
            "status_processamento": "Erro",
            "mensagem": mensagem,
            "erro_tecnico": mensagem,
            "consulta_registrada": True,
            "certidao_id": cert_id,
        }
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


async def _consultar_empresa(empresa_id: int, tentativas: int = 3, browser=None) -> dict:
    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT * FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        tipo_id = _tipo_estadual_id(conexao)
        cnpj = empresa["cnpj"]
        razao_cadastrada = empresa["razao_social"]
    finally:
        conexao.close()

    ultimo = None
    for tentativa in range(1, max(1, tentativas) + 1):
        try:
            ultimo = await executar_consulta_playwright(cnpj, browser=browser)
        except Exception as exc:
            ultimo = {
                "cnpj": cnpj,
                "cnpj_formatado": formatar_cnpj(cnpj),
                "empresa": razao_cadastrada,
                "situacao": "ERRO",
                "tipo_certidao": None,
                "status_processamento": "Erro",
                "mensagem": str(exc),
                "erro_tecnico": str(exc),
                "pendencia": False,
                "pendencia_detalhes": None,
            }
        if ultimo.get("status_processamento") == "Sucesso":
            break
        if tentativa < max(1, tentativas):
            await asyncio.sleep(3 * tentativa)

    ultimo = _normalizar_resultado_final(ultimo or {
        "cnpj": cnpj,
        "situacao": "ERRO",
        "status_processamento": "Erro",
        "mensagem": "Não foi possível executar a consulta.",
    })

    conexao = conectar_banco()
    try:
        # Se o PDF existe, tenta preservá-lo antes de registrar o resultado.
        # Falha no armazenamento não pode apagar o histórico da consulta.
        if ultimo.get("arquivo_pdf") and os.path.isfile(ultimo["arquivo_pdf"]):
            try:
                documento_id, pdf_path = _salvar_documento(
                    conexao,
                    empresa_id,
                    ultimo["arquivo_pdf"],
                    ultimo.get("nome_original_arquivo") or "certidao.pdf",
                )
                ultimo["documento_id"] = documento_id
                ultimo["pdf_path"] = pdf_path
            except Exception as exc:
                ultimo["documento_id"] = None
                ultimo["pdf_path"] = None
                ultimo["erro_tecnico"] = f"Falha ao armazenar PDF: {exc}"
                if ultimo.get("situacao") in {"REGULAR", "POSITIVA COM EFEITOS DE NEGATIVA", "IRREGULAR"}:
                    ultimo["mensagem"] = (
                        (ultimo.get("mensagem") or "Consulta concluída.")
                        + " PDF obtido, mas não foi possível armazená-lo no sistema."
                    )
        else:
            ultimo["pdf_path"] = None
            ultimo["documento_id"] = None

        cert_id = _registrar_resultado(conexao, empresa_id, tipo_id, ultimo)
        _registrar_pendencia(conexao, empresa_id, ultimo)
        _registrar_execucao(conexao, empresa_id, ultimo)
        conexao.commit()
        backup_banco_permanente()

        current = conexao.execute(
            """
            SELECT c.*, t.nome AS tipo_certidao
              FROM certidoes c
              JOIN tipos_certidao t ON t.id=c.tipo_certidao_id
             WHERE c.empresa_id=? AND c.tipo_certidao_id=?
            """,
            (empresa_id, tipo_id),
        ).fetchone()
        resposta = dict(current) if current else {}
        resposta.update({
            "empresa_id": empresa_id,
            "empresa": ultimo.get("empresa") or razao_cadastrada,
            "cnpj": formatar_cnpj(cnpj),
            "situacao": ultimo.get("situacao"),
            "tipo_certidao": ultimo.get("tipo_certidao") or "Estadual - SEFAZ",
            "data_emissao": ultimo.get("data_emissao"),
            "data_validade": ultimo.get("data_validade"),
            "pendencia": bool(ultimo.get("pendencia")),
            "pendencia_detalhes": ultimo.get("pendencia_detalhes"),
            "pdf_path": ultimo.get("pdf_path"),
            "nome_arquivo_original": ultimo.get("nome_original_arquivo"),
            "status_processamento": ultimo.get("status_processamento"),
            "mensagem": ultimo.get("mensagem"),
            "erro_tecnico": ultimo.get("erro_tecnico"),
            "consulta_registrada": True,
            "certidao_id": cert_id,
            "consulta_id": ultimo.get("consulta_id"),
        })
        return resposta
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()



def _tipo_narrativa_id(conexao):
    row = conexao.execute(
        "SELECT id FROM tipos_certidao WHERE nome = ? AND ativo = 1",
        ("Narrativa de Débito Fiscal - SEFAZ",),
    ).fetchone()
    if not row:
        raise LookupError("Tipo de certidão Narrativa de Débito Fiscal - SEFAZ não cadastrado.")
    return row["id"]


def consultar_narrativa_pyautogui(empresa_id: int, certificado_nome: str | None = None) -> dict:
    """Executa a automação visual e persiste a leitura textual do documento."""
    from app.services.sefaz_narrativa_pyautogui import executar_automacao_pyautogui

    conexao = conectar_banco()
    try:
        empresa = conexao.execute("SELECT * FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        if not empresa:
            raise LookupError("Empresa não encontrada.")
        tipo_id = _tipo_narrativa_id(conexao)
        cnpj = empresa["cnpj"]
        razao = empresa["razao_social"]
    finally:
        conexao.close()

    try:
        resultado = executar_automacao_pyautogui(cnpj, certificado_nome=certificado_nome)
    except Exception as exc:
        resultado = {
            "cnpj": cnpj,
            "empresa": razao,
            "situacao": "ERRO",
            "tipo_certidao": "Narrativa de Débito Fiscal - SEFAZ",
            "status_processamento": "Erro",
            "mensagem": str(exc),
            "erro_tecnico": str(exc),
            "pendencia": False,
        }

    conexao = conectar_banco()
    try:
        # Esta automação lê o documento diretamente do navegador; ainda assim,
        # deixamos a estrutura pronta para PDF futuro sem perder a consulta.
        if resultado.get("arquivo_pdf") and os.path.isfile(resultado["arquivo_pdf"]):
            try:
                documento_id, pdf_path = _salvar_documento(
                    conexao, empresa_id, resultado["arquivo_pdf"],
                    resultado.get("nome_original_arquivo") or "CertidaoNarrativa.pdf",
                    subpasta="narrativa",
                    documento_tipo="CERTIDAO_NARRATIVA_SEFAZ_PE",
                    descricao="Certidão Negativa/Narrativa de Débito Fiscal da SEFAZ Pernambuco",
                    origem="SEFAZ-PE",
                )
                resultado["documento_id"] = documento_id
                resultado["pdf_path"] = pdf_path
            except Exception as exc:
                resultado["erro_tecnico"] = f"Falha ao armazenar PDF: {exc}"
        else:
            resultado["documento_id"] = None
            resultado["pdf_path"] = None

        cert_id = _registrar_resultado(
            conexao, empresa_id, tipo_id, resultado, origem="SEFAZ-PE / PYAutoGUI"
        )
        _registrar_execucao_narrativa(conexao, empresa_id, resultado)
        if resultado.get("situacao") == "IRREGULAR":
            _registrar_pendencia_narrativa(conexao, empresa_id, resultado)
        conexao.commit()
        backup_banco_permanente()

        resposta = dict(conexao.execute(
            """SELECT c.*, t.nome AS tipo_certidao FROM certidoes c
               JOIN tipos_certidao t ON t.id=c.tipo_certidao_id
              WHERE c.empresa_id=? AND c.tipo_certidao_id=?""",
            (empresa_id, tipo_id),
        ).fetchone())
        resposta.update({
            "empresa_id": empresa_id,
            "empresa": razao,
            "cnpj": formatar_cnpj(cnpj),
            "situacao": resultado.get("situacao"),
            "tipo_certidao": "Narrativa de Débito Fiscal - SEFAZ",
            "numero_certidao": resultado.get("numero_certidao"),
            "data_emissao": resultado.get("data_emissao"),
            "data_validade": resultado.get("data_validade"),
            "pendencia": bool(resultado.get("pendencia")),
            "pendencia_detalhes": resultado.get("pendencia_detalhes"),
            "pdf_path": resultado.get("pdf_path"),
            "nome_arquivo_original": resultado.get("nome_original_arquivo"),
            "status_processamento": resultado.get("status_processamento"),
            "mensagem": resultado.get("mensagem"),
            "erro_tecnico": resultado.get("erro_tecnico"),
            "texto_extraido": resultado.get("texto_extraido"),
            "consulta_registrada": True,
            "certidao_id": cert_id,
            "consulta_id": resultado.get("consulta_id"),
        })
        return resposta
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _registrar_execucao_narrativa(conexao, empresa_id: int, resultado: dict) -> None:
    automacao = conexao.execute(
        "SELECT id FROM automacoes WHERE tipo='CONSULTA_CERTIDAO_NARRATIVA' AND ativo=1 ORDER BY id LIMIT 1"
    ).fetchone()
    conexao.execute(
        """INSERT INTO execucoes_automacao
           (automacao_id,empresa_id,tipo,status,fim,mensagem,erro_tecnico,resultado,origem)
           VALUES (?,?,?,?,CURRENT_TIMESTAMP,?,?,?,?)""",
        (
            automacao["id"] if automacao else None,
            empresa_id,
            "CONSULTA_CERTIDAO_NARRATIVA",
            resultado.get("status_processamento") or "Erro",
            resultado.get("mensagem"),
            resultado.get("erro_tecnico"),
            json.dumps({
                "situacao": resultado.get("situacao"),
                "pdf_path": resultado.get("pdf_path"),
                "texto_extraido": bool(resultado.get("texto_extraido")),
            }, ensure_ascii=False),
            "SEFAZ-PE / PYAutoGUI",
        ),
    )


def _registrar_pendencia_narrativa(conexao, empresa_id: int, resultado: dict) -> None:
    titulo = "Certidão Narrativa com resultado positivo - SEFAZ-PE"
    descricao = resultado.get("pendencia_detalhes") or "O documento lido no navegador indica Certidão Positiva."
    aberta = conexao.execute(
        "SELECT id FROM pendencias WHERE empresa_id=? AND tipo='CERTIDAO_NARRATIVA' AND status <> 'RESOLVIDA' ORDER BY id DESC LIMIT 1",
        (empresa_id,),
    ).fetchone()
    if aberta:
        conexao.execute("UPDATE pendencias SET descricao=?, atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (descricao, aberta["id"]))
    else:
        conexao.execute(
            """INSERT INTO pendencias
               (empresa_id,tipo,origem,titulo,descricao,status,prioridade,data_identificacao)
               VALUES (?,?,?,?,?,?,?,?)""",
            (empresa_id, "CERTIDAO_NARRATIVA", "SEFAZ-PE", titulo, descricao, "ABERTA", "ALTA", date.today().isoformat()),
        )

async def consultar_estadual(empresa_id: int, tentativas: int = 3, browser=None) -> dict:
    return await _consultar_empresa(empresa_id, tentativas=tentativas, browser=browser)


async def consultar_estadual_todas(tentativas: int = 3) -> dict:
    """Executa a automação real para todas as empresas ativas, sem parar o lote.

    Uma única instância do Chromium é reutilizada; cada empresa recebe seu
    próprio contexto/página. Cada resultado é persistido imediatamente.
    """
    from playwright.async_api import async_playwright
    from app.services.sefaz_pe_service import HEADLESS

    conexao = conectar_banco()
    try:
        empresas = [dict(r) for r in conexao.execute(
            "SELECT id, cnpj, razao_social FROM empresas WHERE ativo=1 ORDER BY id"
        ).fetchall()]
    finally:
        conexao.close()

    resultados = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        try:
            for indice, empresa in enumerate(empresas, start=1):
                try:
                    resultado = await _consultar_empresa(
                        empresa["id"], tentativas=tentativas, browser=browser
                    )
                except Exception as exc:
                    # Mesmo um erro inesperado de uma empresa não interrompe o lote.
                    # O erro também é gravado no histórico para não deixar lacunas.
                    try:
                        resultado = _registrar_falha_empresa(empresa["id"], str(exc))
                    except Exception as persist_exc:
                        resultado = {
                            "empresa_id": empresa["id"],
                            "empresa": empresa["razao_social"],
                            "cnpj": formatar_cnpj(empresa["cnpj"]),
                            "situacao": "ERRO",
                            "status_processamento": "Erro",
                            "mensagem": str(exc),
                            "erro_tecnico": f"{exc}; falha ao registrar histórico: {persist_exc}",
                            "consulta_registrada": False,
                        }
                resultado["ordem_lote"] = indice
                resultado["total_lote"] = len(empresas)
                resultados.append(resultado)
        finally:
            await browser.close()

    resumo = {
        "total": len(resultados),
        "regular": sum(r.get("situacao") == "REGULAR" for r in resultados),
        "positiva_com_efeitos_de_negativa": sum(r.get("situacao") == "POSITIVA COM EFEITOS DE NEGATIVA" for r in resultados),
        "irregular": sum(r.get("situacao") == "IRREGULAR" for r in resultados),
        "aguardando_intervencao": sum(r.get("situacao") == "AGUARDANDO_INTERVENCAO" for r in resultados),
        "erro": sum(r.get("situacao") == "ERRO" for r in resultados),
        "consultas_registradas": sum(bool(r.get("consulta_registrada")) for r in resultados),
    }
    return {"resumo": resumo, "resultados": resultados}


def registrar(dados: dict):
    """Registra/atualiza o estado atual e cria uma entrada histórica imutável.

    Mesmo registros manuais entram no livro de consultas, para que nenhuma
    mudança de situação substitua a evidência anterior.
    """
    conexao = conectar_banco()
    try:
        if not conexao.execute("SELECT id FROM empresas WHERE id=?", (dados["empresa_id"],)).fetchone():
            raise LookupError("Empresa não encontrada.")
        if not conexao.execute("SELECT id FROM tipos_certidao WHERE id=?", (dados["tipo_certidao_id"],)).fetchone():
            raise LookupError("Tipo de certidão não encontrado.")
        atual = conexao.execute(
            "SELECT id FROM certidoes WHERE empresa_id=? AND tipo_certidao_id=?",
            (dados["empresa_id"], dados["tipo_certidao_id"]),
        ).fetchone()
        if atual:
            cert_id = atual["id"]
            conexao.execute(
                "UPDATE certidoes SET situacao=?,numero_certidao=?,data_emissao=?,data_validade=?,origem=?,observacao=?,atualizada_em=CURRENT_TIMESTAMP WHERE id=?",
                (dados["situacao"], dados.get("numero_certidao"), dados.get("data_emissao"), dados.get("data_validade"), dados.get("origem"), dados.get("observacao"), cert_id),
            )
        else:
            cur = conexao.execute(
                "INSERT INTO certidoes (empresa_id,tipo_certidao_id,situacao,numero_certidao,data_emissao,data_validade,origem,observacao) VALUES (?,?,?,?,?,?,?,?)",
                (dados["empresa_id"], dados["tipo_certidao_id"], dados["situacao"], dados.get("numero_certidao"), dados.get("data_emissao"), dados.get("data_validade"), dados.get("origem"), dados.get("observacao")),
            )
            cert_id = cur.lastrowid

        cur = conexao.execute(
            """
            INSERT INTO consultas_certidoes
            (empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,data_emissao,data_validade,
             pdf_path,origem,mensagem,pendencia,pendencia_detalhes,nome_arquivo_original,status_processamento,erro_tecnico)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                dados["empresa_id"], dados["tipo_certidao_id"], cert_id, dados["situacao"],
                dados.get("numero_certidao"), dados.get("data_emissao"), dados.get("data_validade"),
                dados.get("pdf_path"), dados.get("origem"), dados.get("observacao"),
                0, None, dados.get("nome_arquivo_original"), "Registro manual", None,
            ),
        )
        consulta_id = cur.lastrowid
        conexao.execute(
            """
            INSERT INTO certidoes_historico
            (consulta_id,empresa_id,tipo_certidao_id,certidao_id,situacao,numero_certidao,
             data_emissao,data_validade,pdf_path,documento_id,hash_arquivo,nome_arquivo_original,
             status_processamento,erro_tecnico,mensagem,consultado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """,
            (
                consulta_id, dados["empresa_id"], dados["tipo_certidao_id"], cert_id, dados["situacao"],
                dados.get("numero_certidao"), dados.get("data_emissao"), dados.get("data_validade"),
                dados.get("pdf_path"), dados.get("documento_id"), dados.get("hash_arquivo"),
                dados.get("nome_arquivo_original"), "Registro manual", None, dados.get("observacao"),
            ),
        )
        conexao.commit()
        resultado = dict(conexao.execute("SELECT * FROM certidoes WHERE id=?", (cert_id,)).fetchone())
        resultado["consulta_id"] = consulta_id
        backup_banco_permanente()
        return resultado
    finally:
        conexao.close()


def obter_pdf_path(path: str) -> Path:
    base = BASE_DIR.parent.resolve()
    candidato = (base / path).resolve()
    if base != candidato and base not in candidato.parents:
        raise ValueError("Caminho de arquivo inválido.")
    return candidato
