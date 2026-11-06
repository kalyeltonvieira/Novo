"""
Engine de Preço Médio de Mercado (Benchmarking de Compras Públicas)
====================================================================
Compara preços de itens licitados com a curva nacional de valores praticados.
"""

from typing import Dict, Any, List

# Tabela mock de preços de referência de mercado nacional
PRECOS_REFERENCIA_NACIONAL = {
    "caneta esferográfica": 1.50,
    "resma papel a4": 25.00,
    "computador i5 16gb": 3500.00,
    "asfalto tonelada": 450.00,
    "cesta básica": 120.00,
    "gasolina litro": 5.80
}


class MarketPriceEngine:
    """Motor de cálculo de benchmarking e desvio de preço de mercado."""

    def avaliar_sobrepreco(self, item_nome: str, valor_unitario: float) -> Dict[str, Any]:
        """Avalia se um valor unitário possui sobrepreço em relação à média nacional."""
        nome_lower = item_nome.lower()
        preco_ref = None

        for ref_key, ref_val in PRECOS_REFERENCIA_NACIONAL.items():
            if ref_key in nome_lower:
                preco_ref = ref_val
                break

        if not preco_ref:
            return {
                "item": item_nome,
                "valor_unitario": valor_unitario,
                "status": "sem_referencia",
                "percentual_desvio": 0.0
            }

        percentual_desvio = ((valor_unitario - preco_ref) / preco_ref) * 100.0
        sobrepreco = percentual_desvio > 25.0  # Tolerância máxima de 25%

        return {
            "item": item_nome,
            "valor_unitario": valor_unitario,
            "preco_referencia": preco_ref,
            "percentual_desvio": round(percentual_desvio, 2),
            "sobrepreco": sobrepreco,
            "alerta": f"ALERTA: Sobrepreço de {percentual_desvio:.1f}% em relação ao mercado (Ref: R$ {preco_ref:.2f})" if sobrepreco else "Preço regular"
        }
