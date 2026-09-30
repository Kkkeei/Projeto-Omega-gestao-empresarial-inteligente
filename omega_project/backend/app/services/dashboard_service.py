from app.db.database import conectar_banco

def resumo():
 c=conectar_banco()
 try:
  total=c.execute('SELECT COUNT(*) n FROM empresas').fetchone()['n']; ativas=c.execute('SELECT COUNT(*) n FROM empresas WHERE ativo=1').fetchone()['n']
  pend=c.execute("SELECT COUNT(*) n FROM pendencias WHERE status NOT IN ('RESOLVIDA','FECHADA')").fetchone()['n']
  regulares=c.execute("SELECT COUNT(*) n FROM certidoes c JOIN empresas e ON e.id=c.empresa_id WHERE e.ativo=1 AND c.situacao='REGULAR'").fetchone()['n']
  venc=c.execute("SELECT COUNT(*) n FROM certidoes WHERE data_validade IS NOT NULL AND date(data_validade)<date('now')").fetchone()['n']
  prox=c.execute("SELECT COUNT(*) n FROM certidoes WHERE data_validade IS NOT NULL AND date(data_validade)>=date('now') AND date(data_validade)<=date('now','+30 day')").fetchone()['n']
  auto=c.execute("SELECT COUNT(*) n FROM execucoes_automacao WHERE status IN ('EXECUTANDO','PENDENTE')").fetchone()['n']
  return {'empresas_total':total,'empresas':total,'empresas_ativas':ativas,'empresas_inativas':total-ativas,'empresas_regulares':regulares,'pendencias_abertas':pend,'certidoes_vencidas':venc,'certidoes_proximas_vencimento':prox,'automacoes_em_andamento':auto}
 finally: c.close()
