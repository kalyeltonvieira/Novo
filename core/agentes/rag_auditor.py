from typing import Dict, Any, List
from .base import BaseAgente
from core.vector_store import VectorStoreManager

class AgenteRAG(BaseAgente):
    """
    Agente responsável por buscar trechos específicos e evidências nos documentos processados
    (PDFs, textos longos) utilizando busca semântica no banco vetorial.
    """
    def __init__(self, vector_store: VectorStoreManager):
        super().__init__(
            nome="BuscaSemantica",
            descricao="Busca informações granulares ou trechos de texto específicos dentro de documentos, editais, relatórios e arquivos PDFs já baixados/processados."
        )
        self.vector_store = vector_store

    def processar(self, tarefa: str) -> str:
        """
        Recebe a pergunta do usuário, busca no VectorStore e retorna o contexto.
        """
        print(f"[RAG] Buscando evidências para: '{tarefa}'")
        try:
            resultados = self.vector_store.buscar(tarefa, limite=3)
            
            if not resultados:
                return "Não encontrei nenhum documento ou trecho na base que responda a esta pergunta."
            
            resposta = "Encontrei as seguintes evidências nos documentos:\n\n"
            for i, r in enumerate(resultados):
                texto = r.get("texto", "")[:1000] # Limite de 1000 chars por trecho
                origem = r.get("metadados", {}).get("origem", "Documento desconhecido")
                distancia = r.get("distancia", 1.0)
                confianca = max(0, 100 - (distancia * 100))
                
                resposta += f"**Evidência {i+1} (Confiança: {confianca:.1f}%)**\n"
                resposta += f"**Origem**: {origem}\n"
                resposta += f"**Trecho**: \"...{texto}...\"\n\n"
                
            return resposta
            
        except Exception as e:
            return f"Erro ao acessar o banco vetorial: {e}"
