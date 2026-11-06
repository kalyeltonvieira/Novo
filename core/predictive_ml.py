"""
Engine de Machine Learning Preditivo de Fraudes em Licitações
==============================================================
Calcula o Score de Risco Preditivo (0.0 a 1.0) antes da assinatura do contrato.
"""

from typing import Dict, Any, List


class PredictiveFraudEngine:
    """Calculador preditivo de risco de fraudes em editais e contratos."""

    def calcular_score_risco(self, edital_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula o risco preditivo de fraude baseado em atributos históricos.
        
        Features consideradas:
        - prazo_edital_dias (int)
        - valor_estimado (float)
        - possui_exigencia_marca (bool)
        - empresa_recem_criada (bool)
        - quantidade_participantes (int)
        """
        score = 0.1  # Risco base inicial

        prazo = edital_features.get("prazo_edital_dias", 30)
        if prazo < 8:
            score += 0.35  # Edital com prazo extremamente curto

        if edital_features.get("possui_exigencia_marca", False):
            score += 0.25  # Direcionamento de marca específica

        if edital_features.get("empresa_recem_criada", False):
            score += 0.20  # Empresa criada a menos de 180 dias

        participantes = edital_features.get("quantidade_participantes", 5)
        if participantes <= 1:
            score += 0.15  # Licitação deserta ou com único participante

        # Clampa o score entre 0.0 e 1.0
        score_final = min(max(score, 0.0), 1.0)
        
        nivel_risco = "BAIXO"
        if score_final > 0.7:
            nivel_risco = "ALTO (CRÍTICO)"
        elif score_final > 0.4:
            nivel_risco = "MÉDIO"

        return {
            "score_preditivo": round(score_final, 2),
            "nivel_risco": nivel_risco,
            "fatores_relevantes": self._gerar_explicabilidade(edital_features)
        }

    def _gerar_explicabilidade(self, features: Dict[str, Any]) -> List[str]:
        fatores = []
        if features.get("prazo_edital_dias", 30) < 8:
            fatores.append("Prazo de edital inferior ao mínimo recomendado de 8 dias.")
        if features.get("possui_exigencia_marca", False):
            fatores.append("Exigência explícita de marca ou especificação restritiva.")
        if features.get("empresa_recem_criada", False):
            fatores.append("Vencedora em potencial é uma empresa criada recentemente.")
        return fatores
