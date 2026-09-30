from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path

from . import repository
from .notificacoes_service import programar_notificacoes

MESES = repository.MESES


def _competencia_anterior():
    hoje = date.today()
    if hoje.month == 1:
        return hoje.year - 1, 12
    return hoje.year, hoje.month - 1


def _competencia_atual():
    hoje = date.today()
    return hoje.year, hoje.month


def dashboard(q=None, regime=None, situacao=None, ano=None, mes=None):
    ano, mes = (ano, mes) if ano and mes else _competencia_atual()
    from .notificacoes_service import gerar_alertas_vencidos
    gerar_alertas_vencidos()
    return repository.listar_empresas_impostos(q, regime, situacao, ano, mes)


def detalhe_empresa(empresa_id, ano=None, mes=None):
    ano, mes = (ano, mes) if ano and mes else _competencia_anterior()
    from .notificacoes_service import gerar_alertas_vencidos
    gerar_alertas_vencidos(empresa_id)
    data = repository.obter_empresa_impostos(empresa_id, ano, mes)
    if not data:
        raise LookupError("Empresa não encontrada.")
    return data


def detalhe_imposto(empresa_id, tributo_id, ano=None, mes=None):
    ano, mes = (ano, mes) if ano and mes else _competencia_anterior()
    from .notificacoes_service import gerar_alertas_vencidos
    gerar_alertas_vencidos(empresa_id)
    data = repository.obter_detalhe_imposto(empresa_id, tributo_id, ano, mes)
    if not data:
        raise LookupError("Imposto não encontrado para esta empresa.")
    return data


