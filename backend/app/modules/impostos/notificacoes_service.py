from __future__ import annotations

from datetime import date, datetime, timedelta

from app.db.database import conectar_banco

from . import repository

DEFAULTS = {
    "CLIENTE": {"guia_enviada": 1, "antes_vencimento": 1, "dias_antes": 5, "dia_vencimento": 1, "nao_pagamento": 1, "imposto_vencido": 0},
    "CONTABILIDADE": {"guia_enviada": 1, "antes_vencimento": 1, "dias_antes": 5, "dia_vencimento": 1, "nao_pagamento": 1, "imposto_vencido": 1},
}


def listar_configuracoes() -> list[dict]:
    conn = conectar_banco()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM impostos_notificacoes_config ORDER BY publico").fetchall()]
    finally:
        conn.close()


def salvar_configuracao(data: dict) -> dict:
    publico = str(data["publico"]).upper()
    conn = conectar_banco()
    try:
        conn.execute(
            """INSERT INTO impostos_notificacoes_config
               (publico,guia_enviada,antes_vencimento,dias_antes,dia_vencimento,nao_pagamento,imposto_vencido)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(publico) DO UPDATE SET
                 guia_enviada=excluded.guia_enviada,
                 antes_vencimento=excluded.antes_vencimento,
                 dias_antes=excluded.dias_antes,
                 dia_vencimento=excluded.dia_vencimento,
                 nao_pagamento=excluded.nao_pagamento,
                 imposto_vencido=excluded.imposto_vencido,
                 atualizado_em=CURRENT_TIMESTAMP""",
            (publico, int(bool(data.get("guia_enviada", True))), int(bool(data.get("antes_vencimento", True))), int(data.get("dias_antes", 5)), int(bool(data.get("dia_vencimento", True))), int(bool(data.get("nao_pagamento", True))), int(bool(data.get("imposto_vencido", False)))),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM impostos_notificacoes_config WHERE publico=?", (publico,)).fetchone())
    finally:
        conn.close()


def _configs() -> dict[str, dict]:
    rows = listar_configuracoes()
    out = {r["publico"]: r for r in rows}
    for publico, default in DEFAULTS.items():
        if publico not in out:
            out[publico] = {"publico": publico, **default}
    return out


def programar_notificacoes(empresa_id: int, imposto_mensal_id: int, tributo_nome: str, competencia_label: str, vencimento: str | None, valor: float | None, status: str | None = None) -> list[dict]:
    venc = None
    if vencimento:
        try:
            venc = date.fromisoformat(vencimento[:10])
        except ValueError:
            venc = None
    configs = _configs()
    eventos = []
    pago = str(status or "").upper() == "PAGO"
    for publico, cfg in configs.items():
        prefixo = "cliente" if publico == "CLIENTE" else "contabilidade"
        if int(cfg.get("guia_enviada", 0)):
            agendado = datetime.now().isoformat(timespec="minutes")
            if not repository.notificacao_existe(imposto_mensal_id, publico, "GUIA_ENVIADA", agendado):
                eventos.append(repository.registrar_notificacao(empresa_id, imposto_mensal_id, "GUIA_ENVIADA", "Guia registrada", f"A guia de {tributo_nome} da competência {competencia_label} foi registrada.", publico, agendado, "PROGRAMADA"))
        if venc is not None and (not pago) and int(cfg.get("antes_vencimento", 0)):
            dia = venc - timedelta(days=int(cfg.get("dias_antes", 5)))
            agendado = dia.isoformat()
            if not repository.notificacao_existe(imposto_mensal_id, publico, "ANTES_VENCIMENTO", agendado):
                eventos.append(repository.registrar_notificacao(empresa_id, imposto_mensal_id, "ANTES_VENCIMENTO", "Próximo do vencimento", f"A guia de {tributo_nome} vence em {venc.strftime('%d/%m/%Y')}.", publico, agendado, "PROGRAMADA"))
        if venc is not None and (not pago) and int(cfg.get("dia_vencimento", 0)):
            agendado = venc.isoformat()
            if not repository.notificacao_existe(imposto_mensal_id, publico, "VENCIMENTO", agendado):
                eventos.append(repository.registrar_notificacao(empresa_id, imposto_mensal_id, "VENCIMENTO", "Vencimento", f"A guia de {tributo_nome} vence hoje ({venc.strftime('%d/%m/%Y')}).", publico, agendado, "PROGRAMADA"))
    return eventos


def gerar_alertas_vencidos(empresa_id: int | None = None) -> list[dict]:
    """Registra alertas internos idempotentes para guias vencidas/não pagas.

    Os eventos ficam pendentes para um canal de envio processá-los. Este módulo
    não afirma que enviou e-mail/WhatsApp sem integração de transporte ativa.
    """
    configs = _configs()
    ativos = {
        publico: cfg
        for publico, cfg in configs.items()
        if int(cfg.get("nao_pagamento", 0))
        or (publico == "CONTABILIDADE" and int(cfg.get("imposto_vencido", 0)))
    }
    if not ativos:
        return []
    conn = conectar_banco()
    try:
        where = [
            "im.status NOT IN ('PAGO','CREDOR','SEM_MOVIMENTACAO','SEM_MOVIMENTO','SEM_APURACAO')",
            "im.data_vencimento IS NOT NULL",
            "date(substr(im.data_vencimento,1,10)) < ?",
        ]
        params: list = [date.today().isoformat()]
        if empresa_id is not None:
            where.append("im.empresa_id=?")
            params.append(empresa_id)
        rows = conn.execute(f"""
            SELECT im.id,im.empresa_id,im.data_vencimento,im.competencia_ano,
                   im.competencia_mes,t.nome,im.valor
              FROM impostos_mensais im JOIN tributos t ON t.id=im.tributo_id
             WHERE {' AND '.join(where)}
        """, params).fetchall()
        created: list[int] = []
        for row in rows:
            venc = date.fromisoformat(row["data_vencimento"][:10])
            competencia = f"{row['competencia_mes']:02d}/{row['competencia_ano']}"
            for publico, cfg in ativos.items():
                tipos: list[tuple[str, str, str]] = []
                if int(cfg.get("nao_pagamento", 0)):
                    tipos.append((
                        "NAO_PAGAMENTO",
                        "Guia não identificada como paga",
                        f"A guia de {row['nome']} da competência {competencia}, vencida em {venc.strftime('%d/%m/%Y')}, ainda não está registrada como paga."
                    ))
                if publico == "CONTABILIDADE" and int(cfg.get("imposto_vencido", 0)):
                    tipos.append((
                        "IMPOSTO_VENCIDO",
                        "Imposto vencido",
                        f"O imposto {row['nome']} da competência {competencia} está vencido desde {venc.strftime('%d/%m/%Y')}."
                    ))
                for tipo, titulo, mensagem in tipos:
                    existe = conn.execute(
                        "SELECT 1 FROM impostos_notificacoes_eventos WHERE imposto_mensal_id=? AND publico=? AND tipo=? LIMIT 1",
                        (row["id"], publico, tipo),
                    ).fetchone()
                    if existe:
                        continue
                    cur = conn.execute(
                        "INSERT INTO impostos_notificacoes_eventos (empresa_id,imposto_mensal_id,publico,tipo,titulo,mensagem,agendado_para,status) VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP,'PENDENTE_ENVIO')",
                        (row["empresa_id"], row["id"], publico, tipo, titulo, mensagem),
                    )
                    created.append(cur.lastrowid)
        conn.commit()
        if not created:
            return []
        placeholders = ",".join("?" for _ in created)
        return [dict(r) for r in conn.execute(
            f"SELECT * FROM impostos_notificacoes_eventos WHERE id IN ({placeholders}) ORDER BY id",
            created,
        ).fetchall()]
    finally:
        conn.close()
def listar_eventos(empresa_id: int | None = None, imposto_mensal_id: int | None = None) -> list[dict]:
    conn = conectar_banco()
    try:
        where=[]; params=[]
        if empresa_id is not None: where.append("empresa_id=?"); params.append(empresa_id)
        if imposto_mensal_id is not None: where.append("imposto_mensal_id=?"); params.append(imposto_mensal_id)
        sql="SELECT * FROM impostos_notificacoes_eventos" + (" WHERE "+" AND ".join(where) if where else "") + " ORDER BY COALESCE(agendado_para,criado_em) DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally: conn.close()


def reenviar(evento_id: int) -> dict:
    conn = conectar_banco()
    try:
        row = conn.execute("SELECT * FROM impostos_notificacoes_eventos WHERE id=?", (evento_id,)).fetchone()
        if not row:
            raise LookupError("Evento de notificação não encontrado.")
        cur = conn.execute("INSERT INTO impostos_notificacoes_eventos (empresa_id,imposto_mensal_id,publico,tipo,titulo,mensagem,agendado_para,status) VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP,'PENDENTE_ENVIO')", (row["empresa_id"],row["imposto_mensal_id"],row["publico"],"REENVIO",f"Reenvio: {row['titulo']}",row["mensagem"]))
        conn.commit()
        return dict(conn.execute("SELECT * FROM impostos_notificacoes_eventos WHERE id=?", (cur.lastrowid,)).fetchone())
    finally: conn.close()
