"""
Gerador de Peças Jurídicas e Notícia de Fato (MPF / TCE)
=========================================================
Compila achados de auditoria em representações legais formais.
"""

from typing import Dict, Any, List


class LegalReportGenerator:
    """Gerador de representação jurídica formal para o Ministério Público."""

    def gerar_noticia_de_fato(self, dados_anomalia: Dict[str, Any]) -> str:
        """Compila uma Notícia de Fato padronizada em formato de peça jurídica."""
        titulo = dados_anomalia.get("titulo", "Irregularidade em Licitação Pública")
        descricao = dados_anomalia.get("descricao", "Sem descrição disponível.")
        valor = dados_anomalia.get("valor_envolvido", 0.0)
        orgao = dados_anomalia.get("orgao", "Prefeitura Municipal")

        peca = (
            f"EXCELENTÍSSIMO SENHOR PROCURADOR DA REPÚBLICA / MINISTÉRIO PÚBLICO\n"
            f"ASSUNTO: NOTÍCIA DE FATO - REPRESENTAÇÃO POR IRREGULARIDADES EM CONTRATAÇÃO PÚBLICA\n\n"
            f"1. DOS FATOS:\n"
            f"Chegou ao conhecimento desta auditoria automatizada indícios de severa irregularidade perante o órgão {orgao}.\n"
            f"Descrição das anomalias: {descricao}\n"
            f"Valor estimado envolvido: R$ {valor:,.2f}\n\n"
            f"2. DO ENQUADRAMENTO JURÍDICO:\n"
            f"Os fatos narrados enquadram-se, em tese, nos tipos previstos na Lei de Licitações (Lei nº 14.133/2021) "
            f"e nos atos de improbidade administrativa previstos na Lei nº 8.429/1992.\n\n"
            f"3. DOS PEDIDOS:\n"
            f"Requer-se a instauração de Procedimento Preparatório ou Inquérito Civil Público para apuração dos fatos.\n\n"
            f"Termos em que pede deferimento.\n"
            f"Emitido automaticamente pelo Cérebro da Transparência."
        )
        return peca
