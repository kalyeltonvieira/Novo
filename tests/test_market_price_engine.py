"""
Testes Unitários da Engine de Preço Médio
==========================================
"""

import pytest
from core.market_price_engine import MarketPriceEngine


def test_avaliar_sobrepreco_detectado():
    engine = MarketPriceEngine()
    # Resma de papel R$ 50 (referência R$ 25 => +100% desvio)
    res = engine.avaliar_sobrepreco("Resma Papel A4 alcalino", 50.0)
    assert res["sobrepreco"] is True
    assert res["percentual_desvio"] == 100.0
    assert "ALERTA" in res["alerta"]


def test_avaliar_preco_regular():
    engine = MarketPriceEngine()
    res = engine.avaliar_sobrepreco("Gasolina litro comum", 5.90)
    assert res["sobrepreco"] is False
    assert "regular" in res["alerta"].lower()
