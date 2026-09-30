import json, re
from datetime import datetime
from typing import Optional
from app.db.database import conectar_banco
from app.services.brasilapi import consultar_cnpj, mapear_brasilapi

def normalizar_cnpj(cnpj: str) -> str: return re.sub(r'\D','',cnpj or '')

def validar_cnpj(cnpj: str) -> str:
    d=normalizar_cnpj(cnpj)
    if len(d)!=14 or len(set(d))==1: raise ValueError('CNPJ inválido.')
    w1=[5,4,3,2,9,8,7,6,5,4,3,2]
    w2=[6,5,4,3,2,9,8,7,6,5,4,3,2]
    s=sum(int(d[i])*w1[i] for i in range(12)); r=s%11; x=0 if r<2 else 11-r
    if x!=int(d[12]): raise ValueError('CNPJ inválido.')
    s=sum(int(d[i])*w2[i] for i in range(13)); r=s%11; x=0 if r<2 else 11-r
    if x!=int(d[13]): raise ValueError('CNPJ inválido.')
    return d

def empresa_por_id(empresa_id):
    c=conectar_banco();
    try:
        r=c.execute('SELECT * FROM empresas WHERE id=?',(empresa_id,)).fetchone(); return dict(r) if r else None
    finally: c.close()

def listar_empresas(q=None, ativo=None):
    c=conectar_banco();
    try:
        sql='SELECT * FROM empresas WHERE 1=1'; p=[]
        if q:
            t=f'%{q}%'; sql+=' AND (cnpj LIKE ? OR razao_social LIKE ? OR nome_fantasia LIKE ?)'; p += [t,t,t]
        if ativo is not None: sql+=' AND ativo=?'; p.append(1 if ativo else 0)
        sql+=' ORDER BY ativo DESC, razao_social'; return [dict(r) for r in c.execute(sql,p).fetchall()]
    finally: c.close()

def _json(v): return json.dumps(v,ensure_ascii=False,default=str)

def criar_empresa(dados):
    cnpj=validar_cnpj(dados['cnpj']); dados={**dados,'cnpj':cnpj}
    c=conectar_banco()
    try:
        if c.execute('SELECT id FROM empresas WHERE cnpj=?',(cnpj,)).fetchone(): raise ValueError('Já existe uma empresa cadastrada com este CNPJ.')
        campos=list(dados); vals=[dados[k] for k in campos]
        cur=c.execute(f"INSERT INTO empresas ({','.join(campos)}) VALUES ({','.join('?' for _ in campos)})",vals); eid=cur.lastrowid
        c.execute('INSERT INTO empresa_historicos (empresa_id,tipo_evento,descricao,dados_novos,origem) VALUES (?,?,?,?,?)',(eid,'CADASTRO','Empresa cadastrada',_json(dados),'MANUAL'))
        if dados.get('regime_tributario'): c.execute('INSERT INTO regimes_tributarios_historico (empresa_id,regime_novo,data_alteracao,origem) VALUES (?,?,?,?)',(eid,dados['regime_tributario'],datetime.now().strftime('%Y-%m-%d'),'CADASTRO'))
        c.commit(); return dict(c.execute('SELECT * FROM empresas WHERE id=?',(eid,)).fetchone())
    except: c.rollback(); raise
    finally: c.close()

def atualizar_empresa(empresa_id,dados):
    atual=empresa_por_id(empresa_id)
    if not atual: raise LookupError('Empresa não encontrada.')
    dados={k:v for k,v in dados.items() if v is not None}
    if not dados: return atual
    dados.pop('regime_tributario',None); dados.pop('ativo',None); dados.pop('data_saida',None)
    if not dados: return atual
    c=conectar_banco()
    try:
        sets=', '.join(f'{k}=?' for k in dados); vals=list(dados.values())+[datetime.now().strftime('%Y-%m-%d %H:%M:%S'),empresa_id]
        c.execute(f'UPDATE empresas SET {sets}, atualizado_em=? WHERE id=?',vals)
        c.execute('INSERT INTO empresa_historicos (empresa_id,tipo_evento,descricao,dados_anteriores,dados_novos,origem) VALUES (?,?,?,?,?,?)',(empresa_id,'ALTERACAO_CADASTRAL','Atualização cadastral',_json(atual),_json(dados),'MANUAL'))
        c.commit(); return dict(c.execute('SELECT * FROM empresas WHERE id=?',(empresa_id,)).fetchone())
    except: c.rollback(); raise
    finally: c.close()

