"""
Testes do Loop de Auto-Crítica dos Agentes (Multi-Agent Reflection)
====================================================================
"""

import pytest
from unittest.mock import MagicMock
from core.agentes.supervisor import SupervisorRouter


def test_reflection_valida_anomalia_forte():
    ai_manager = MagicMock()
    supervisor = SupervisorRouter(ai_manager=ai_manager, especialistas=[])

    anomalia = {
        "titulo": "Suspeita de Cartel",
        "severidade": "critica",
        "score_confianca": 0.85
    }

    resultado = supervisor.refletir_e_validar_anomalia(anomalia)
    assert resultado["status"] == "validado"
    assert "sustentada" in resultado["critica_revisor"]


def test_reflection_rejeita_falso_positivo():
    ai_manager = MagicMock()
    supervisor = SupervisorRouter(ai_manager=ai_manager, especialistas=[])

    anomalia = {
        "titulo": "Valor acima da média",
        "severidade": "baixa",
        "score_confianca": 0.2
    }

    resultado = supervisor.refletir_e_validar_anomalia(anomalia)
    assert resultado["status"] == "falso_positivo"
    assert "insuficiente" in resultado["critica_revisor"]
