"""
Testes Unitários do Gerador Peças Jurídicas
============================================
"""

import pytest
from core.legal_generator import LegalReportGenerator


def test_gerar_noticia_de_fato():
    generator = LegalReportGenerator()
    anomalia = {
        "titulo": "Nepotismo em Contrato Público",
        "descricao": "Contrato administrativo firmado com parente do Secretário de Obras.",
        "valor_envolvido": 750000.0,
        "orgao": "Prefeitura de São Paulo"
    }

    peca = generator.gerar_noticia_de_fato(anomalia)
    assert "PROCURADOR DA REPÚBLICA" in peca
    assert "Prefeitura de São Paulo" in peca
    assert "750,000.00" in peca or "750000" in peca
    assert "14.133/2021" in peca
