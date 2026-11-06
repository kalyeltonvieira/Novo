"""
Testes Unitários do Audit Ledger Criptográfico
===============================================
"""

import pytest
from core.audit_ledger import AuditLedger


def test_gerar_e_verificar_selo():
    ledger = AuditLedger()
    relatorio = {
        "id": "rel_001",
        "auditor": "Dr. Silva",
        "anomalia": "Superfaturamento"
    }

    selo = ledger.gerar_selo_criptografico(relatorio)
    assert selo["status_integridade"] == "SELADO_E_VERIFICADO"
    assert len(selo["hash_sha256"]) == 64

    # Verifica integridade VÁLIDA
    assert ledger.verificar_selo(relatorio, selo) is True

    # Adulteração de dados deve FALHAR
    relatorio_adulterado = relatorio.copy()
    relatorio_adulterado["anomalia"] = "Nenhuma (Adulterado)"
    assert ledger.verificar_selo(relatorio_adulterado, selo) is False
