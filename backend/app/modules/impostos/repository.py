from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.db.database import conectar_banco

MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
ESFERAS = ("Federal", "Estadual", "Municipal")
STATUS_FINAIS = {"PAGO", "CREDOR", "SEM_MOVIMENTACAO", "SEM_APURACAO"}


def competencia_iso(ano: int, mes: int) -> str:
    return f"{ano:04d}-{mes:02d}-01"


def competencia_label(ano: int, mes: int) -> str:
    return f"{MESES[mes]}/{ano}"


def chave_competencia(ano: int, mes: int) -> int:
    return ano * 12 + mes


def competencia_entre(inicio: str | None, fim: str | None, ano: int, mes: int) -> bool:
    alvo = chave_competencia(ano, mes)
    if inicio:
        try:
            i_ano, i_mes = map(int, inicio[:7].split("-"))
            if alvo < chave_competencia(i_ano, i_mes):
                return False
        except Exception:
            pass
    if fim:
        try:
            f_ano, f_mes = map(int, fim[:7].split("-"))
            if alvo > chave_competencia(f_ano, f_mes):
                return False
        except Exception:
            pass
    return True


def _status_exibicao(row: dict[str, Any], hoje: date | None = None) -> tuple[str, int | None]:
    hoje = hoje or date.today()
    status = (row.get("status_mensal") or "PENDENTE").upper()
    venc = row.get("data_vencimento")
    if status == "PAGO":
        return "PAGO", None
    if status == "CREDOR":
        return "CREDOR", None
    if status in {"SEM_MOVIMENTO", "SEM_MOVIMENTACAO"}:
        return "SEM_MOVIMENTACAO", None
    if status == "SEM_APURACAO":
        return "SEM_APURACAO", None
    if status == "PENDENTE" and not venc:
        return "PENDENTE", None
    if venc:
        try:
            d = date.fromisoformat(venc[:10])
            delta = (d - hoje).days
            if delta < 0:
                return "EM_ATRASO", delta
            if delta <= 7:
                return "A_VENCER", delta
            return "A_PAGAR", delta
        except Exception:
            pass
    return status, None


def _status_geral(tributos: list[dict[str, Any]]) -> dict[str, Any]:
    atrasados = []
    vencendo = []
    pendentes = 0
    for item in tributos:
        status, dias = _status_exibicao(item)
        item["status_exibicao"] = status
        item["dias_para_vencimento"] = dias
        if status == "EM_ATRASO":
            atrasados.append(item)
        elif status == "A_VENCER":
            vencendo.append(item)
        elif status == "PENDENTE":
            pendentes += 1
    if atrasados:
        return {"chave": "VENCIDO", "rotulo": f"{len(atrasados)} imposto(s) vencido(s)", "quantidade": len(atrasados)}
    if vencendo:
        dias = min((x["dias_para_vencimento"] or 0) for x in vencendo)
        rotulo = f"{len(vencendo)} imposto(s) vencendo em {dias} dia(s)" if dias != 0 else f"{len(vencendo)} imposto(s) vencendo hoje"
        return {"chave": "VENCENDO", "rotulo": rotulo, "quantidade": len(vencendo), "dias": dias}
    if pendentes:
        return {"chave": "PENDENTE", "rotulo": f"{pendentes} imposto(s) pendente(s)", "quantidade": pendentes}
    return {"chave": "EM_DIA", "rotulo": "Em dia", "quantidade": 0}


