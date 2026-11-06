"""
Testes para core/agentes/supervisor.py
=======================================
Testa o sistema de roteamento multi-agente.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.agentes.supervisor import SupervisorRouter
from core.agentes.base import BaseAgente
from utils.ai_providers import AIManager, AIProvider


class AgenteMock(BaseAgente):
    """Agente mock para testes."""
    
    def __init__(self, nome, descricao, resposta_fixa=None):
        super().__init__(nome, descricao)
        self.resposta_fixa = resposta_fixa or f"Resposta do {nome}"
        self.tarefas_recebidas = []
    
    def processar(self, tarefa: str) -> str:
        self.tarefas_recebidas.append(tarefa)
        return self.resposta_fixa


@pytest.fixture
def ai_manager_mock():
    """Mock do AIManager."""
    manager = Mock(spec=AIManager)
    client_mock = Mock()
    client_mock.is_available.return_value = True
    manager.get_client.return_value = client_mock
    return manager


@pytest.fixture
def supervisor(ai_manager_mock):
    """Fixture do SupervisorRouter com agentes mock."""
    agentes = [
        AgenteMock("Navegador", "Navega em URLs"),
        AgenteMock("Analista", "Analisa documentos"),
        AgenteMock("Correlacionador", "Correlaciona entidades")
    ]
    return SupervisorRouter(ai_manager_mock, agentes)


def test_supervisor_init(ai_manager_mock):
    """Testa inicialização do SupervisorRouter."""
    agentes = [AgenteMock("Teste", "Descrição")]
    supervisor = SupervisorRouter(ai_manager_mock, agentes)
    
    assert supervisor.ai_manager == ai_manager_mock
    assert len(supervisor.especialistas) == 1
    assert "Teste" in supervisor.especialistas
    assert supervisor.max_iteracoes == 5


def test_supervisor_gerar_system_prompt(supervisor):
    """Testa geração do system prompt."""
    prompt = supervisor._gerar_system_prompt()
    
    assert "Supervisor" in prompt
    assert "Navegador" in prompt
    assert "Analista" in prompt
    assert "Correlacionador" in prompt
    assert "agente" in prompt.lower()
    assert "json" in prompt.lower()


def test_supervisor_processar_sem_delegacao(supervisor, ai_manager_mock):
    """Testa processamento quando não há delegação."""
    # Mock para retornar resposta direta sem JSON
    ai_manager_mock.get_client().chat_completion.return_value = {
        "content": "Resposta direta do supervisor",
        "reasoning": None
    }
    
    resultado = supervisor.processar("Pergunta simples", "")
    
    assert resultado == "Resposta direta do supervisor"


def test_supervisor_processar_com_delegacao(supervisor, ai_manager_mock):
    """Testa processamento com delegação para agente especialista."""
    # Primeira chamada: delega para Navegador
    primeira_resposta = '''```json
{
  "agente": "Navegador",
  "tarefa": "Acesse https://exemplo.com"
}
```'''
    
    # Segunda chamada: resposta final após delegação
    segunda_resposta = "Análise completa do site"
    
    ai_manager_mock.get_client().chat_completion.side_effect = [
        {"content": primeira_resposta, "reasoning": None},
        {"content": segunda_resposta, "reasoning": None}
    ]
    
    resultado = supervisor.processar("Analise o site exemplo.com", "")
    
    assert resultado == "Análise completa do site"
    assert len(supervisor.especialistas["Navegador"].tarefas_recebidas) == 1
    assert "https://exemplo.com" in supervisor.especialistas["Navegador"].tarefas_recebidas[0]


def test_supervisor_limite_iteracoes(supervisor, ai_manager_mock):
    """Testa limite de iterações forçando resposta final."""
    # Sempre delega para forçar múltiplas iterações
    delegacao = '''```json
{
  "agente": "Navegador",
  "tarefa": "Tarefa"
}
```'''
    
    ai_manager_mock.get_client().chat_completion.side_effect = [
        {"content": delegacao, "reasoning": None},
        {"content": delegacao, "reasoning": None},
        {"content": delegacao, "reasoning": None},
        {"content": "Resposta final forçada", "reasoning": None}
    ]
    
    resultado = supervisor.processar("Pergunta", "")
    
    assert resultado == "Resposta final forçada"
    assert len(supervisor.especialistas["Navegador"].tarefas_recebidas) == 3


def test_supervisor_ia_indisponivel(supervisor, ai_manager_mock):
    """Testa comportamento quando IA está indisponível."""
    ai_manager_mock.get_client().is_available.return_value = False
    
    resultado = supervisor.processar("Pergunta", "")
    
    assert "Erro: Provedor de IA indisponível" in resultado


def test_supervisor_callback_ui(supervisor, ai_manager_mock):
    """Testa callbacks de UI."""
    callback_mock = Mock()
    callback_pensamento_mock = Mock()
    
    ai_manager_mock.get_client().chat_completion.return_value = {
        "content": "<thought>Pensamento</thought>\nResposta",
        "reasoning": None
    }
    
    resultado = supervisor.processar("Pergunta", "", callback_ui=callback_mock, callback_pensamento=callback_pensamento_mock)
    
    callback_pensamento_mock.assert_called_once_with("Pensamento")


def test_supervisor_extracao_pensamento(supervisor, ai_manager_mock):
    """Testa extração de blocos <thought>."""
    ai_manager_mock.get_client().chat_completion.return_value = {
        "content": "<thought>Pensamento 1</thought>\nTexto\n<thought>Pensamento 2</thought>\nResposta final",
        "reasoning": None
    }
    
    callback_mock = Mock()
    resultado = supervisor.processar("Pergunta", "", callback_pensamento=callback_mock)
    
    assert callback_mock.call_count == 2
    assert "Resposta final" in resultado


def test_supervisor_json_invalido(supervisor, ai_manager_mock):
    """Testa tratamento de JSON inválido."""
    ai_manager_mock.get_client().chat_completion.return_value = {
        "content": "```json\n{json inválido}\n```\nResposta normal",
        "reasoning": None
    }
    
    resultado = supervisor.processar("Pergunta", "")
    
    # Deve ignorar JSON inválido e retornar resposta normal
    assert "Resposta normal" in resultado


def test_supervisor_agente_inexistente(supervisor, ai_manager_mock):
    """Testa delegação para agente inexistente."""
    ai_manager_mock.get_client().chat_completion.return_value = {
        "content": '```json\n{"agente": "Inexistente", "tarefa": "Tarefa"}\n```\nResposta',
        "reasoning": None
    }
    
    resultado = supervisor.processar("Pergunta", "")
    
    # Deve ignorar delegação inválida e retornar resposta
    assert "Resposta" in resultado
