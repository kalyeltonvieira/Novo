"""
Avaliador de Conformidade LAI e Saúde do Portal de Transparência
================================================================
Calcula o Índice de Transparência Digital (0 a 100) baseado na Lei nº 12.527/2011.
"""

from typing import Dict, Any, List


class PortalHealthAuditor:
    """Calculador de nota de transparência de portais públicos."""

    def calcular_indice_lai(self, portal_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Avalia os critérios obrigatórios da LAI:
        - tem_busca_funcional (bool)
        - possui_dados_abertos_csv (bool)
        - atualizado_ultimo_mes (bool)
        - tempo_resposta_ms (int)
        """
        score = 0.0

        if portal_features.get("tem_busca_funcional", False):
            score += 30.0

        if portal_features.get("possui_dados_abertos_csv", False):
            score += 30.0

        if portal_features.get("atualizado_ultimo_mes", False):
            score += 25.0

        tempo = portal_features.get("tempo_resposta_ms", 1500)
        if tempo < 2000:
            score += 15.0  # Resposta rápida

        score_final = min(round(score, 1), 100.0)

        classificacao = "EXCELENTE"
        if score_final < 50.0:
            classificacao = "INSATISFATÓRIO"
        elif score_final < 80.0:
            classificacao = "REGULAR"

        return {
            "score_lai": score_final,
            "classificacao": classificacao,
            "recomendacoes": self._gerar_recomendacoes(portal_features)
        }

    def _gerar_recomendacoes(self, features: Dict[str, Any]) -> List[str]:
        recs = []
        if not features.get("possui_dados_abertos_csv", False):
            recs.append("Disponibilizar download de dados em formato aberto (.CSV ou .JSON).")
        if not features.get("tem_busca_funcional", False):
            recs.append("Adicionar mecanismo de busca e filtros para contratos e licitações.")
        return recs