def inativar_empresa(empresa_id,data_saida,observacao=None):
    atual=empresa_por_id(empresa_id)
    if not atual: raise LookupError('Empresa não encontrada.')
    if not atual['ativo']: raise ValueError('Empresa já está inativa.')
    c=conectar_banco()
    try:
        c.execute("UPDATE empresas SET ativo=0,data_saida=?,atualizado_em=? WHERE id=?",(data_saida,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),empresa_id))
        c.execute('INSERT INTO empresa_historicos (empresa_id,tipo_evento,descricao,dados_anteriores,dados_novos,origem) VALUES (?,?,?,?,?,?)',(empresa_id,'INATIVACAO','Empresa inativada',_json(atual),_json({'ativo':0,'data_saida':data_saida,'observacao':observacao}),'MANUAL'))
        c.commit(); return dict(c.execute('SELECT * FROM empresas WHERE id=?',(empresa_id,)).fetchone())
    finally: c.close()

def alterar_regime(empresa_id,regime,mes,ano,observacao=None):
    atual=empresa_por_id(empresa_id)
    if not atual: raise LookupError('Empresa não encontrada.')
    if atual.get('regime_tributario')==regime: raise ValueError('O regime informado já é o regime atual da empresa.')
    c=conectar_banco()
    try:
        c.execute('UPDATE empresas SET regime_tributario=?,atualizado_em=? WHERE id=?',(regime,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),empresa_id))
        c.execute('INSERT INTO regimes_tributarios_historico (empresa_id,regime_anterior,regime_novo,mes_inicio,ano_inicio,data_alteracao,origem,observacao) VALUES (?,?,?,?,?,?,?,?)',(empresa_id,atual.get('regime_tributario'),regime,mes,ano,f'{ano:04d}-{mes:02d}-01','MANUAL',observacao))
        c.execute('INSERT INTO empresa_historicos (empresa_id,tipo_evento,descricao,dados_anteriores,dados_novos,origem) VALUES (?,?,?,?,?,?)',(empresa_id,'ALTERACAO_REGIME','Regime tributário alterado',_json({'regime_tributario':atual.get('regime_tributario')}),_json({'regime_tributario':regime,'mes_inicio':mes,'ano_inicio':ano}),'MANUAL'))
        c.commit(); return dict(c.execute('SELECT * FROM empresas WHERE id=?',(empresa_id,)).fetchone())
    finally: c.close()

def historico_empresa(empresa_id):
    if not empresa_por_id(empresa_id): raise LookupError('Empresa não encontrada.')
    c=conectar_banco();
    try: return [dict(r) for r in c.execute('SELECT * FROM empresa_historicos WHERE empresa_id=? ORDER BY id DESC',(empresa_id,)).fetchall()]
    finally: c.close()

async def consultar_cnpj_externo(cnpj): validar_cnpj(cnpj); return await consultar_cnpj(cnpj)

async def sincronizar_empresa(empresa_id):
    atual=empresa_por_id(empresa_id)
    if not atual: raise LookupError('Empresa não encontrada.')
    dados=mapear_brasilapi(await consultar_cnpj(atual['cnpj']))
    # A sincronização cadastral NÃO altera o telefone informado no ÔMEGA.
    # O telefone fica sob controle do cadastro interno e não é sobrescrito pela BrasilAPI.
    dados.pop('telefone', None)
    dados={k:v for k,v in dados.items() if v is not None and k not in {'cnpj','regime_tributario','ativo','data_saida'}}
    alteracoes={k:{'anterior':atual.get(k),'novo':v} for k,v in dados.items() if atual.get(k)!=v}
    if alteracoes: atualizar_empresa(empresa_id,dados)
    c=conectar_banco()
    try:
        agora=datetime.now().strftime('%Y-%m-%d %H:%M:%S'); c.execute('UPDATE empresas SET ultima_sincronizacao=?,atualizado_em=? WHERE id=?',(agora,agora,empresa_id)); c.execute('INSERT INTO empresa_historicos (empresa_id,tipo_evento,descricao,dados_anteriores,dados_novos,origem) VALUES (?,?,?,?,?,?)',(empresa_id,'SINCRONIZACAO','Sincronização cadastral com BrasilAPI',_json(atual),_json(dados),'BRASILAPI')); c.commit(); return dict(c.execute('SELECT * FROM empresas WHERE id=?',(empresa_id,)).fetchone()),alteracoes
    finally: c.close()