def listar_tributos(ativos_apenas: bool = False, q: str | None = None, esfera: str | None = None) -> list[dict[str, Any]]:
    conn = conectar_banco()
    try:
        where: list[str] = []
        params: list[Any] = []
        if ativos_apenas:
            where.append("ativo=1")
        if q:
            termo = f"%{q.strip().lower()}%"
            where.append("(LOWER(nome) LIKE ? OR LOWER(COALESCE(sigla,'')) LIKE ? OR LOWER(COALESCE(esfera,'')) LIKE ?)")
            params += [termo, termo, termo]
        if esfera and esfera.upper() != "TODAS":
            where.append("UPPER(COALESCE(esfera,''))=?")
            params.append(esfera.upper())
        sql = "SELECT * FROM tributos"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ativo DESC, nome COLLATE NOCASE"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def criar_tributo(data: dict[str, Any]) -> dict[str, Any]:
    nome = str(data.get("nome") or "").strip()
    codigo = str(data.get("sigla") or "").strip()
    esfera = str(data.get("esfera") or "").strip().title()
    if not nome or not codigo or esfera not in ESFERAS:
        raise ValueError("Nome, código do tributo e esfera são obrigatórios.")
    conn = conectar_banco()
    try:
        if conn.execute("SELECT 1 FROM tributos WHERE LOWER(nome)=LOWER(?) OR sigla=? LIMIT 1", (nome, codigo)).fetchone():
            raise ValueError("Já existe um tributo com esse nome ou código.")
        cur = conn.execute("INSERT INTO tributos (nome,sigla,esfera,categoria,periodicidade,descricao) VALUES (?,?,?,?,?,?)", (nome, codigo, esfera, data.get("categoria"), data.get("periodicidade") or "Mensal", data.get("descricao")))
        conn.commit()
        return dict(conn.execute("SELECT * FROM tributos WHERE id=?", (cur.lastrowid,)).fetchone())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def atualizar_tributo(tributo_id: int, data: dict[str, Any]) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        atual = conn.execute("SELECT * FROM tributos WHERE id=?", (tributo_id,)).fetchone()
        if not atual:
            raise LookupError("Tributo não encontrado.")
        nome = str(data.get("nome") or "").strip()
        sigla = str(data.get("sigla") or "").strip()
        esfera = str(data.get("esfera") or "").strip().title()
        if not nome or not sigla or esfera not in ESFERAS:
            raise ValueError("Nome, código do tributo e esfera são obrigatórios.")
        dup = conn.execute("SELECT 1 FROM tributos WHERE id<>? AND (LOWER(nome)=LOWER(?) OR sigla=?) LIMIT 1", (tributo_id, nome, sigla)).fetchone()
        if dup:
            raise ValueError("Já existe outro tributo com esse nome ou código.")
        conn.execute("UPDATE tributos SET nome=?,sigla=?,esfera=?,categoria=?,periodicidade=?,descricao=?,ativo=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?", (nome, sigla, esfera, data.get("categoria"), data.get("periodicidade") or "Mensal", data.get("descricao"), int(bool(data.get("ativo", True))), tributo_id))
        conn.commit()
        return dict(conn.execute("SELECT * FROM tributos WHERE id=?", (tributo_id,)).fetchone())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def empresa_existe(empresa_id: int, apenas_ativa: bool = False) -> bool:
    conn = conectar_banco()
    try:
        sql = "SELECT 1 FROM empresas WHERE id=?" + (" AND ativo=1" if apenas_ativa else "") + " LIMIT 1"
        return conn.execute(sql, (empresa_id,)).fetchone() is not None
    finally:
        conn.close()


