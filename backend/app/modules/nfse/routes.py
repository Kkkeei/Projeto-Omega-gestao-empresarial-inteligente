from __future__ import annotations

import base64
import html
import re
import tempfile
import xml.etree.ElementTree as ET
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from typing import Any
import io
from typing import Literal

from app.api.v1.auth.routes import current_user
from app.modules.nfse import service

router = APIRouter(prefix="/api/v1/nfse", tags=["NFS-e"])


class ConsultarRequest(BaseModel):
    origem: str = Field(min_length=2, max_length=2)
    entidade_id: int = Field(gt=0)


class ImportarA3Request(BaseModel):
    origem: str = Field(min_length=2, max_length=2)
    entidade_id: int = Field(gt=0)
    thumbprint_sha256: str = Field(min_length=16, max_length=128)
    content_type: str = "application/json"
    body_b64: str = Field(min_length=1)


class SalvarConfigRequest(BaseModel):
    origem: Literal["PJ", "PF"]
    entidade_id: int = Field(gt=0)
    sincronizacao_automatica: bool = False
    frequencia_horas: int = Field(default=24, ge=1, le=720)
    horario: str = Field(default="02:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@router.get("/config")
def obter_config(origem: Literal["PJ", "PF"], entidade_id: int, _user=Depends(current_user)):
    try:
        return service.obter_config(origem, entidade_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/config")
def salvar_config(body: SalvarConfigRequest, _user=Depends(current_user)):
    try:
        return service.salvar_config(
            body.origem,
            body.entidade_id,
            body.sincronizacao_automatica,
            body.frequencia_horas,
            body.horario,
            _user["id"],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


class ConfiguracaoNfseRequest(BaseModel):
    origem: str = Field(min_length=2, max_length=2)
    entidade_id: int = Field(gt=0)
    sincronizacao_automatica: bool
    frequencia_horas: int = Field(ge=1, le=720)
    horario: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class EventoNfseRequest(BaseModel):
    tipo_evento: str = Field(min_length=1, max_length=80)
    descricao: str = Field(min_length=1, max_length=2000)
    origem: str = Field(default="SISTEMA", max_length=80)
    dados: dict[str, Any] = Field(default_factory=dict)


class LancamentoNfseRequest(BaseModel):
    data_lancamento: str
    conta_debito: str = Field(min_length=1, max_length=120)
    conta_credito: str = Field(min_length=1, max_length=120)
    historico: str = Field(min_length=1, max_length=500)
    valor: float = Field(ge=0)
    observacao: str | None = Field(default=None, max_length=2000)


class ZipNfseRequest(BaseModel):
    nfse_ids: list[int] = Field(min_length=1, max_length=500)


@router.get("/contexto")
def contexto(origem: str, entidade_id: int, _user=Depends(current_user)):
    try:
        return service.contexto(origem, entidade_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("")
def listar(origem: str | None = None, entidade_id: int | None = None, limit: int = 100, offset: int = 0, competencia: str | None = None, _user=Depends(current_user)):
    try:
        documents = service.listar(origem, entidade_id, limit, offset, competencia)
        return {"total": len(documents), "nfse": documents}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/painel")
def painel(competencia: str, _user=Depends(current_user)):
    try:
        return service.painel(competencia)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/configuracao")
def obter_configuracao(origem: str, entidade_id: int, _user=Depends(current_user)):
    try:
        return service.obter_config(origem, entidade_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/configuracao")
def salvar_configuracao(body: ConfiguracaoNfseRequest, user=Depends(current_user)):
    try:
        return service.salvar_config(
            body.origem, body.entidade_id, body.sincronizacao_automatica,
            body.frequencia_horas, body.horario, user["id"],
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/importar-xml")
async def importar_xml(
    origem: str = Form(...),
    entidade_id: int = Form(..., gt=0),
    arquivo: UploadFile = File(...),
    user=Depends(current_user),
):
    try:
        data = await arquivo.read(25 * 1024 * 1024 + 1)
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, "O arquivo excede o limite de 25 MB.")
        return service.importar_xml_manual(origem, entidade_id, arquivo.filename or "", data, user["id"])
    except HTTPException:
        raise
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/importar-eml")
async def importar_eml(
    origem: str = Form(...),
    entidade_id: int = Form(..., gt=0),
    arquivo: UploadFile = File(...),
    user=Depends(current_user),
):
    try:
        data = await arquivo.read(25 * 1024 * 1024 + 1)
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, "O arquivo excede o limite de 25 MB.")
        return service.importar_email_eml(origem, entidade_id, arquivo.filename or "", data, user["id"])
    except HTTPException:
        raise
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{nfse_id}/eventos")
def eventos(nfse_id: int, _user=Depends(current_user)):
    try:
        items = service.listar_eventos(nfse_id)
        return {"total": len(items), "eventos": items}
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{nfse_id}/eventos")
def registrar_evento(nfse_id: int, body: EventoNfseRequest, user=Depends(current_user)):
    try:
        return service.registrar_evento(
            nfse_id, body.tipo_evento, body.descricao, user["id"],
            origem=body.origem, dados=body.dados,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{nfse_id}/eventos/consultar-adn")
def consultar_eventos_adn(nfse_id: int, _user=Depends(current_user)):
    try:
        return service.consultar_eventos_adn(nfse_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/{nfse_id}/lancamento")
def salvar_lancamento(nfse_id: int, body: LancamentoNfseRequest, user=Depends(current_user)):
    try:
        return service.salvar_lancamento(
            nfse_id, body.data_lancamento, body.conta_debito, body.conta_credito,
            body.historico, body.valor, body.observacao, user["id"],
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/exportar/excel")
def exportar_excel(competencia: str, origem: str | None = None, entidade_id: int | None = None, _user=Depends(current_user)):
    try:
        content = service.exportar_excel(competencia, origem, entidade_id)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="nfse-{competencia}.xlsx"'},
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/exportar/xml-zip")
def exportar_xml_zip(body: ZipNfseRequest, _user=Depends(current_user)):
    try:
        content = service.zip_xmls(body.nfse_ids)
        return Response(
            content=content,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="nfse-xmls.zip"'},
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc

@router.get("/{nfse_id}")
def detalhe(nfse_id: int, _user=Depends(current_user)):
    try:
        return service.detalhe(nfse_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{nfse_id}/pdf")
def gerar_pdf(nfse_id: int, _user=Depends(current_user)):
    """Gera DANFSe em layout compacto semelhante ao modelo nacional, a partir do XML original."""
    try:
        doc = service.detalhe(nfse_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    xml_text = doc.get("xml")
    if not xml_text:
        raise HTTPException(404, "O XML original desta NFS-e não está disponível no armazenamento.")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise HTTPException(422, "O XML desta NFS-e está malformado e não pode ser convertido em PDF.") from exc

    # Para XML nacional, utiliza o renderizador baseado no modelo técnico oficial
    # DANFSe v2.0 (NT 008/2026), em vez do layout genérico de contingência abaixo.
    # A biblioteca lê os campos diretamente do XML e gera o QR code/chave quando disponíveis.
    root_name = root.tag.rsplit("}", 1)[-1].split(":")[-1].lower()
    local_names = [el.tag.rsplit("}", 1)[-1].split(":")[-1].lower() for el in root.iter()]
    has_national_nfse = (
        root_name in {"nfse", "compnfse", "nfseproc"}
        and "infnfse" in local_names
        and ("infdps" in local_names or "chnfse" in local_names)
    )
    if has_national_nfse:
        try:
            from danfse_brasil import parse_danfse, render_danfse_pdf
            with tempfile.TemporaryDirectory(prefix="omega-danfse-") as tmp:
                tmp_path = Path(tmp)
                xml_path = tmp_path / "nota.xml"
                pdf_path = tmp_path / "danfse.pdf"
                xml_path.write_text(xml_text, encoding="utf-8")
                danfse_data = parse_danfse(xml_path)
                render_danfse_pdf(danfse_data, pdf_path)
                pdf_bytes = pdf_path.read_bytes()
            safe_number = re.sub(r"[^A-Za-z0-9_-]", "_", str(doc.get("numero") or nfse_id))
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="danfse-{safe_number}.pdf"'},
            )
        except HTTPException:
            raise
        except Exception as exc:
            # Não emitir silenciosamente um PDF diferente do modelo oficial para XML nacional.
            raise HTTPException(
                422,
                "Não foi possível gerar o DANFSe no modelo nacional a partir deste XML. "
                "Confira se a versão da biblioteca danfse-brasil está instalada e se o XML é compatível.",
            ) from exc

    def lname(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].split(":")[-1].lower()

    # Indexa os campos do XML ignorando namespaces, para aceitar diferentes versões do leiaute.
    index: dict[str, list[str]] = {}
    for el in root.iter():
        name = lname(el.tag)
        value = (el.text or "").strip()
        if value:
            index.setdefault(name, []).append(value)

    def val(*names: str, default: str = "—") -> str:
        for name in names:
            values = index.get(name.lower(), [])
            if values:
                return values[0]
        return default

    def money(value: str) -> str:
        try:
            n = float(value.replace(",", "."))
            return "R$ " + f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, AttributeError):
            return value if value and value != "—" else "—"

    def first_present(*names: str, default: str = "—") -> str:
        result = val(*names, default="")
        return result or default

    # Resolve valores mais comuns do XML nacional; o fallback preserva dados disponíveis.
    numero = first_present("nNFSe", "numero", default=str(doc.get("numero") or nfse_id))
    chave = first_present("chNFSe", "chaveAcesso", "chave_acesso", default=str(doc.get("chave_acesso") or "—"))
    competencia = first_present("dCompet", "competencia", default="—")
    emissao = first_present("dhProc", "dhEmi", "dataEmissao", default=str(doc.get("data_emissao") or "—"))
    numero_dps = first_present("nDPS", "numeroDPS", default="—")
    serie_dps = first_present("serie", "serieDPS", default="—")
    emissao_dps = first_present("dhEmi", "dataEmissaoDPS", default="—")
    cnpj_prest = first_present("CNPJ", "CPF", default="—")
    prestador = first_present("xNome", "razaoSocial", "nomeEmpresarial", default="—")
    # Prefer the XML's actual provider/taker blocks when the document contains both.
    def block_values(block_names: tuple[str, ...]) -> dict[str, str]:
        wanted = {x.lower() for x in block_names}
        for parent in root.iter():
            if lname(parent.tag) in wanted:
                found: dict[str, str] = {}
                for child in parent.iter():
                    n = lname(child.tag)
                    v = (child.text or "").strip()
                    if v and n not in found:
                        found[n] = v
                return found
        return {}

    prest = block_values(("prest", "prestador", "emit"))
    toma = block_values(("toma", "tomador", "adquirente"))
    serv = block_values(("serv", "servico"))
    valores = block_values(("valores",))
    trib = block_values(("trib", "tributacao"))

    def bv(block: dict[str, str], *keys: str, default: str = "—") -> str:
        for key in keys:
            if block.get(key.lower()):
                return block[key.lower()]
        return default

    prestador = bv(prest, "xNome", "razaoSocial", "nome", default=prestador)
    prest_doc = bv(prest, "CNPJ", "CPF", "NIF", default=cnpj_prest)
    tomador = bv(toma, "xNome", "razaoSocial", "nome", default="—")
    tomador_doc = bv(toma, "CNPJ", "CPF", "NIF", default="—")
    prest_end = " ".join(filter(lambda x: x != "—", [bv(prest, "xLgr", "logradouro", default=""), bv(prest, "nro", "numeroEndereco", default=""), bv(prest, "xBairro", "bairro", default="")])) or "—"
    toma_end = " ".join(filter(lambda x: x != "—", [bv(toma, "xLgr", "logradouro", default=""), bv(toma, "nro", "numeroEndereco", default=""), bv(toma, "xBairro", "bairro", default="")])) or "—"
    municipio_prest = bv(prest, "xMun", "municipio", default="—")
    uf_prest = bv(prest, "UF", "uf", default="—")
    municipio_toma = bv(toma, "xMun", "municipio", default="—")
    uf_toma = bv(toma, "UF", "uf", default="—")
    descricao = bv(serv, "xDescServ", "discriminacao", "descricaoServico", default=first_present("xDescServ", "discriminacao", default="—"))
    codigo_servico = bv(serv, "cTribNac", "cTribMun", "codigoTributacaoNacional", default="—")
    local_prestacao = bv(serv, "xLocPrestacao", "xMunPrestacao", default=municipio_prest)
    valor_servico = bv(valores, "vServ", "valorServicos", "valorServico", default=first_present("vServ", "valorServico", default=str(doc.get("valor") or "—")))
    valor_liquido = bv(valores, "vLiq", "valorLiquidoNfse", default=valor_servico)
    iss_tipo = bv(trib, "tribISSQN", "tpRetISSQN", "tipoTributacaoISSQN", default="—")
    iss_valor = bv(valores, "vISSQN", "valorISSQN", default="—")

    output = BytesIO()
    pdf = SimpleDocTemplate(output, pagesize=A4, rightMargin=9*mm, leftMargin=9*mm, topMargin=7*mm, bottomMargin=7*mm, title=f"DANFSe {numero}", author="ÔMEGA")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DanfseTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=12, alignment=TA_CENTER, spaceAfter=0))
    styles.add(ParagraphStyle(name="DanfseSub", parent=styles["Normal"], fontSize=7, leading=8, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="DanfseSection", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=6.6, leading=7.4, textColor=colors.HexColor("#111111")))
    styles.add(ParagraphStyle(name="DanfseLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=5.7, leading=6.4, textColor=colors.HexColor("#202020")))
    styles.add(ParagraphStyle(name="DanfseValue", parent=styles["Normal"], fontSize=6.4, leading=7.2, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="DanfseTiny", parent=styles["Normal"], fontSize=5.5, leading=6.2, wordWrap="CJK"))

    def P(text: str, style: str = "DanfseValue") -> Paragraph:
        return Paragraph(escape(str(text or "—")).replace("\n", "<br/>"), styles[style])

    story = []
    # Logo extraído da referência visual fornecida pelo usuário e incorporado ao projeto.
    logo_path = Path(__file__).with_name("assets") / "danfse_logo.png"
    logo_path.parent.mkdir(parents=True, exist_ok=True)
    if logo_path.exists():
        logo = Image(str(logo_path), width=43*mm, height=12*mm)
        logo.hAlign = "LEFT"
    else:
        logo = P("NFS-e", "DanfseTitle")
    header = Table([[logo, P("DANFSe v2.0<br/>Documento Auxiliar da NFS-e", "DanfseTitle"), P("Município: " + municipio_prest + " - " + uf_prest + "<br/>Ambiente Gerador: " + first_present("tpAmb", default="—") + "<br/>Tipo de Ambiente: " + first_present("tpAmb", default="—"), "DanfseTiny")]], colWidths=[48*mm, 86*mm, 57*mm], rowHeights=[15*mm])
    header.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.8,colors.HexColor("#222222")),("INNERGRID",(0,0),(-1,-1),0.35,colors.HexColor("#777777")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(1,0),"CENTER"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
    story += [header, Spacer(1, 1*mm)]

    def section(title: str, cells: list[tuple[str, str]], widths: list[float] | None = None):
        story.append(P(title.upper(), "DanfseSection"))
        if not cells:
            return
        if widths is None:
            widths = [181*mm/len(cells)] * len(cells)
        # Campos em grade compacta, como no DANFSe de referência.
        data = [[P(label, "DanfseLabel") for label, _ in cells], [P(value) for _, value in cells]]
        tbl = Table(data, colWidths=widths)
        tbl.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.35,colors.black),("INNERGRID",(0,0),(-1,-1),0.25,colors.HexColor("#777777")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
        story.append(tbl)
        story.append(Spacer(1, 1*mm))

    section("Chave de acesso da NFS-e", [("Chave de acesso", chave)])
    section("Identificação da NFS-e", [("Número da NFS-e", numero), ("Competência", competencia), ("Data/hora de emissão", emissao)], [43*mm, 55*mm, 83*mm])
    section("Identificação da DPS", [("Número da DPS", numero_dps), ("Série da DPS", serie_dps), ("Emissão da DPS", emissao_dps)], [43*mm, 55*mm, 83*mm])
    section("Emitente da NFS-e", [("Emitente", "Prestador"), ("Situação", first_present("cStat", "situacao", default=str(doc.get("situacao") or "NFS-e gerada"))), ("Finalidade", first_present("finNFe", "finalidade", default="—"))], [60*mm, 60*mm, 61*mm])
    section("Prestador / fornecedor", [("CNPJ / CPF / NIF", prest_doc), ("Inscrição municipal", bv(prest, "IM", "inscricaoMunicipal", default="—")), ("Telefone", bv(prest, "fone", "telefone", default="—"))], [60*mm, 60*mm, 61*mm])
    section("Dados do prestador", [("Nome empresarial", prestador), ("Município / UF", municipio_prest + " / " + uf_prest)], [105*mm, 76*mm])
    section("Endereço do prestador", [("Endereço", prest_end), ("E-mail", bv(prest, "email", default="—"))], [105*mm, 76*mm])
    section("Tomador / adquirente", [("CNPJ / CPF / NIF", tomador_doc), ("Inscrição municipal", bv(toma, "IM", "inscricaoMunicipal", default="—")), ("Telefone", bv(toma, "fone", "telefone", default="—"))], [60*mm, 60*mm, 61*mm])
    section("Dados do tomador", [("Nome empresarial", tomador), ("Município / UF", municipio_toma + " / " + uf_toma)], [105*mm, 76*mm])
    section("Endereço do tomador", [("Endereço", toma_end), ("E-mail", bv(toma, "email", default="—"))], [105*mm, 76*mm])
    section("Serviço prestado", [("Código de tributação nacional/municipal", codigo_servico), ("Código NBS", bv(serv, "cNBS", "codigoNBS", default="—")), ("Local da prestação", local_prestacao)], [65*mm, 40*mm, 66*mm])
    section("Descrição do serviço", [("Descrição", descricao)])
    section("Tributação municipal (ISSQN)", [("Tipo de tributação", iss_tipo), ("Base de cálculo", bv(valores, "vBC", "baseCalculo", default="—")), ("Alíquota", bv(valores, "pAliq", "aliquota", default="—")), ("Retenção ISSQN", bv(trib, "tpRetISSQN", "retencaoISSQN", default="—")), ("ISSQN apurado", money(iss_valor))], [45*mm, 35*mm, 30*mm, 31*mm, 30*mm])
    section("Tributação federal", [("IRRF", bv(valores, "vRetIRRF", default="—")), ("Previdência retida", bv(valores, "vRetCP", default="—")), ("PIS retido", bv(valores, "vRetPIS", default="—")), ("COFINS retido", bv(valores, "vRetCOFINS", default="—"))], [43*mm, 43*mm, 43*mm, 42*mm])
    section("Tributação IBS/CBS", [("CST / cClassTrib", bv(trib, "CST", "cClassTrib", default="—")), ("Base de cálculo", bv(valores, "vBCIBSCBS", default="—")), ("IBS / CBS apurado", bv(valores, "vIBS", "vCBS", default="—"))], [60*mm, 55*mm, 56*mm])
    section("Valores da NFS-e", [("Valor da operação / serviço", money(valor_servico)), ("Descontos", money(bv(valores, "vDescIncond", "vDescCond", default="—"))), ("Total das retenções", money(bv(valores, "vTotalRet", "vTotTrib", default="—"))), ("Valor líquido da NFS-e", money(valor_liquido))], [48*mm, 40*mm, 40*mm, 43*mm])
    section("Informações complementares", [("Informações", first_present("xInfComp", "informacoesComplementares", default="—"))])
    story.append(Spacer(1, 2*mm))
    footer = Table([[P("DATA CIENTIFICAÇÃO:", "DanfseLabel"), P("IDENTIFICAÇÃO E ASSINATURA", "DanfseLabel"), P("Nº NFS-e / CHAVE NFS-e<br/>" + numero + " / " + chave, "DanfseTiny")]], colWidths=[48*mm, 65*mm, 90*mm], rowHeights=[10*mm])
    footer.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.6,colors.black),("INNERGRID",(0,0),(-1,-1),0.35,colors.black),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),3)]))
    story.append(footer)
    pdf.build(story)
    safe_number = re.sub(r"[^A-Za-z0-9_-]", "_", str(numero or nfse_id))
    return Response(content=output.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="nfse-{safe_number}.pdf"'})


@router.post("/consultar")
def consultar(body: ConsultarRequest, _user=Depends(current_user)):
    try:
        return service.consultar_a1(body.origem, body.entidade_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/a3/importar")
def importar_a3(body: ImportarA3Request, _user=Depends(current_user)):
    try:
        return service.importar_resposta_a3(body.origem, body.entidade_id, body.thumbprint_sha256, body.content_type, body.body_b64)
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
