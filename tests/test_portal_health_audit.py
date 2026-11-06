"""
Testes Unitários do Avaliador LAI
==================================
"""

import pytest
from core.portal_health_audit import PortalHealthAuditor


def test_calcular_indice_lai_excelente():
    auditor = PortalHealthAuditor()
    features = {
        "tem_busca_funcional": True,
        "possui_dados_abertos_csv": True,
        "atualizado_ultimo_mes": True,
        "tempo_resposta_ms": 500
    }
    res = auditor.calcular_indice_lai(features)
    assert res["score_lai"] == 100.0
    assert res["classificacao"] == "EXCELENTE"


def test_calcular_indice_lai_insatisfatorio():
    auditor = PortalHealthAuditor()
    features = {
        "tem_busca_funcional": False,
        "possui_dados_abertos_csv": False,
        "atualizado_ultimo_mes": False,
        "tempo_resposta_ms": 5000
    }
    res = auditor.calcular_indice_lai(features)
    assert res["score_lai"] == 0.0
    assert res["classificacao"] == "INSATISFATÓRIO"
    assert len(res["recomendacoes"]) >= 2
