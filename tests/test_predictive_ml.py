"""
Testes Unitários da Engine Preditiva de Fraudes
================================================
"""

import pytest
from core.predictive_ml import PredictiveFraudEngine


def test_calcular_score_risco_alto():
    engine = PredictiveFraudEngine()
    features = {
        "prazo_edital_dias": 3,
        "possui_exigencia_marca": True,
        "empresa_recem_criada": True,
        "quantidade_participantes": 1
    }
    resultado = engine.calcular_score_risco(features)
    assert resultado["score_preditivo"] > 0.7
    assert resultado["nivel_risco"] == "ALTO (CRÍTICO)"
    assert len(resultado["fatores_relevantes"]) >= 3


def test_calcular_score_risco_baixo():
    engine = PredictiveFraudEngine()
    features = {
        "prazo_edital_dias": 45,
        "possui_exigencia_marca": False,
        "empresa_recem_criada": False,
        "quantidade_participantes": 8
    }
    resultado = engine.calcular_score_risco(features)
    assert resultado["score_preditivo"] <= 0.3
    assert resultado["nivel_risco"] == "BAIXO"
