
from __future__ import annotations

from typing import Any

from app.modules.certificados import service as repository


class CertificateService:
    """Façade única para módulos consumidores.

    NFS-e/SEFAZ/eSocial não devem acessar storage, PFX, PC/SC, PKCS#11 ou PIN.
    Esta camada expõe apenas identidade, validação, uso e assinatura futura.
    """

    def get(self, certificado_id: int) -> dict[str, Any]:
        return repository.obter(certificado_id)

    def get_for_company(self, empresa_id: int, tipo: str | None = None) -> list[dict[str, Any]]:
        return repository.listar(empresa_id, tipo)

    def validate_for_use(self, certificado_id: int) -> dict[str, Any]:
        cert = repository.obter(certificado_id)
        if not cert["apto_para_uso"]:
            raise ValueError("O certificado não está apto para uso.")
        if cert["status"] != "ATIVO":
            raise ValueError("O certificado não está ativo.")
        return cert

    def record_usage(self, certificado_id: int, modulo: str) -> None:
        repository.registrar_uso(certificado_id, modulo)

    def identity(self, certificado_id: int) -> dict[str, Any]:
        cert = self.validate_for_use(certificado_id)
        return {
            "certificado_id": cert["id"],
            "empresa_id": cert["empresa_id"],
            "tipo": cert["tipo"],
            "titular": cert["nome_titular"],
            "documento": cert["documento_titular"],
            "emissor": cert["emissor"],
            "numero_serie": cert["numero_serie"],
            "thumbprint_sha256": cert["thumbprint_sha256"],
            "validade": cert["data_validade"],
        }


certificate_service = CertificateService()