def listar_empresas_impostos(q: str | None, regime: str | None, situacao: str | None, ano: int, mes: int) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        where = ["e.ativo=1"]
        params: list[Any] = []
        if q:
            termo = q.strip().lower()
            where.append("(LOWER(e.razao_social) LIKE ? OR LOWER(COALESCE(e.nome_fantasia,'')) LIKE ? OR e.cnpj LIKE ?)")
            params.extend([f"%{termo}%", f"%{termo}%", f"%{q.strip()}%"])
        if regime and regime.upper() != "TODOS":
            where.append("UPPER(COALESCE(e.regime_tributario,''))=?")
            params.append(regime.upper())
        comp = competencia_iso(ano, mes)
        rows = conn.execute(
            f"""
            SELECT e.id,e.razao_social,e.nome_fantasia,e.cnpj,e.regime_tributario,
                   ei.tributo_id,t.nome AS tributo_nome,t.esfera,
                   im.id AS imposto_mensal_id,im.status AS status_mensal,im.valor,im.data_vencimento
              FROM empresas e
              LEFT JOIN empresa_impostos ei ON ei.empresa_id=e.id AND ei.status='ATIVO'
                 AND (ei.vigencia_inicio IS NULL OR substr(ei.vigencia_inicio,1,7) <= substr(?,1,7))
                 AND (ei.vigencia_fim IS NULL OR substr(ei.vigencia_fim,1,7) >= substr(?,1,7))
              LEFT JOIN tributos t ON t.id=ei.tributo_id
              LEFT JOIN impostos_mensais im ON im.empresa_id=e.id AND im.tributo_id=ei.tributo_id
                 AND im.competencia_ano=? AND im.competencia_mes=?
             WHERE {' AND '.join(where)}
             ORDER BY e.razao_social COLLATE NOCASE
            """,
            [comp, comp, ano, mes, *params],
        ).fetchall()
        empresas: dict[int, dict[str, Any]] = {}
        for r in rows:
            d = dict(r)
            e = empresas.setdefault(d["id"], {k: d[k] for k in ("id","razao_social","nome_fantasia","cnpj","regime_tributario")})
            e.setdefault("_tributos", [])
            if d.get("tributo_id"):
                e["_tributos"].append(d)
        lista: list[dict[str, Any]] = []
        for e in empresas.values():
            tributos = e.pop("_tributos", [])
            for t in tributos:
                t["status_exibicao"], t["dias_para_vencimento"] = _status_exibicao(t)
            total = len(tributos)
            informados = sum(1 for t in tributos if t.get("status_mensal") and t.get("status_mensal") != "PENDENTE")
            resumo_status = _status_geral(tributos)
            e.update({
                "tributos_vinculados": total,
                "impostos_informados": informados,
                "impostos_pendentes": sum(1 for t in tributos if t["status_exibicao"] == "PENDENTE"),
                "impostos_atrasados": sum(1 for t in tributos if t["status_exibicao"] == "EM_ATRASO"),
                "impostos_vencendo": sum(1 for t in tributos if t["status_exibicao"] == "A_VENCER"),
                "impostos_pagos": sum(1 for t in tributos if t["status_exibicao"] == "PAGO"),
                "valor_a_pagar": round(sum(float(t.get("valor") or 0) for t in tributos if t["status_exibicao"] in {"A_PAGAR","A_VENCER","EM_ATRASO"}), 2),
                "status_geral": resumo_status,
            })
            if situacao and situacao.upper() not in {"TODAS", "TODOS"} and resumo_status["chave"] != situacao.upper():
                continue
            lista.append(e)

        regime_rows = conn.execute("SELECT UPPER(COALESCE(regime_tributario,'')) regime,COUNT(*) quantidade FROM empresas WHERE ativo=1 GROUP BY UPPER(COALESCE(regime_tributario,''))").fetchall()
        regime_map = {str(r["regime"]): int(r["quantidade"]) for r in regime_rows}
        indicadores = {
            "total_empresas": len(lista),
            "regimes": {
                "TODOS": sum(regime_map.values()),
                "SIMPLES NACIONAL": regime_map.get("SIMPLES NACIONAL",0),
                "LUCRO PRESUMIDO": regime_map.get("LUCRO PRESUMIDO",0),
                "LUCRO REAL": regime_map.get("LUCRO REAL",0),
            },
            "empresas_configuradas": sum(1 for e in lista if e["tributos_vinculados"] > 0),
            "impostos_pendentes": sum(e["impostos_pendentes"] for e in lista),
            "impostos_pagos": sum(e["impostos_pagos"] for e in lista),
            "valor_a_pagar": round(sum(e["valor_a_pagar"] for e in lista),2),
            "competencia": {"ano":ano,"mes":mes,"label":competencia_label(ano,mes)},
        }
        return {"empresas": lista, "indicadores": indicadores, "competencia": indicadores["competencia"]}
    finally:
        conn.close()


