from __future__ import annotations

import base64
import gzip
import json
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zlib
from decimal import Decimal, InvalidOperation
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterator

import httpx

from app.db.database import conectar_banco, STORAGE_BASE
from app.services.certificado_service import certificate_service

ADN_PROD = "https://adn.nfse.gov.br/contribuintes"
ADN_HML = "https://adn.producaorestrita.nfse.gov.br/contribuintes"
PROVIDER_NAME = "ADN_NFSE"


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "sim", "yes"}


def _provider_base_url() -> str:
    url = os.getenv("OMEGA_NFSE_ADN_URL", ADN_PROD).strip().rstrip("/")
    if url not in {ADN_PROD, ADN_HML}:
        raise ValueError("OMEGA_NFSE_ADN_URL deve apontar para o ADN de produção ou produção restrita.")
    return url


def _normalize_doc(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _subject(origin: str, entity_id: int) -> tuple[str, int]:
    origin = origin.upper()
    if origin not in {"PJ", "PF"}:
        raise ValueError("Origem inválida. Use PJ ou PF.")
    return origin, int(entity_id)


def _certificate_validity(cert: dict[str, Any]) -> datetime | None:
    """Interpret validity values stored by current and legacy certificate forms."""
    raw = cert.get("data_validade") or cert.get("validade")
    if raw is None:
        return None
    raw_text = str(raw).strip()
    if not raw_text:
        return None

    # Date-only values mean that the certificate remains valid through that day.
    date_formats = ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y%m%d")
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_text):
            value = datetime.fromisoformat(raw_text + "T23:59:59+00:00")
        else:
            value = None
            for fmt in date_formats:
                try:
                    day = datetime.strptime(raw_text, fmt)
                    value = day.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            if value is None:
                value = datetime.fromisoformat(raw_text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "sim", "on"}
    return bool(value)


def _certificate_problem(cert: dict[str, Any], now: datetime) -> str | None:
    cert_type = str(cert.get("tipo") or "").strip().upper()
    status = str(cert.get("status") or "").strip().upper()
    if cert_type not in {"A1", "A3"}:
        return "Tipo de certificado desconhecido."
    if status != "ATIVO":
        return f"Certificado cadastrado, mas status atual é {status or 'não informado'}."
    if not _truthy(cert.get("apto_para_uso")):
        return "O cadastro não está marcado como apto para uso. Abra Certificados e valide o cadastro."
    expiry = _certificate_validity(cert)
    if expiry is None:
        return "A validade não foi reconhecida. Reabra o cadastro do certificado e confira a data de validade."
    if expiry < now:
        return "Certificado vencido. Atualize ou substitua o certificado na aba Certificados."
    thumbprint = str(cert.get("thumbprint_sha256") or "").strip().lower()
    if cert_type == "A3" and not re.fullmatch(r"[0-9a-f]{64}", thumbprint):
        return "O A3 não possui thumbprint SHA-256 válido. Detecte novamente o cartão no OMEGA Bridge e salve o cadastro."
    # Os métodos públicos do repositório removem storage_ref intencionalmente.
    # Não validar essa referência aqui: isso faria todo A1 parecer ausente.
    # A disponibilidade real do PFX é validada pela fachada ao abrir o mTLS.
    return None


def _certificate_candidates(origin: str, entity_id: int) -> list[dict[str, Any]]:
    """Return safe diagnostic metadata; never include storage refs or secrets."""
    certs = (certificate_service.get_for_company(entity_id) if origin == "PJ"
             else certificate_service.get_for_pf(entity_id))
    now = datetime.now(timezone.utc)
    result = []
    for cert in certs:
        expiry = _certificate_validity(cert)
        result.append({
            "id": cert.get("id"),
            "tipo": str(cert.get("tipo") or "").upper(),
            "status": str(cert.get("status") or "NÃO INFORMADO").upper(),
            "validade": cert.get("data_validade"),
            "titular": cert.get("nome_titular") or cert.get("pessoa_nome"),
            "documento": cert.get("documento_titular") or cert.get("cnpj") or cert.get("cpf"),
            "apto_para_uso": _truthy(cert.get("apto_para_uso")),
            "selecionavel": _certificate_problem(cert, now) is None,
            "motivo": _certificate_problem(cert, now),
        })
    return result


