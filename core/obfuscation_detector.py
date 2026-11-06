"""
Detector de Ofuscação de Dados Públicos
========================================
Identifica quando informações no Frontend são propositalmente ocultadas via CSS/Imagens.
"""

import re
from typing import Dict, Any, List


class ObfuscationDetector:
    """Detector de técnicas de ocultação de informações de interesse público."""

    def analisar_ocultacao_dom(self, html_content: str) -> Dict[str, Any]:
        """Detecta elementos ocultos no DOM via CSS ou atributos de estilo."""
        alertas = []

        # Procura estilos de ocultação em elementos contendo palavras de valor/contrato
        if re.search(r'style=["\'].*?display\s*:\s*none.*?["\'].*?(?:contrato|valor|rs|cpf|cnpj)', html_content, re.IGNORECASE):
            alertas.append("Tentativa de ocultar contrato/valor utilizando 'display: none'.")

        if re.search(r'style=["\'].*?visibility\s*:\s*hidden.*?["\'].*?(?:contrato|valor|rs|cpf|cnpj)', html_content, re.IGNORECASE):
            alertas.append("Tentativa de ocultar informações utilizando 'visibility: hidden'.")

        return {
            "possui_ofuscacao": len(alertas) > 0,
            "alertas_ofuscacao": alertas
        }
