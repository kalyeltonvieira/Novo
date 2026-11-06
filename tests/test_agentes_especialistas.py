"""
Testes para core/agentes/especialistas.py
==========================================
Testa os agentes especialistas do sistema multi-agente.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.agentes.base import BaseAgente
from core.agentes.especialistas import (
    NavegadorAgente, AgenteGrafo, AgenteDiarioOficial, AgentePayroll,
    AgenteGeospatial, AgenteExtrator, AgenteRelator, AgenteSancoes,
    AgenteBancario, AgenteSuperfaturamento, AgenteLinhaDoTempo
)

@pytest.fixture
def navegador_mock():
    """Mock do NavegadorAutomatizado."""
    navegador = Mock()
    navegador.correlacionador = Mock()
    navegador.correlacionador.empresas = {}
    navegador.correlacionador.pessoas = {}
    return navegador

@pytest.fixture
def correlacionador_mock():
    """Mock do Correlacionador."""
    correlacionador = Mock()
    correlacionador.empresas = {}
    correlacionador.pessoas = {}
    correlacionador.relacionamentos = []
    return correlacionador

@pytest.fixture
def ai_manager_mock():
    """Mock do AI Manager."""
    manager = Mock()
    manager.get_client = Mock(return_value=Mock())
    return manager


def test_navegador_agente_init(navegador_mock):
    """Testa inicialização do NavegadorAgente."""
    with patch('core.agentes.especialistas.NavegadorAutomatizado'):
        agente = NavegadorAgente(navegador_mock)
        assert agente.nome == "Navegador"
        assert "Navega em uma URL específica" in agente.descricao
        assert agente.navegador == navegador_mock


def test_navegador_agente_processar_url_simples(navegador_mock):
    """Testa processamento de URL simples."""
    navegador_mock.extrator = Mock()
    navegador_mock.extrator.extrair_dados_portal.return_value = {"licitacoes": []}
    
    agente = NavegadorAgente(navegador_mock)
    agente.navegador.navegar.return_value = True
    agente.navegador.obter_html.return_value = "<html><body>Teste</body></html>"
    resultado = agente.processar("https://exemplo.com")
    
    assert isinstance(resultado, str)
    assert "exemplo.com" in resultado.lower() or "teste" in resultado.lower()


def test_agente_grafo_init(correlacionador_mock):
    """Testa inicialização do AgenteGrafo."""
    agente = AgenteGrafo(correlacionador_mock)
    assert agente.nome == "GrafoSocietario"
    assert "Gera um mapa visual" in agente.descricao


def test_agente_diario_oficial_init(ai_manager_mock):
    """Testa inicialização do AgenteDiarioOficial."""
    agente = AgenteDiarioOficial(lista_documentos=[], ai_manager=ai_manager_mock)
    assert agente.nome == "GazetteAuditor"
    assert "Diários Oficiais" in agente.descricao


def test_agente_payroll_init(ai_manager_mock):
    """Testa inicialização do AgentePayroll."""
    agente = AgentePayroll(lista_documentos=[], ai_manager=ai_manager_mock)
    assert agente.nome == "PayrollAuditor"
    assert "planilhas financeiras" in agente.descricao


def test_agente_geospatial_init(correlacionador_mock):
    """Testa inicialização do AgenteGeospatial."""
    agente = AgenteGeospatial(correlacionador_mock)
    assert agente.nome == "GeospatialAuditor"
    assert "mapa" in agente.descricao.lower()


def test_agente_extrator_init(ai_manager_mock):
    """Testa inicialização do AgenteExtrator."""
    agente = AgenteExtrator(lista_documentos=[], ai_manager=ai_manager_mock)
    assert agente.nome == "InvoiceParser"
    assert "Notas Fiscais" in agente.descricao


def test_agente_relator_init(ai_manager_mock):
    """Testa inicialização do AgenteRelator."""
    agente = AgenteRelator(historico_mensagens=[], ai_manager=ai_manager_mock)
    assert agente.nome == "ReporterAuditor"
    assert "Laudo Pericial final" in agente.descricao


def test_agente_sancoes_init(correlacionador_mock):
    """Testa inicialização do AgenteSancoes."""
    agente = AgenteSancoes(correlacionador_mock)
    assert agente.nome == "SanctionAuditor"
    assert "sanções" in agente.descricao


def test_agente_bancario_init(ai_manager_mock):
    """Testa inicialização do AgenteBancario."""
    agente = AgenteBancario(lista_documentos=[], ai_manager=ai_manager_mock)
    assert agente.nome == "BankingAuditor"
    assert "extratos bancários" in agente.descricao


def test_agente_superfaturamento_init():
    """Testa inicialização do AgenteSuperfaturamento."""
    agente = AgenteSuperfaturamento(historico_mensagens=[])
    assert agente.nome == "OverpricingAuditor"
    assert "superfaturamento" in agente.descricao


def test_agente_linha_do_tempo_init(correlacionador_mock, ai_manager_mock):
    """Testa inicialização do AgenteLinhaDoTempo."""
    agente = AgenteLinhaDoTempo(historico_mensagens=[], correlacionador=correlacionador_mock, ai_manager=ai_manager_mock)
    assert agente.nome == "TimelineAuditor"
    assert "linha do tempo" in agente.descricao


def test_especialistas_heranca_base_agente(navegador_mock, correlacionador_mock, ai_manager_mock):
    """Testa que todos os especialistas herdam de BaseAgente."""
    agentes = [
        NavegadorAgente(navegador_mock),
        AgenteGrafo(correlacionador_mock),
        AgenteDiarioOficial([], ai_manager_mock),
        AgentePayroll([], ai_manager_mock),
        AgenteGeospatial(correlacionador_mock),
        AgenteExtrator([], ai_manager_mock),
        AgenteRelator([], ai_manager_mock),
        AgenteSancoes(correlacionador_mock),
        AgenteBancario([], ai_manager_mock),
        AgenteSuperfaturamento([]),
        AgenteLinhaDoTempo([], correlacionador_mock, ai_manager_mock),
    ]
    
    for agente in agentes:
        assert isinstance(agente, BaseAgente)
        assert hasattr(agente, 'processar')