def garantir_mensal(empresa_id: int, tributo_id: int, ano: int, mes: int) -> dict[str, Any]:
    conn = conectar_banco()
    try:
        comp = competencia_iso(ano, mes)
        vinculo = conn.execute(
            """
            SELECT * FROM empresa_impostos
             WHERE empresa_id=? AND tributo_id=?
               AND (vigencia_inicio IS NULL OR substr(vigencia_inicio,1,7) <= substr(?,1,7))
               AND (vigencia_fim IS NULL OR substr(vigencia_fim,1,7) >= substr(?,1,7))
             ORDER BY id DESC LIMIT 1
            """,
            (empresa_id, tributo_id, comp, comp),
        ).fetchone()
        if not vinculo:
            raise LookupError("O imposto não está configurado para esta competência.")
        existente = conn.execute("SELECT * FROM impostos_mensais WHERE empresa_id=? AND tributo_id=? AND competencia_ano=? AND competencia_mes=?", (empresa_id,tributo_id,ano,mes)).fetchone()
        if existente:
            return dict(existente)
        cur = conn.execute("INSERT INTO impostos_mensais (empresa_id,tributo_id,competencia_ano,competencia_mes,status) VALUES (?,?,?,?, 'PENDENTE')", (empresa_id,tributo_id,ano,mes))
        conn.commit()
        return dict(conn.execute("SELECT * FROM impostos_mensais WHERE id=?", (cur.lastrowid,)).fetchone())
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def obter_empresa_impostos(empresa_id: int, ano: int, mes: int) -> dict[str, Any] | None:
    if not empresa_existe(empresa_id):
        return None
    conn = conectar_banco()
    try:
        empresa = conn.execute("SELECT id,cnpj,razao_social,nome_fantasia,regime_tributario,municipio,uf,ativo,observacoes FROM empresas WHERE id=?", (empresa_id,)).fetchone()
        comp = competencia_iso(ano,mes)
        links = conn.execute(
            """
            SELECT ei.*, t.nome, t.sigla, t.esfera, t.categoria, t.periodicidade, t.ativo AS tributo_ativo
              FROM empresa_impostos ei JOIN tributos t ON t.id=ei.tributo_id
             WHERE ei.empresa_id=? AND (ei.vigencia_inicio IS NULL OR substr(ei.vigencia_inicio,1,7) <= substr(?,1,7))
               AND (ei.vigencia_fim IS NULL OR substr(ei.vigencia_fim,1,7) >= substr(?,1,7))
             ORDER BY CASE t.esfera WHEN 'Federal' THEN 1 WHEN 'Estadual' THEN 2 WHEN 'Municipal' THEN 3 ELSE 4 END, t.nome COLLATE NOCASE
            """, (empresa_id,comp,comp)
        ).fetchall()
        tributos: list[dict[str,Any]] = []
        for l in links:
            d = dict(l)
            mensal = conn.execute("SELECT * FROM impostos_mensais WHERE empresa_id=? AND tributo_id=? AND competencia_ano=? AND competencia_mes=?", (empresa_id,d["tributo_id"],ano,mes)).fetchone()
            if not mensal:
                cur = conn.execute("INSERT INTO impostos_mensais (empresa_id,tributo_id,competencia_ano,competencia_mes,status) VALUES (?,?,?,?, 'PENDENTE')", (empresa_id,d["tributo_id"],ano,mes)); conn.commit()
                mensal = conn.execute("SELECT * FROM impostos_mensais WHERE id=?", (cur.lastrowid,)).fetchone()
            m = dict(mensal)
            d.update({"imposto_mensal_id":m["id"],"status_mensal":m["status"],"valor":m["valor"],"data_vencimento":m["data_vencimento"],"data_pagamento":m["data_pagamento"],"numero_documento":m["numero_documento"],"mensal_observacao":m["observacao"]})
            d["status_exibicao"], d["dias_para_vencimento"] = _status_exibicao(d)
            tributos.append(d)
        resumo = {
            "tributos_vinculados": len(tributos),
            "informados": sum(1 for x in tributos if x["status_mensal"] != "PENDENTE"),
            "atrasados": sum(1 for x in tributos if x["status_exibicao"] == "EM_ATRASO"),
            "vencendo": sum(1 for x in tributos if x["status_exibicao"] == "A_VENCER"),
            "sem_valor": sum(1 for x in tributos if x["status_exibicao"] in {"SEM_APURACAO","CREDOR","SEM_MOVIMENTACAO"} or (x["status_mensal"] != "PENDENTE" and float(x.get("valor") or 0)==0)),
            "valor_a_pagar": round(sum(float(x.get("valor") or 0) for x in tributos if x["status_exibicao"] in {"A_PAGAR","A_VENCER","EM_ATRASO"}),2),
        }
        grupos = {e:[x for x in tributos if (x.get("esfera") or "").lower()==e.lower()] for e in ESFERAS}
        return {"empresa":dict(empresa),"competencia":{"ano":ano,"mes":mes,"label":competencia_label(ano,mes)},"resumo":resumo,"tributos":tributos,"grupos":grupos}
    finally:
        conn.close()


