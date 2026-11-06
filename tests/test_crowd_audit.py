"""
Testes Unitários da Auditoria Colaborativa (Crowd Audit)
=========================================================
"""

import pytest
from core.crowd_audit import CrowdAuditManager


def test_crowd_audit_adicionar_e_consultar():
    manager = CrowdAuditManager()
    manager.adicionar_anotacao("alt_001", "jornalista_ana", "Confirmei os dados no Diário Oficial de ontem.")
    
    anotacoes = manager.obter_anotacoes_alerta("alt_001")
    assert len(anotacoes) == 1
    assert anotacoes[0]["usuario"] == "jornalista_ana"
    assert anotacoes[0]["voto"] == "concordo"