def _texto_arquivo(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    if ext in {".jpg", ".jpeg", ".png"}:
        try:
            import pytesseract  # opcional
            from PIL import Image
            return pytesseract.image_to_string(Image.open(path), lang="por+eng")
        except Exception:
            return ""
    return ""


def _parse_extracao(texto: str) -> dict:
    texto = texto or ""
    dados = {"competencia_extraida": None, "valor_extraido": None, "vencimento_extraido": None, "codigo_receita": None, "cnpj_extraido": None, "data_pagamento_extraida": None, "periodo_apuracao_inicio": None, "periodo_apuracao_fim": None}
    # Datas no padrão brasileiro.
    datas = re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", texto)
    datas_iso = [f"{d[6:10]}-{d[3:5]}-{d[0:2]}" for d in datas]
    venc_patterns = r"(?:vencimento|venc|data\s+de\s+vencimento)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})"
    m = re.search(venc_patterns, texto, re.I)
    if m:
        d=m.group(1); dados["vencimento_extraido"]=f"{d[6:10]}-{d[3:5]}-{d[0:2]}"
    elif datas_iso:
        dados["vencimento_extraido"] = datas_iso[-1]
    cnpj = re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", texto)
    if cnpj: dados["cnpj_extraido"]=cnpj.group(0)
    codigo = re.search(r"(?:c[oó]digo\s+(?:da\s+)?receita|receita)\s*[:\-]?\s*(\d{4,12})", texto, re.I)
    if codigo: dados["codigo_receita"]=codigo.group(1)
    valores=[]
    for raw in re.findall(r"(?:R\$\s*)?\b\d{1,3}(?:\.\d{3})*,\d{2}\b", texto):
        try: valores.append(float(raw.replace('.','').replace(',','.')))
        except ValueError: pass
    mval=re.search(r"(?:valor(?:\s+do\s+documento)?|principal|total(?:\s+a\s+pagar)?)\s*[:\-]?\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})",texto,re.I)
    if mval:
        try: dados["valor_extraido"]=float(mval.group(1).replace('.','').replace(',','.'))
        except ValueError: pass
    elif valores: dados["valor_extraido"]=valores[-1]
    comp=re.search(r"(?:compet[êe]ncia|per[ií]odo de apura[cç][ãa]o)\D{0,30}(\d{2}/\d{4})",texto,re.I)
    if comp: dados["competencia_extraida"]=comp.group(1)
    else:
        mcomp=re.search(r"\b(0[1-9]|1[0-2])/(20\d{2})\b",texto)
        if mcomp: dados["competencia_extraida"]=mcomp.group(0)
    periodo=re.search(r"(\d{2}/\d{2}/\d{4})\s*(?:a|à|-|até)\s*(\d{2}/\d{2}/\d{4})",texto,re.I)
    if periodo:
        a,b=periodo.groups(); dados["periodo_apuracao_inicio"]=f"{a[6:10]}-{a[3:5]}-{a[0:2]}"; dados["periodo_apuracao_fim"]=f"{b[6:10]}-{b[3:5]}-{b[0:2]}"
    pay=re.search(r"(?:pagamento|pago em|data do pagamento)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",texto,re.I)
    if pay:
        d=pay.group(1); dados["data_pagamento_extraida"]=f"{d[6:10]}-{d[3:5]}-{d[0:2]}"
    return dados


def preparar_guia(empresa_id:int,tributo_id:int,ano:int,mes:int,arquivo,storage_base:Path)->dict:
    if not arquivo.filename: raise ValueError("Selecione um arquivo.")
    ext=Path(arquivo.filename).suffix.lower()
    if ext not in {".pdf",".jpg",".jpeg",".png"}: raise ValueError("O arquivo deve ser PDF, JPG ou PNG.")
    conteudo=arquivo.file.read()
    if len(conteudo)>10*1024*1024: raise ValueError("O arquivo excede o limite de 10 MB.")
    mensal=repository.garantir_mensal(empresa_id,tributo_id,ano,mes)
    pasta=storage_base/"impostos"/str(empresa_id)/f"{ano:04d}"/f"{mes:02d}"
    pasta.mkdir(parents=True,exist_ok=True)
    nome=f"{uuid.uuid4().hex}{ext}"
    caminho=pasta/nome; caminho.write_bytes(conteudo)
    texto=_texto_arquivo(caminho); dados=_parse_extracao(texto)
    dig=hashlib.sha256(conteudo).hexdigest()
    documento=repository.adicionar_documento(mensal["id"],{"nome_arquivo":arquivo.filename,"caminho_arquivo":str(caminho),"extensao":ext.lstrip('.'),"mime_type":arquivo.content_type,"tamanho":len(conteudo),"hash_arquivo":dig,"status_documento":"RASCUNHO",**dados})
    return {"documento":documento,"mensal":mensal,"extracao":dados,"texto_extraido_disponivel":bool(texto.strip())}


def confirmar_guia(empresa_id:int,tributo_id:int,data:dict)->dict:
    doc_id=data["documento_id"]
    mensal=repository.obter_mensal(empresa_id,tributo_id,data["competencia_ano"],data["competencia_mes"])
    if not mensal: mensal=repository.garantir_mensal(empresa_id,tributo_id,data["competencia_ano"],data["competencia_mes"])
    venc=data.get("vencimento"); pag=data.get("data_pagamento")
    status="PAGO" if pag else "A_PAGAR"
    msg=data.get("mensagem_cliente")
    if not msg:
        valor=float(data.get("valor") or 0)
        valor_brl=f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")
        msg=(f"Prezado cliente,\n\nSegue em anexo a guia referente à competência {data['competencia_mes']:02d}/{data['competencia_ano']}, com vencimento em {venc[8:10]}/{venc[5:7]}/{venc[:4]}" + (f", no valor de {valor_brl}." if valor else ".") + "\n\nQualquer dúvida estamos à disposição.\n\nAtenciosamente,\nEquipe Contábil") if venc else "Prezado cliente,\n\nSegue em anexo a guia de imposto da competência informada.\n\nAtenciosamente,\nEquipe Contábil"
    repository.atualizar_documento(doc_id,{"competencia_extraida":data.get("competencia_extraida"),"valor_extraido":data.get("valor"),"vencimento_extraido":venc,"codigo_receita":data.get("codigo_receita"),"cnpj_extraido":data.get("cnpj"),"data_pagamento_extraida":pag,"periodo_apuracao_inicio":data.get("periodo_apuracao_inicio"),"periodo_apuracao_fim":data.get("periodo_apuracao_fim"),"mensagem_cliente":msg,"observacao":data.get("observacao")})
    mens=repository.salvar_mensal(empresa_id,{"tributo_id":tributo_id,"competencia_ano":data["competencia_ano"],"competencia_mes":data["competencia_mes"],"status":status,"valor":data.get("valor"),"data_vencimento":venc,"data_pagamento":pag,"numero_documento":data.get("codigo_receita"),"observacao":data.get("observacao")},"CONFIRMACAO_GUIA")
    # Marca documento como confirmado.
    repository.atualizar_documento(doc_id,{"status_documento":"CONFIRMADO"})
    from .notificacoes_service import programar_notificacoes
    # Obtém nome para a mensagem sem depender da camada HTTP.
    detal=repository.obter_mensal(empresa_id,tributo_id,data["competencia_ano"],data["competencia_mes"])
    tributo_nome=detal.get("nome","Imposto") if detal else "Imposto"
    programar_notificacoes(empresa_id,mens["id"],tributo_nome,repository.competencia_label(data["competencia_ano"],data["competencia_mes"]),venc,data.get("valor"))
    return repository.obter_detalhe_imposto(empresa_id,tributo_id,data["competencia_ano"],data["competencia_mes"])
