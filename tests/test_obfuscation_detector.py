"""
Testes Unitários do Detector de Ofuscação
==========================================
"""

import pytest
from core.obfuscation_detector import ObfuscationDetector


def test_analisar_ocultacao_dom_detectado():
    detector = ObfuscationDetector()
    html = '<div style="display: none;">Contrato nº 123 - Valor R$ 500.000</div>'
    res = detector.analisar_ocultacao_dom(html)
    assert res["possui_ofuscacao"] is True
    assert len(res["alertas_ofuscacao"]) >= 1


def test_analisar_ocultacao_dom_limpo():
    detector = ObfuscationDetector()
    html = '<div class="contrato">Contrato nº 123 - Valor R$ 500.000</div>'
    res = detector.analisar_ocultacao_dom(html)
    assert res["possui_ofuscacao"] is False
