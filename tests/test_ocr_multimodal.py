"""
Testes Unitários do OCR Multimodal
===================================
"""

import pytest
from core.ocr_multimodal import OCRMultimodalProcessor


def test_ocr_multimodal_processador():
    processor = OCRMultimodalProcessor()
    res = processor.extrair_texto_imagem("caminho_inexistente.png")
    assert res["status"] == "erro"


def test_detectar_rasuras_texto():
    processor = OCRMultimodalProcessor()
    anomalias = processor._detectar_rasuras("Valor pago: R$ 50.000 ### CANCELADO ###")
    assert len(anomalias) >= 1
