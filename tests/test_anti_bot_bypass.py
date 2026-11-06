"""
Testes Unitários do Bypass Anti-Bot
====================================
"""

import pytest
from core.anti_bot_bypass import AntiBotBypass


def test_obter_user_agent_aleatorio():
    bypass = AntiBotBypass()
    ua = bypass.obter_user_agent_aleatorio()
    assert "Mozilla" in ua


def test_resolver_desafio_numerico():
    bypass = AntiBotBypass()
    res = bypass.resolver_desafio_numerico("Quanto é 12 + 8?")
    assert res == 20

    res_sub = bypass.resolver_desafio_numerico("Quanto é 15 - 5?")
    assert res_sub == 10