def _active_certificate(origin: str, entity_id: int) -> dict[str, Any]:
    origin, entity_id = _subject(origin, entity_id)
    if origin == "PJ":
        certs = certificate_service.get_for_company(entity_id)
    else:
        certs = certificate_service.get_for_pf(entity_id)
    now = datetime.now(timezone.utc)
    active: list[tuple[datetime, dict[str, Any]]] = []
    for cert in certs:
        if _certificate_problem(cert, now) is not None:
            continue
        expiry = _certificate_validity(cert)
        if expiry is not None:
            active.append((expiry, cert))
    active.sort(key=lambda pair: pair[0], reverse=True)
    if not active:
        raise ValueError("Não foi encontrado certificado apto para NFS-e. Confira os certificados cadastrados e o motivo indicado na tela.")
    return active[0][1]


def _entity(origin: str, entity_id: int) -> dict[str, Any]:
    origin, entity_id = _subject(origin, entity_id)
    with conectar_banco() as conn:
        if origin == "PJ":
            row = conn.execute(
                "SELECT id, cnpj documento, razao_social nome, municipio, codigo_ibge, uf FROM empresas WHERE id=? AND ativo=1",
                (entity_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id, cpf documento, nome, NULL municipio, NULL codigo_ibge, NULL uf FROM pessoas_fisicas WHERE id=? AND ativo=1",
                (entity_id,),
            ).fetchone()
    if not row:
        raise LookupError("Titular não encontrado ou inativo.")
    return dict(row)


@contextmanager
def _a1_mtls_files(cert: dict[str, Any], origin: str) -> Iterator[tuple[Path, Path]]:
    with certificate_service.a1_mtls_files(cert["id"], origin) as paths:
        yield paths


def _adn_url(nsu: int) -> str:
    base = _provider_base_url()
    # Método oficial para contribuintes: GET /DFe/{NSU}.
    return f"{base}/DFe/{int(nsu)}?tipoNSU=DISTRIBUICAO&lote=true"


def _decode_xml_candidate(raw: Any) -> str | None:
    """Decode an ADN document payload (usually base64-encoded GZIP XML).

    Some test providers and older integrations may return plain XML or plain
    base64 XML. Prefer recognizing the payload before attempting base64 decode
    because base64.b64decode() without validate=True can silently ignore XML
    punctuation and corrupt a perfectly valid plain-text XML document.
    """
    if isinstance(raw, (bytes, bytearray)):
        data = bytes(raw)
        if data.startswith(b"\x1f\x8b"):
            try:
                data = gzip.decompress(data)
            except (OSError, EOFError, zlib.error):
                return None
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return None
        return text if text.lstrip().startswith("<") else None

    if not isinstance(raw, str) or not raw.strip():
        return None

    text = raw.lstrip("\ufeff\r\n\t ")
    if text.startswith("<"):
        return text

    # ADN can return base64 in JSON. Permit embedded whitespace/newlines while
    # still requiring a valid base64 alphabet.
    compact = "".join(raw.split())
    try:
        data = base64.b64decode(compact, validate=True)
    except (ValueError, base64.binascii.Error):
        return None

    if data.startswith(b"\x1f\x8b"):
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError, zlib.error):
            return None

    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    return decoded if decoded.lstrip().startswith("<") else None


def _xml_local_name(tag: Any) -> str:
    """Return an XML local name irrespective of namespace or prefix."""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].split(":")[-1].casefold()


def _xml_text_index(root: ET.Element) -> dict[str, list[str]]:
    """Index non-empty element text by local tag name (namespace agnostic)."""
    values: dict[str, list[str]] = {}
    for element in root.iter():
        name = _xml_local_name(element.tag)
        value = (element.text or "").strip()
        if name and value:
            values.setdefault(name, []).append(value)
    return values


def _first_xml_text(index: dict[str, list[str]], names: tuple[str, ...]) -> str | None:
    for name in names:
        for value in index.get(name.casefold(), []):
            if value.strip():
                return value.strip()
    return None


def _normalize_xml_date(value: Any) -> str | None:
    """Normalize supported date/time strings to ISO 8601 for storage/UI."""
    if value is None or isinstance(value, bool):
        return None
    raw = str(value).strip()
    if not raw:
        return None

    # Preserve date-only values as YYYY-MM-DD (without inventing a time).
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue

    iso_candidate = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
    try:
        return datetime.fromisoformat(iso_candidate).isoformat()
    except ValueError:
        return None


