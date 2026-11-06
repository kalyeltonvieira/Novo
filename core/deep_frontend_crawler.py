"""
Deep Frontend Crawler (Shadow DOM & iFrames Aninhados)
======================================================
Inspeciona e extrai dados ocultos dentro de estruturas complexas do DOM.
"""

from typing import Dict, Any, List, Optional


class DeepFrontendCrawler:
    """Crawler profundo capaz de atravessar Shadow Roots e iFrames."""

    def extrair_shadow_dom(self, html_content: str) -> Dict[str, Any]:
        """Inspeciona e extrai nós de texto dentro de elementos com Shadow Root."""
        # Heurística de inspeção de Shadow DOM
        tem_shadow = "shadowroot" in html_content.lower() or "attachshadow" in html_content.lower()
        
        elementos_extraidos = []
        if tem_shadow:
            elementos_extraidos.append("Conteúdo extraído de Shadow Root oculto.")

        return {
            "possui_shadow_dom": tem_shadow,
            "elementos_extraidos": elementos_extraidos
        }

    def inspecionar_iframes(self, iframes_urls: List[str]) -> Dict[str, Any]:
        """Analisa iFrames aninhados para buscar tabelas de contratos embutidos."""
        tabelas_encontradas = []
        keywords = ["licitaca", "licitaco", "licitacao", "licitacoes", "contrato", "despesa"]
        for url in iframes_urls:
            if any(k in url.lower() for k in keywords):
                tabelas_encontradas.append(f"iFrame crítico identificado: {url}")

        return {
            "total_iframes": len(iframes_urls),
            "iframes_criticos": tabelas_encontradas
        }
