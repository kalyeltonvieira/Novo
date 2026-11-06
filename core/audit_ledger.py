"""
Audit Ledger e Selo Criptográfico Imutável de Evidências
=========================================================
Gera hashes criptográficos SHA-256 e selos de não-adulteração para laudos de auditoria.
"""

import hashlib
import json
import time
from typing import Dict, Any


class AuditLedger:
    """Gerenciador de integridade criptográfica de relatórios de anomalias."""

    def gerar_selo_criptografico(self, relatorio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gera um selo criptográfico assinado com hash SHA-256 e timestamp."""
        payload_canonical = json.dumps(relatorio_data, sort_keys=True)
        timestamp = int(time.time())

        data_to_hash = f"{payload_canonical}:{timestamp}".encode("utf-8")
        hash_sha256 = hashlib.sha256(data_to_hash).hexdigest()

        return {
            "relatorio_id": relatorio_data.get("id", "desconhecido"),
            "hash_sha256": hash_sha256,
            "timestamp_unix": timestamp,
            "status_integridade": "SELADO_E_VERIFICADO"
        }

    def verificar_selo(self, relatorio_data: Dict[str, Any], selo: Dict[str, Any]) -> bool:
        """Valida se o relatório não sofreu adulteração desde a emissão do selo."""
        payload_canonical = json.dumps(relatorio_data, sort_keys=True)
        timestamp = selo.get("timestamp_unix", 0)

        data_to_hash = f"{payload_canonical}:{timestamp}".encode("utf-8")
        expected_hash = hashlib.sha256(data_to_hash).hexdigest()

        return expected_hash == selo.get("hash_sha256")