def _parse_xml_money(value: Any) -> float | None:
    """Parse XML/JSON monetary values without losing decimal separators.

    XML normally uses the decimal point (e.g. 1234.56); human-formatted
    fallback values may use Brazilian separators (e.g. 1.234,56).
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) else None

    raw = str(value).strip().replace("\u00a0", " ")
    raw = raw.replace("R$", "").replace(" ", "")
    if not raw:
        return None

    # If both separators are present, the last one is treated as the decimal
    # separator. This supports both 1.234,56 and 1,234.56.
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")

    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", raw):
        return None
    try:
        number = float(Decimal(raw))
    except (InvalidOperation, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _extract_xml_key(root: ET.Element, index: dict[str, list[str]]) -> str | None:
    direct = _first_xml_text(index, ("chaveAcesso", "chAcesso", "chave_acesso", "chaveNfse", "chaveNFSe"))
    if direct and re.fullmatch(r"\d{44}", re.sub(r"\D", "", direct)):
        return re.sub(r"\D", "", direct)

    # In some XML representations the key is encoded in an Id attribute.
    for element in root.iter():
        for attr_value in element.attrib.values():
            match = re.search(r"(?<!\d)(\d{44})(?!\d)", str(attr_value))
            if match:
                return match.group(1)

    for value in (text for texts in index.values() for text in texts):
        match = re.search(r"(?<!\d)(\d{44})(?!\d)", value)
        if match:
            return match.group(1)
    return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError, OverflowError):
        return None


def _mapping_value(item: dict[str, Any], *names: str) -> Any:
    """Read external ADN/provider fields without depending on JSON key casing."""
    for name in names:
        if name in item and item[name] not in (None, ""):
            return item[name]
    lowered = {str(key).casefold(): value for key, value in item.items()}
    for name in names:
        value = lowered.get(name.casefold())
        if value not in (None, ""):
            return value
    return None


_ADN_XML_PAYLOAD_KEYS = (
    "docZip", "doczip", "conteudo", "documento", "arquivoXml", "arquivo_xml",
    "xml", "xmlGzip", "conteudoXml", "arquivoXML",
)


def _parse_candidate_document(item: dict[str, Any], origin: str, subject_id: int) -> dict[str, Any]:
    raw_payload = _mapping_value(item, *_ADN_XML_PAYLOAD_KEYS)
    xml_text = _decode_xml_candidate(raw_payload)

    chave = _mapping_value(item, "chaveAcesso", "chave_acesso", "chave", "chNFe")
    if chave:
        normalized_key = re.sub(r"\D", "", str(chave))
        chave = normalized_key if re.fullmatch(r"\d{44}", normalized_key) else None
    numero = _mapping_value(item, "numero", "numeroNfse", "nNFSe", "numNfse", "nNF")
    data_emissao = None
    for date_key in ("dataEmissao", "data_emissao", "dhProc", "dhEmi", "dataEmissaoNfse"):
        data_emissao = _normalize_xml_date(_mapping_value(item, date_key))
        if data_emissao:
            break

    valor = None
    for value_key in ("valor", "valorServico", "valorServicoPrestado", "vServ", "vNFSe"):
        raw_value = _mapping_value(item, value_key)
        if raw_value not in (None, ""):
            valor = _parse_xml_money(raw_value)
            if valor is not None:
                break
    schema = _mapping_value(item, "schema", "Schema", "tipoDocumento")

    if xml_text:
        try:
            root = ET.fromstring(xml_text)
            index = _xml_text_index(root)

            if not chave:
                chave = _extract_xml_key(root, index)

            if not numero:
                numero = _first_xml_text(
                    index,
                    ("nNFSe", "NumeroNfse", "NumeroNFSe", "Numero", "nNF"),
                )

            # In the national NFS-e layout, dhProc indicates processing of the
            # generated NFS-e and dhEmi indicates the DPS emission timestamp.
            # Prefer the NFS-e processing timestamp, falling back to the DPS
            # timestamp and common provider aliases.
            if not data_emissao:
                for tag in (
                    "dhProc", "dhEmi", "dataEmissao", "dataEmissaoNfse",
                    "dataEmissaoNFSe", "dtEmissao", "dEmi", "dataHoraEmissao",
                ):
                    candidate = _first_xml_text(index, (tag,))
                    data_emissao = _normalize_xml_date(candidate)
                    if data_emissao:
                        break

            # Prefer the gross service value (vServ) rather than taxes or net
            # payable amounts. Aliases are fallbacks for other supported layouts.
            if valor is None:
                for tag in (
                    "vServ", "valorServico", "valorServicos", "valorServicoPrestado",
                    "vServPrest", "vNFSe", "valorNfse", "valorNFSe", "vLiq",
                ):
                    for candidate in index.get(tag.casefold(), []):
                        valor = _parse_xml_money(candidate)
                        if valor is not None:
                            break
                    if valor is not None:
                        break
        except ET.ParseError:
            # Keep the original payload available for diagnostics, but don't
            # fabricate metadata from malformed XML.
            pass

    return {
        "origin": origin,
        "subject_id": subject_id,
        "provider": PROVIDER_NAME,
        "nsu": _safe_int(_mapping_value(item, "nsu", "NSU", "numeroNSU")),
        "schema": schema,
        "chave_acesso": str(chave) if chave else None,
        "numero": str(numero).strip() if numero is not None else None,
        "data_emissao": data_emissao,
        "valor": valor,
        "situacao": "IMPORTADA",
        "xml": xml_text,
        "raw": item,
    }


def _has_unparsed_document_batch(payload: Any) -> bool:
    """Detect a non-empty known batch that yielded no recognized XML items.

    This prevents advancing the NSU cursor when ADN changes the XML payload
    field name and the response would otherwise look like an empty batch.
    """
    containers = {"lote", "lotedfe", "documentos", "documents", "dfe", "dfes"}
    stack = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                normalized = re.sub(r"[^a-z]", "", str(key).casefold())
                if normalized in containers:
                    if isinstance(value, list) and value:
                        return True
                    if isinstance(value, dict) and value:
                        return True
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            stack.extend(value for value in current if isinstance(value, (dict, list)))
    return False


def _extract_items(payload: Any) -> tuple[list[dict[str, Any]], int | None, int | None]:
    if not isinstance(payload, dict):
        return [], None, None
    ult_nsu = _mapping_value(payload, "ultNSU", "ultNsu", "ultimoNSU", "ultimo_nsu")
    max_nsu = _mapping_value(payload, "maxNSU", "maxNsu", "maximoNSU", "max_nsu")
    candidates: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            normalized_keys = {str(key).casefold() for key in value}
            if normalized_keys.intersection({key.casefold() for key in _ADN_XML_PAYLOAD_KEYS}):
                candidates.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(payload)
    def _int(v: Any) -> int | None:
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None
    return candidates, _int(ult_nsu), _int(max_nsu)


def _save_documents(origin: str, subject_id: int, documents: list[dict[str, Any]], response_raw: str) -> int:
    if not documents:
        return 0
    storage = STORAGE_BASE / "nfse" / origin.lower() / str(subject_id)
    storage.mkdir(parents=True, exist_ok=True)
    inserted = 0
    created_paths: list[Path] = []
    try:
        with conectar_banco() as conn:
            for doc in documents:
                nsu = doc.get("nsu")
                raw_json = json.dumps(doc.get("raw") or {}, ensure_ascii=False, default=str)
                if nsu is None and not doc.get("chave_acesso"):
                    raise ValueError("Documento fiscal sem NSU e sem chave de acesso; não é possível importar sem risco de duplicidade.")

                # Evita criar arquivos órfãos quando o NSU/chave já foi importado.
                if nsu is not None:
                    duplicate = conn.execute(
                        "SELECT id FROM nfse_documentos WHERE origem=? AND entidade_id=? AND provider=? AND nsu=? LIMIT 1",
                        (origin, subject_id, PROVIDER_NAME, nsu),
                    ).fetchone()
                elif doc.get("chave_acesso"):
                    duplicate = conn.execute(
                        "SELECT id FROM nfse_documentos WHERE origem=? AND entidade_id=? AND provider=? AND chave_acesso=? LIMIT 1",
                        (origin, subject_id, PROVIDER_NAME, doc["chave_acesso"]),
                    ).fetchone()
                else:
                    duplicate = None
                if duplicate:
                    continue

                xml_path = None
                if doc.get("xml"):
                    digest_source = doc.get("chave_acesso") or raw_json
                    digest = __import__("hashlib").sha256(digest_source.encode("utf-8", "replace")).hexdigest()[:24]
                    name = f"{nsu or 'sem-nsu'}-{digest}.xml"
                    path = storage / name
                    path.write_text(doc["xml"], encoding="utf-8")
                    created_paths.append(path)
                    xml_path = str(path.relative_to(STORAGE_BASE.parent))

                conn.execute(
                    """INSERT OR IGNORE INTO nfse_documentos
                    (origem, entidade_id, provider, nsu, schema, chave_acesso, numero,
                     data_emissao, valor, situacao, xml_path, resposta_json, criado_em, atualizado_em)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""",
                    (origin, subject_id, PROVIDER_NAME, nsu, doc.get("schema"), doc.get("chave_acesso"), doc.get("numero"),
                     doc.get("data_emissao"), doc.get("valor"), doc.get("situacao"), xml_path, raw_json),
                )
                changed = conn.execute("SELECT changes()").fetchone()[0]
                inserted += changed
                if not changed and xml_path:
                    try:
                        (STORAGE_BASE.parent / xml_path).unlink(missing_ok=True)
                    except OSError:
                        pass
            conn.commit()
    except Exception:
        # A transação será revertida pelo context manager; remover arquivos que
        # pertenciam a esta tentativa para não deixar XMLs órfãos no storage.
        for path in created_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return inserted


def _cursor(origin: str, subject_id: int) -> dict[str, Any]:
    with conectar_banco() as conn:
        row = conn.execute(
            "SELECT * FROM nfse_sync WHERE origem=? AND entidade_id=? AND provider=?",
            (origin, subject_id, PROVIDER_NAME),
        ).fetchone()
        if row:
            return dict(row)
        conn.execute(
            "INSERT INTO nfse_sync(origem,entidade_id,provider,ultimo_nsu,status) VALUES(?,?,?,?,?)",
            (origin, subject_id, PROVIDER_NAME, 0, "PRONTO"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM nfse_sync WHERE origem=? AND entidade_id=? AND provider=?",
            (origin, subject_id, PROVIDER_NAME),
        ).fetchone()
        return dict(row)


def contexto(origin: str, entity_id: int) -> dict[str, Any]:
    origin, entity_id = _subject(origin, entity_id)
    entity = _entity(origin, entity_id)
    cursor = _cursor(origin, entity_id)
    cert: dict[str, Any] | None
    certificate_message = None
    candidates = _certificate_candidates(origin, entity_id)
    try:
        cert = _active_certificate(origin, entity_id)
    except ValueError as exc:
        # A listagem de documentos deve continuar acessível mesmo que o titular
        # ainda não tenha certificado utilizável. Também devolvemos diagnóstico
        # seguro para distinguir cadastro inexistente de cadastro não apto.
        cert = None
        if not candidates:
            certificate_message = "Nenhum certificado foi encontrado para este titular no ÔMEGA. Cadastre o A1/A3 na aba Certificados."
        else:
            details = "; ".join(f"{item['tipo']} (#{item['id']}): {item['motivo']}" for item in candidates)
            certificate_message = details or str(exc)
    return {
        "origem": origin,
        "entidade_id": entity_id,
        "entidade": entity,
        "certificados_cadastrados": candidates,
        "certificado": ({
            "id": cert["id"],
            "tipo": cert["tipo"],
            "meio_armazenamento": cert["meio_armazenamento"],
            "titular": cert.get("nome_titular"),
            "documento": cert.get("documento_titular"),
            "validade": cert.get("data_validade"),
            "thumbprint_sha256": cert.get("thumbprint_sha256"),
        } if cert else None),
        "mensagem_certificado": certificate_message,
        "provider": PROVIDER_NAME,
        "ambiente": "PRODUÇÃO" if _provider_base_url() == ADN_PROD else "PRODUÇÃO RESTRITA",
        "ultimo_nsu": cursor["ultimo_nsu"],
        "ultimo_sync": cursor.get("ultimo_sync"),
        "status": cursor.get("status"),
    }


def _request_a1(origin: str, entity_id: int, cert: dict[str, Any], nsu: int) -> tuple[int, str, str]:
    url = _adn_url(nsu)
    timeout = float(os.getenv("OMEGA_NFSE_TIMEOUT", "60"))
    with _a1_mtls_files(cert, origin) as (cert_file, key_file):
        with httpx.Client(timeout=timeout, cert=(str(cert_file), str(key_file)), verify=True, follow_redirects=True) as client:
            response = client.get(url)
    return response.status_code, response.headers.get("content-type", ""), response.text


def _update_cursor(origin: str, subject_id: int, ultimo_nsu: int | None, max_nsu: int | None, status: str, message: str | None = None) -> None:
    with conectar_banco() as conn:
        conn.execute(
            """UPDATE nfse_sync SET
            ultimo_nsu=CASE WHEN ? IS NULL THEN ultimo_nsu ELSE MAX(ultimo_nsu, ?) END,
            max_nsu=CASE WHEN ? IS NULL THEN max_nsu WHEN max_nsu IS NULL THEN ? ELSE MAX(max_nsu, ?) END,
            ultimo_sync=CURRENT_TIMESTAMP,
            status=?, mensagem=?, proxima_consulta_em=?
            WHERE origem=? AND entidade_id=? AND provider=?""",
            (ultimo_nsu, ultimo_nsu, max_nsu, max_nsu, max_nsu, status, message,
             (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat() if status == "SEM_DOCUMENTOS" else None,
             origin, subject_id, PROVIDER_NAME),
        )
        conn.commit()


def _begin_sync(origin: str, entity_id: int, cursor: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    status = cursor.get("status")
    observed_updated = cursor.get("atualizado_em")
    stale_lock = False
    if status == "CONSULTANDO":
        try:
            updated = datetime.fromisoformat(str(observed_updated).replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            stale_lock = now - updated > timedelta(minutes=10)
        except (TypeError, ValueError):
            stale_lock = False
        if not stale_lock:
            raise ValueError("Já existe uma consulta NFS-e em andamento para este titular. Se ela foi interrompida, aguarde 10 minutos e tente novamente.")

    next_at = cursor.get("proxima_consulta_em")
    if next_at:
        try:
            dt = datetime.fromisoformat(str(next_at).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > now:
                remaining = max(1, int((dt - now).total_seconds() // 60))
                raise ValueError(f"A fila do ADN está em espera. Tente novamente em aproximadamente {remaining} minuto(s).")
        except ValueError as exc:
            if str(exc).startswith("A fila do ADN"):
                raise

    with conectar_banco() as conn:
        if stale_lock:
            cur = conn.execute(
                "UPDATE nfse_sync SET status='CONSULTANDO', mensagem='Retomada após consulta interrompida', "
                "atualizado_em=strftime('%Y-%m-%d %H:%M:%f','now') "
                "WHERE origem=? AND entidade_id=? AND provider=? AND status='CONSULTANDO' AND atualizado_em=?",
                (origin, entity_id, PROVIDER_NAME, observed_updated),
            )
        else:
            cur = conn.execute(
                "UPDATE nfse_sync SET status='CONSULTANDO', mensagem=NULL, "
                "atualizado_em=strftime('%Y-%m-%d %H:%M:%f','now') "
                "WHERE origem=? AND entidade_id=? AND provider=? AND status!='CONSULTANDO'",
                (origin, entity_id, PROVIDER_NAME),
            )
        conn.commit()
        if cur.rowcount != 1:
            raise ValueError("Já existe uma consulta NFS-e em andamento para este titular.")


def consultar_a1(origin: str, entity_id: int) -> dict[str, Any]:
    origin, entity_id = _subject(origin, entity_id)
    cert = _active_certificate(origin, entity_id)
    if cert["tipo"] != "A1":
        raise ValueError("O certificado ativo não é A1. Para A3, use a opção de consulta pelo Bridge.")

    cursor = _cursor(origin, entity_id)
    _begin_sync(origin, entity_id, cursor)

    current_nsu = int(cursor.get("ultimo_nsu") or 0)
    previous_max = cursor.get("max_nsu")
    total_found = 0
    total_inserted = 0
    max_batches = 100

    for batch_number in range(max_batches):
        try:
            status_code, content_type, body = _request_a1(
                origin, entity_id, cert, current_nsu
            )
        except Exception as exc:
            _update_cursor(
                origin, entity_id, current_nsu, previous_max,
                "ERRO_API", str(exc)
            )
            raise

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            _update_cursor(
                origin, entity_id, current_nsu, previous_max,
                "ERRO_RESPOSTA",
                f"Resposta do ADN não é JSON válido (content-type: {content_type})."
            )
            raise ValueError(
                "O ADN retornou uma resposta inválida; cursor preservado."
            ) from exc

        if not isinstance(payload, dict):
            _update_cursor(
                origin, entity_id, current_nsu, previous_max,
                "ERRO_RESPOSTA", "Resposta do ADN em formato inesperado."
            )
            raise ValueError("Resposta do ADN em formato inesperado.")

        items, ult_nsu, max_nsu = _extract_items(payload)
        errors = payload.get("Erros") or []
        error_codes = {
            str(item.get("Codigo", "")).upper()
            for item in errors if isinstance(item, dict)
        }
        no_documents = (
            payload.get("StatusProcessamento") == "NENHUM_DOCUMENTO_LOCALIZADO"
            or "E2220" in error_codes
        )

        if status_code >= 400 and no_documents and not items:
            _update_cursor(
                origin, entity_id, current_nsu,
                max_nsu if max_nsu is not None else previous_max,
                "SEM_DOCUMENTOS", None
            )
            certificate_service.record_usage(cert["id"], "NFS-E", origin=origin)
            return {
                "ok": True,
                "provider": PROVIDER_NAME,
                "certificado_tipo": "A1",
                "http_status": status_code,
                "documentos_encontrados": total_found,
                "documentos_importados": total_inserted,
                "ultimo_nsu": current_nsu,
                "max_nsu": max_nsu if max_nsu is not None else previous_max,
                "content_type": content_type,
                "lotes_consultados": batch_number + 1,
                "fim_da_fila": True,
            }

        if status_code >= 400:
            _update_cursor(
                origin, entity_id, current_nsu, previous_max,
                "ERRO_API", f"ADN HTTP {status_code}: {body[:500]}"
            )
            raise ValueError(
                f"ADN respondeu HTTP {status_code}. Verifique a mensagem registrada."
            )

        if not items and _has_unparsed_document_batch(payload):
            _update_cursor(
                origin, entity_id, current_nsu, previous_max,
                "ERRO_LAYOUT", "Lote não vazio sem campo XML reconhecido."
            )
            raise ValueError(
                "Lote do ADN sem campo XML reconhecido; cursor preservado."
            )

        documents = [
            _parse_candidate_document(item, origin, entity_id)
            for item in items
        ]

        try:
            inserted = _save_documents(origin, entity_id, documents, body)
        except Exception as exc:
            _update_cursor(
                origin, entity_id, current_nsu, previous_max,
                "ERRO_IMPORTACAO", "Falha ao salvar documentos do ADN."
            )
            raise ValueError(
                "Falha ao salvar documentos; cursor preservado para nova tentativa."
            ) from exc

        total_found += len(documents)
        total_inserted += inserted

        received_nsus = [
            _safe_int(doc.get("nsu")) for doc in documents
        ]
        received_nsus = [
            value for value in received_nsus
            if value is not None and value >= 0
        ]

        candidates = [
            value for value in (ult_nsu, max(received_nsus) if received_nsus else None)
            if value is not None
        ]
        next_nsu = max(candidates) if candidates else current_nsu

        if not documents:
            _update_cursor(
                origin, entity_id, current_nsu,
                max_nsu if max_nsu is not None else previous_max,
                "SEM_DOCUMENTOS", None
            )
            certificate_service.record_usage(cert["id"], "NFS-E", origin=origin)
            return {
                "ok": True,
                "provider": PROVIDER_NAME,
                "certificado_tipo": "A1",
                "http_status": status_code,
                "documentos_encontrados": total_found,
                "documentos_importados": total_inserted,
                "ultimo_nsu": current_nsu,
                "max_nsu": max_nsu if max_nsu is not None else previous_max,
                "content_type": content_type,
                "lotes_consultados": batch_number + 1,
                "fim_da_fila": True,
            }

        if next_nsu <= current_nsu:
            _update_cursor(
                origin, entity_id, current_nsu, previous_max,
                "ERRO_CURSOR",
                "O lote trouxe documentos, mas não confirmou avanço do NSU."
            )
            raise ValueError(
                "O ADN retornou documentos sem avanço confirmado do NSU; "
                "a consulta foi interrompida para evitar repetição infinita."
            )

        current_nsu = next_nsu
        if max_nsu is not None:
            previous_max = max_nsu

        _update_cursor(
            origin, entity_id, current_nsu, previous_max,
            "CONSULTANDO", None
        )

    _update_cursor(
        origin, entity_id, current_nsu, previous_max,
        "DOCUMENTOS_IMPORTADOS",
        "Limite de segurança de 100 lotes atingido; execute nova consulta para continuar."
    )
    certificate_service.record_usage(cert["id"], "NFS-E", origin=origin)
    return {
        "ok": True,
        "provider": PROVIDER_NAME,
        "certificado_tipo": "A1",
        "documentos_encontrados": total_found,
        "documentos_importados": total_inserted,
        "ultimo_nsu": current_nsu,
        "max_nsu": previous_max,
        "lotes_consultados": max_batches,
        "fim_da_fila": False,
    }


def importar_resposta_a3(origin: str, entity_id: int, thumbprint: str, content_type: str, body_b64: str) -> dict[str, Any]:
    origin, entity_id = _subject(origin, entity_id)
    cert = _active_certificate(origin, entity_id)
    if cert["tipo"] != "A3":
        raise ValueError("O certificado ativo deste titular não é A3.")
    if cert.get("thumbprint_sha256", "").lower() != thumbprint.lower():
        raise ValueError("O certificado A3 detectado no cartão não corresponde ao certificado cadastrado no ÔMEGA.")
    try:
        body = base64.b64decode(body_b64, validate=True)
    except Exception as exc:
        raise ValueError("Resposta do Bridge inválida.") from exc
    text = body.decode("utf-8", "replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("O Bridge retornou conteúdo que não é JSON válido. Nenhum NSU foi avançado.") from exc
    if not isinstance(payload, dict):
        raise ValueError("O Bridge retornou uma estrutura NFS-e inesperada. Nenhum NSU foi avançado.")
    items, ult_nsu, max_nsu = _extract_items(payload)
    cursor = _cursor(origin, entity_id)
    if not items and _has_unparsed_document_batch(payload):
        _update_cursor(origin, entity_id, cursor.get("ultimo_nsu"), cursor.get("max_nsu"), "ERRO_LAYOUT", "Lote não vazio sem campo XML reconhecido.")
        raise ValueError("A resposta A3 contém um lote de documentos sem um campo XML reconhecido. O NSU foi preservado para nova tentativa.")
    documents = [_parse_candidate_document(item, origin, entity_id) for item in items]
    try:
        inserted = _save_documents(origin, entity_id, documents, text)
    except Exception as exc:
        _update_cursor(origin, entity_id, cursor.get("ultimo_nsu"), cursor.get("max_nsu"), "ERRO_IMPORTACAO", "Falha ao persistir os documentos recebidos pelo Bridge.")
        raise ValueError("A resposta A3 foi recebida, mas ocorreu uma falha ao salvar os documentos. O NSU foi preservado para nova tentativa.") from exc
    _update_cursor(origin, entity_id, ult_nsu if ult_nsu is not None else cursor["ultimo_nsu"], max_nsu, "DOCUMENTOS_IMPORTADOS" if documents else "SEM_DOCUMENTOS", None)
    certificate_service.record_usage(cert["id"], "NFS-E", origin=origin)
    return {"ok": True, "provider": PROVIDER_NAME, "certificado_tipo": "A3", "documentos_encontrados": len(documents), "documentos_importados": inserted, "ultimo_nsu": ult_nsu, "max_nsu": max_nsu, "content_type": content_type}


def listar(origin: str | None = None, entity_id: int | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 500))
    offset = max(0, int(offset))
    with conectar_banco() as conn:
        sql = "SELECT * FROM nfse_documentos WHERE 1=1"
        params: list[Any] = []
        if origin:
            sql += " AND origem=?"; params.append(origin.upper())
        if entity_id is not None:
            sql += " AND entidade_id=?"; params.append(entity_id)
        sql += " ORDER BY COALESCE(data_emissao, criado_em, '') DESC, id DESC LIMIT ? OFFSET ?"; params.extend([limit, offset])
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def detalhe(nfse_id: int) -> dict[str, Any]:
    with conectar_banco() as conn:
        row = conn.execute("SELECT * FROM nfse_documentos WHERE id=?", (nfse_id,)).fetchone()
    if not row:
        raise LookupError("NFS-e não encontrada.")
    result = dict(row)
    if result.get("xml_path"):
        path = STORAGE_BASE.parent / result["xml_path"]
        if path.is_file():
            result["xml"] = path.read_text(encoding="utf-8", errors="replace")
    return result