def listar_configuracoes_empresa(empresa_id: int) -> list[dict[str,Any]]:
    conn = conectar_banco()
    try:
        rows=conn.execute("""
            SELECT ei.*,t.nome,t.sigla,t.esfera,t.ativo AS tributo_ativo
              FROM empresa_impostos ei JOIN tributos t ON t.id=ei.tributo_id
             WHERE ei.empresa_id=?
             ORDER BY CASE WHEN ei.status='ATIVO' THEN 0 ELSE 1 END,
                      CASE t.esfera WHEN 'Federal' THEN 1 WHEN 'Estadual' THEN 2 WHEN 'Municipal' THEN 3 ELSE 4 END,
                      t.nome COLLATE NOCASE
        """,(empresa_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def vincular_tributo(empresa_id: int, data: dict[str,Any]) -> dict[str,Any]:
    inicio=data.get("vigencia_inicio")
    if not inicio: raise ValueError("Informe a competência inicial.")
    inicio=str(inicio)[:7]+"-01" if len(str(inicio))==7 else str(inicio)[:10]
    fim=data.get("vigencia_fim")
    if fim: fim=str(fim)[:7]+"-01" if len(str(fim))==7 else str(fim)[:10]
    if fim and chave_competencia(int(inicio[:4]),int(inicio[5:7])) > chave_competencia(int(fim[:4]),int(fim[5:7])):
        raise ValueError("A competência final não pode ser anterior à inicial.")
    conn=conectar_banco()
    try:
        if not empresa_existe(empresa_id): raise LookupError("Empresa não encontrada.")
        tributo=conn.execute("SELECT * FROM tributos WHERE id=?",(data["tributo_id"],)).fetchone()
        if not tributo or int(tributo["ativo"])!=1: raise LookupError("Tributo inexistente ou inativo.")
        regime=conn.execute("SELECT regime_tributario FROM empresas WHERE id=?",(empresa_id,)).fetchone()[0]
        overlaps=conn.execute("""
            SELECT id FROM empresa_impostos
             WHERE empresa_id=? AND tributo_id=?
               AND NOT (COALESCE(vigencia_fim,'9999-12-01') < ? OR COALESCE(?, '9999-12-01') < COALESCE(vigencia_inicio,'0000-01-01'))
             LIMIT 1
        """,(empresa_id,data["tributo_id"],inicio,fim)).fetchone()
        if overlaps: raise ValueError("Este imposto já está configurado para esta empresa no período informado.")
        cur=conn.execute("INSERT INTO empresa_impostos (empresa_id,tributo_id,regime_tributario,obrigatorio,vigencia_inicio,vigencia_fim,status,observacao) VALUES (?,?,?,?,?,?,'ATIVO',?)",(empresa_id,data["tributo_id"],regime,int(bool(data.get("obrigatorio",True))),inicio,fim,data.get("observacao")))
        # Cria as obrigações mensais já transcorridas até a competência atual.
        hoje=date.today(); y0,m0=int(inicio[:4]),int(inicio[5:7]); y,m=y0,m0
        while (y,m) <= (hoje.year,hoje.month) and (fim is None or (y,m) <= (int(fim[:4]),int(fim[5:7]))):
            conn.execute("INSERT OR IGNORE INTO impostos_mensais (empresa_id,tributo_id,competencia_ano,competencia_mes,status) VALUES (?,?,?,?, 'PENDENTE')",(empresa_id,data["tributo_id"],y,m))
            m+=1
            if m==13: y+=1;m=1
        conn.commit()
        return dict(conn.execute("SELECT * FROM empresa_impostos WHERE id=?",(cur.lastrowid,)).fetchone())
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def atualizar_vinculo(vinculo_id:int,data:dict[str,Any]) -> dict[str,Any]:
    conn=conectar_banco()
    try:
        atual=conn.execute("SELECT * FROM empresa_impostos WHERE id=?",(vinculo_id,)).fetchone()
        if not atual: raise LookupError("Configuração de imposto não encontrada.")
        status=str(data.get("status") or atual["status"]).upper()
        inicio=data.get("vigencia_inicio") or atual["vigencia_inicio"]
        fim=data.get("vigencia_fim")
        if status=="INATIVO" and not fim: raise ValueError("Informe a competência de encerramento ao inativar o imposto.")
        if fim and inicio and fim[:7] < inicio[:7]: raise ValueError("A competência final não pode ser anterior à inicial.")
        overlap=conn.execute("""
            SELECT id FROM empresa_impostos
             WHERE id<>? AND empresa_id=? AND tributo_id=?
               AND NOT (COALESCE(vigencia_fim,'9999-12-01') < ? OR COALESCE(?, '9999-12-01') < COALESCE(vigencia_inicio,'0000-01-01'))
             LIMIT 1
        """,(vinculo_id,atual["empresa_id"],atual["tributo_id"],inicio,fim)).fetchone()
        if overlap: raise ValueError("Este imposto já possui outro vínculo no período informado.")
        conn.execute("UPDATE empresa_impostos SET vigencia_inicio=?,vigencia_fim=?,status=?,obrigatorio=?,observacao=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",(inicio,fim if status=="INATIVO" else None,status,int(bool(data.get("obrigatorio",atual["obrigatorio"]))),data.get("observacao"),vinculo_id))
        conn.commit()
        return dict(conn.execute("SELECT ei.*,t.nome,t.sigla,t.esfera FROM empresa_impostos ei JOIN tributos t ON t.id=ei.tributo_id WHERE ei.id=?",(vinculo_id,)).fetchone())
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def obter_mensal(empresa_id:int,tributo_id:int,ano:int,mes:int) -> dict[str,Any] | None:
    conn=conectar_banco()
    try:
        comp=competencia_iso(ano,mes)
        row=conn.execute("""
            SELECT im.*,t.nome,t.sigla,t.esfera,t.categoria,t.periodicidade,t.ativo AS tributo_ativo,
                   ei.vigencia_inicio,ei.vigencia_fim,ei.status AS vinculo_status
              FROM impostos_mensais im JOIN tributos t ON t.id=im.tributo_id
              LEFT JOIN empresa_impostos ei ON ei.empresa_id=im.empresa_id AND ei.tributo_id=im.tributo_id
                 AND (ei.vigencia_inicio IS NULL OR substr(ei.vigencia_inicio,1,7) <= substr(?,1,7))
                 AND (ei.vigencia_fim IS NULL OR substr(ei.vigencia_fim,1,7) >= substr(?,1,7))
             WHERE im.empresa_id=? AND im.tributo_id=? AND im.competencia_ano=? AND im.competencia_mes=?
             ORDER BY ei.id DESC LIMIT 1
        """,(comp,comp,empresa_id,tributo_id,ano,mes)).fetchone()
        if not row: return None
        d=dict(row); d["status_exibicao"],d["dias_para_vencimento"]=_status_exibicao({"status_mensal":d["status"],"data_vencimento":d["data_vencimento"]})
        return d
    finally: conn.close()


def obter_detalhe_imposto(empresa_id:int,tributo_id:int,ano:int,mes:int)->dict[str,Any]|None:
    conn=conectar_banco()
    try:
        empresa=conn.execute("SELECT id,razao_social,nome_fantasia,cnpj,regime_tributario FROM empresas WHERE id=?",(empresa_id,)).fetchone()
        comp = competencia_iso(ano, mes)
        tributo=conn.execute("""
            SELECT ei.*,t.nome,t.sigla,t.esfera,t.categoria,t.periodicidade,t.ativo AS tributo_ativo
              FROM empresa_impostos ei JOIN tributos t ON t.id=ei.tributo_id
             WHERE ei.empresa_id=? AND ei.tributo_id=?
               AND (ei.vigencia_inicio IS NULL OR substr(ei.vigencia_inicio,1,7) <= substr(?,1,7))
               AND (ei.vigencia_fim IS NULL OR substr(ei.vigencia_fim,1,7) >= substr(?,1,7))
             ORDER BY ei.id DESC LIMIT 1
        """,(empresa_id,tributo_id,comp,comp)).fetchone()
        if not empresa or not tributo: return None
        mensal=obter_mensal(empresa_id,tributo_id,ano,mes)
        if not mensal:
            mensal=garantir_mensal(empresa_id,tributo_id,ano,mes)
            mensal=obter_mensal(empresa_id,tributo_id,ano,mes)
        docs=conn.execute("""
            SELECT d.*, COALESCE(u.nome, 'Usuário do sistema') AS usuario_upload_nome
              FROM documentos_impostos d
              LEFT JOIN usuarios u ON u.id=d.usuario_upload_id
             WHERE d.imposto_mensal_id=?
               AND COALESCE(d.status_documento,'CONFIRMADO')='CONFIRMADO'
             ORDER BY d.id DESC
        """,(mensal["id"],)).fetchall()
        eventos=conn.execute("SELECT * FROM impostos_notificacoes_eventos WHERE imposto_mensal_id=? AND publico='CLIENTE' ORDER BY COALESCE(agendado_para,criado_em)",(mensal["id"],)).fetchall()
        hist=conn.execute("SELECT * FROM impostos_historico WHERE imposto_mensal_id=? ORDER BY criado_em DESC LIMIT 30",(mensal["id"],)).fetchall()
        return {"empresa":dict(empresa),"tributo":dict(tributo),"competencia":{"ano":ano,"mes":mes,"label":competencia_label(ano,mes)},"mensal":mensal,"documentos":[dict(x) for x in docs],"notificacoes":[dict(x) for x in eventos],"historico":[dict(x) for x in hist]}
    finally: conn.close()


def salvar_mensal(empresa_id:int,data:dict[str,Any],acao:str="ATUALIZACAO") -> dict[str,Any]:
    conn=conectar_banco()
    try:
        comp = competencia_iso(int(data["competencia_ano"]), int(data["competencia_mes"]))
        vinculo=conn.execute("""
            SELECT * FROM empresa_impostos
             WHERE empresa_id=? AND tributo_id=?
               AND (vigencia_inicio IS NULL OR substr(vigencia_inicio,1,7) <= substr(?,1,7))
               AND (vigencia_fim IS NULL OR substr(vigencia_fim,1,7) >= substr(?,1,7))
             ORDER BY id DESC LIMIT 1
        """,(empresa_id,data["tributo_id"],comp,comp)).fetchone()
        if not vinculo: raise LookupError("O tributo não está configurado para esta competência.")
        old=conn.execute("SELECT * FROM impostos_mensais WHERE empresa_id=? AND tributo_id=? AND competencia_ano=? AND competencia_mes=?",(empresa_id,data["tributo_id"],data["competencia_ano"],data["competencia_mes"])).fetchone()
        if old is None:
            cur=conn.execute("INSERT INTO impostos_mensais (empresa_id,tributo_id,competencia_ano,competencia_mes,status,valor,data_vencimento,data_pagamento,numero_documento,observacao) VALUES (?,?,?,?,?,?,?,?,?,?)",(empresa_id,data["tributo_id"],data["competencia_ano"],data["competencia_mes"],data.get("status","PENDENTE").upper(),data.get("valor"),data.get("data_vencimento"),data.get("data_pagamento"),data.get("numero_documento"),data.get("observacao")))
            mensal=conn.execute("SELECT * FROM impostos_mensais WHERE id=?",(cur.lastrowid,)).fetchone()
            old_status=None; old_val=None; old_json=None
        else:
            old_dict=dict(old); old_status=old_dict.get("status"); old_val=old_dict.get("valor"); old_json=json.dumps(old_dict,ensure_ascii=False)
            conn.execute("UPDATE impostos_mensais SET status=?,valor=?,data_vencimento=?,data_pagamento=?,numero_documento=?,observacao=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?",(data.get("status","PENDENTE").upper(),data.get("valor"),data.get("data_vencimento"),data.get("data_pagamento"),data.get("numero_documento"),data.get("observacao"),old["id"]))
            mensal=conn.execute("SELECT * FROM impostos_mensais WHERE id=?",(old["id"],)).fetchone()
        new_dict=dict(mensal)
        conn.execute("INSERT INTO impostos_historico (imposto_mensal_id,empresa_id,tributo_id,competencia_ano,competencia_mes,acao,status_anterior,status_novo,valor_anterior,valor_novo,dados_anteriores,dados_novos) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(mensal["id"],empresa_id,data["tributo_id"],data["competencia_ano"],data["competencia_mes"],acao,old_status,new_dict.get("status"),old_val,new_dict.get("valor"),old_json,json.dumps(new_dict,ensure_ascii=False)))
        conn.commit(); return new_dict
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def listar_historico_mensal(imposto_mensal_id:int)->list[dict[str,Any]]:
    conn=conectar_banco()
    try: return [dict(x) for x in conn.execute("SELECT * FROM impostos_historico WHERE imposto_mensal_id=? ORDER BY criado_em DESC",(imposto_mensal_id,)).fetchall()]
    finally: conn.close()


def remover_documentos_rascunho(imposto_mensal_id:int)->list[dict[str,Any]]:
    conn=conectar_banco()
    try:
        rows=[dict(x) for x in conn.execute(
            "SELECT id,caminho_arquivo FROM documentos_impostos WHERE imposto_mensal_id=? AND status_documento='RASCUNHO'",
            (imposto_mensal_id,),
        ).fetchall()]
        if rows:
            conn.execute(
                "DELETE FROM documentos_impostos WHERE imposto_mensal_id=? AND status_documento='RASCUNHO'",
                (imposto_mensal_id,),
            )
            conn.commit()
        return rows
    finally: conn.close()


def adicionar_documento(imposto_mensal_id:int,data:dict[str,Any])->dict[str,Any]:
    conn=conectar_banco()
    try:
        cur=conn.execute("""INSERT INTO documentos_impostos
          (imposto_mensal_id,nome_arquivo,caminho_arquivo,extensao,mime_type,tamanho,hash_arquivo,observacao,competencia_extraida,valor_extraido,vencimento_extraido,codigo_receita,cnpj_extraido,data_pagamento_extraida,periodo_apuracao_inicio,periodo_apuracao_fim,mensagem_cliente,enviado_em,usuario_upload_id,status_documento)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(imposto_mensal_id,data["nome_arquivo"],data["caminho_arquivo"],data.get("extensao"),data.get("mime_type"),data.get("tamanho"),data.get("hash_arquivo"),data.get("observacao"),data.get("competencia_extraida"),data.get("valor_extraido"),data.get("vencimento_extraido"),data.get("codigo_receita"),data.get("cnpj_extraido"),data.get("data_pagamento_extraida"),data.get("periodo_apuracao_inicio"),data.get("periodo_apuracao_fim"),data.get("mensagem_cliente"),data.get("enviado_em"),data.get("usuario_upload_id"),data.get("status_documento","CONFIRMADO")))
        conn.commit(); return dict(conn.execute("SELECT * FROM documentos_impostos WHERE id=?",(cur.lastrowid,)).fetchone())
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def atualizar_documento(documento_id:int,data:dict[str,Any])->dict[str,Any]:
    conn=conectar_banco()
    try:
        row=conn.execute("SELECT * FROM documentos_impostos WHERE id=?",(documento_id,)).fetchone()
        if not row: raise LookupError("Documento não encontrado.")
        allowed=["competencia_extraida","valor_extraido","vencimento_extraido","codigo_receita","cnpj_extraido","data_pagamento_extraida","periodo_apuracao_inicio","periodo_apuracao_fim","mensagem_cliente","observacao","enviado_em","usuario_upload_id","status_documento"]
        sets=[]; params=[]
        for key in allowed:
            if key in data:
                sets.append(f"{key}=?"); params.append(data[key])
        if sets:
            conn.execute("UPDATE documentos_impostos SET "+",".join(sets)+" WHERE id=?",params+[documento_id]); conn.commit()
        return dict(conn.execute("SELECT * FROM documentos_impostos WHERE id=?",(documento_id,)).fetchone())
    finally: conn.close()


def notificacao_existe(imposto_mensal_id: int, publico: str, tipo: str, agendado_para: str | None) -> bool:
    conn = conectar_banco()
    try:
        if tipo == 'GUIA_ENVIADA':
            row = conn.execute(
                "SELECT 1 FROM impostos_notificacoes_eventos WHERE imposto_mensal_id=? AND publico=? AND tipo=? LIMIT 1",
                (imposto_mensal_id, publico, tipo),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT 1 FROM impostos_notificacoes_eventos WHERE imposto_mensal_id=? AND publico=? AND tipo=? AND COALESCE(agendado_para,'')=COALESCE(?, '') LIMIT 1",
                (imposto_mensal_id, publico, tipo, agendado_para),
            ).fetchone()
        return row is not None
    finally:
        conn.close()


def registrar_notificacao(empresa_id:int,imposto_mensal_id:int,tipo:str,titulo:str,mensagem:str,publico:str,agendado_para:str|None,status:str="PROGRAMADA"):
    conn=conectar_banco()
    try:
        cur=conn.execute("INSERT INTO impostos_notificacoes_eventos (empresa_id,imposto_mensal_id,publico,tipo,titulo,mensagem,agendado_para,status) VALUES (?,?,?,?,?,?,?,?)",(empresa_id,imposto_mensal_id,publico,tipo,titulo,mensagem,agendado_para,status))
        conn.commit(); return dict(conn.execute("SELECT * FROM impostos_notificacoes_eventos WHERE id=?",(cur.lastrowid,)).fetchone())
    except Exception:
        conn.rollback(); raise
    finally: conn.close()
