"""
Testes para core/agentes/base.py
=================================
Testa a classe base para agentes especialistas.
"""

import pytest
from core.agentes.base import BaseAgente


class AgenteTeste(BaseAgente):
    """Agente de teste para fins de unit testing."""
    
    def processar(self, tarefa: str) -> str:
        """Implementação de teste do método processar."""
        return f"Processado: {tarefa}"


def test_base_agente_init():
    """Testa inicialização da classe BaseAgente."""
    agente = BaseAgente(nome="Teste", descricao="Agente de teste")
    assert agente.nome == "Teste"
    assert agente.descricao == "Agente de teste"


def test_base_agente_processar_not_implemented():
    """Testa que processar levanta NotImplementedError na classe base."""
    agente = BaseAgente(nome="Teste", descricao="Agente de teste")
    with pytest.raises(NotImplementedError, match="Os especialistas devem implementar este método"):
        agente.processar("tarefa teste")


def test_agente_teste_processar():
    """Testa implementação concreta do método processar."""
    agente = AgenteTeste(nome="Teste", descricao="Agente de teste")
    resultado = agente.processar("minha tarefa")
    assert resultado == "Processado: minha tarefa"


def test_agente_teste_heranca():
    """Testa que AgenteTeste herda corretamente de BaseAgente."""
    agente = AgenteTeste(nome="Teste", descricao="Agente de teste")
    assert isinstance(agente, BaseAgente)
    assert hasattr(agente, 'nome')
    assert hasattr(agente, 'descricao')
    assert hasattr(agente, 'processar')
