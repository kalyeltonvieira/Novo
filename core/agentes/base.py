"""
Base para Agentes do Sistema
=============================
Classe base abstrata para todos os agentes especialistas e avançados.
"""

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.agentes.base")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.agentes.base")
    metrics = None
    MONITORING_AVAILABLE = False


class BaseAgente:
    """
    Interface base para todos os Agentes Especialistas e Avançados do sistema.
    
    Attributes:
        nome (str): Nome identificador do agente.
        descricao (str): Descrição clara das capacidades e objetivo do agente.
    """
    
    def __init__(self, nome: str, descricao: str):
        """
        Inicializa um novo Agente com nome e descrição.
        
        Args:
            nome (str): Nome do agente.
            descricao (str): Descrição do propósito do agente.
        """
        self.nome = nome
        self.descricao = descricao
        if MONITORING_AVAILABLE and metrics:
            metrics.increment("agente_criado", tags={"agente": nome})
        logger.info(f"Agente '{self.nome}' inicializado.")

    def processar(self, tarefa: str) -> str:
        """
        Executa a tarefa solicitada e retorna o resultado formatado em texto.
        
        Args:
            tarefa (str): Descrição da tarefa a ser realizada pelo agente.
            
        Returns:
            str: Resultado do processamento realizado pelo agente.
            
        Raises:
            NotImplementedError: Deve ser implementado pelas sub-classes especializadas.
        """
        raise NotImplementedError("Os especialistas devem implementar este método.")
