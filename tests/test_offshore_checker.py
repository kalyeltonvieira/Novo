"""
Testes Unitários do Verificador Offshore e Laranjas
===================================================
"""

import pytest
from core.offshore_checker import OffshoreChecker


def test_verificar_socio_offshore():
    checker = OffshoreChecker()
    socio = {
        "id": "s1",
        "nome": "John Doe",
        "pais_residencia": "British Virgin Islands",
        "renda_estimada": 50000.0,
        "valor_contrato_empresa": 1000000.0
    }
    res = checker.verificar_socio_offshore(socio)
    assert res["is_offshore"] is True
    assert "ALERTA" in res["alerta"]


def test_verificar_suspeita_laranja():
    checker = OffshoreChecker()
    socio = {
        "id": "s2",
        "nome": "José da Silva",
        "pais_residencia": "Brasil",
        "renda_estimada": 1412.0,  # Salário mínimo
        "valor_contrato_empresa": 2000000.0
    }
    res = checker.verificar_socio_offshore(socio)
    assert res["suspeita_laranja"] is True
    assert "ALERTA" in res["alerta"]
