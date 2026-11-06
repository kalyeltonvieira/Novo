"""
Testes para core/navegador_automatizado.py
============================================
Testa o navegador automatizado e extrator de portal de transparência.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from core.navegador_automatizado import NavegadorAutomatizado, ExtratorPortalTransparencia


@pytest.fixture
def navegador():
    """Fixture do NavegadorAutomatizado."""
    with patch('core.navegador_automatizado.webdriver'):
        navegador = NavegadorAutomatizado(headless=True)
        return navegador


@pytest.fixture
def extrator():
    """Fixture do ExtratorPortalTransparencia."""
    with patch('core.navegador_automatizado.webdriver'):
        navegador = NavegadorAutomatizado(headless=True)
        extrator = ExtratorPortalTransparencia(navegador)
        return extrator


def test_navegador_init():
    """Testa inicialização do NavegadorAutomatizado."""
    with patch('core.navegador_automatizado.webdriver') as mock_webdriver:
        navegador = NavegadorAutomatizado(headless=True)
        assert navegador.headless is True


def test_navegador_navegar_para(navegador):
    """Testa navegação para uma URL."""
    navegador.driver = Mock()
    navegador.navegar_para("https://exemplo.com")
    navegador.driver.get.assert_called_once_with("https://exemplo.com")


def test_navegador_extrair_texto(navegador):
    """Testa extração de texto da página."""
    navegador.driver = Mock()
    navegador.driver.page_source = "<html><body>Conteúdo de teste</body></html>"
    
    texto = navegador.extrair_texto()
    assert "Conteúdo de teste" in texto


def test_navegador_capturar_screenshot(navegador):
    """Testa captura de screenshot."""
    from unittest.mock import mock_open
    mock_driver = Mock()
    mock_driver.get_screenshot_as_png.return_value = b"fake"
    navegador.driver = mock_driver
    with patch('builtins.open', mock_open()):
        navegador.capturar_screenshot("teste.png")
    mock_driver.get_screenshot_as_png.assert_called_once()


def test_navegador_fechar(navegador):
    """Testa fechamento do navegador."""
    mock_driver = Mock()
    navegador.driver = mock_driver
    navegador.fechar()
    mock_driver.quit.assert_called_once()


def test_extrator_init(extrator):
    """Testa inicialização do ExtratorPortalTransparencia."""
    assert extrator.navegador is not None


def test_extrator_extrair_dados_portal(extrator):
    """Testa extração de dados do portal."""
    extrator.navegador = Mock()
    extrator.navegador.extrair_texto.return_value = "Dados do portal"
    
    dados = extrator.extrair_dados_portal("https://exemplo.com")
    
    assert isinstance(dados, dict)
    assert 'licitacoes' in dados


def test_extrator_extrair_menu_links(extrator):
    """Testa extração de links do menu."""
    extrator.navegador = Mock()
    extrator.navegador.obter_html.return_value = '''
        <html>
        <nav>
            <a href="/licitacoes">Licitações</a>
            <a href="/contratos">Contratos</a>
        </nav>
        </html>
    '''
    
    links = extrator.extrair_menu_links("https://exemplo.com")
    
    assert isinstance(links, list)
    assert len(links) > 0


def test_extrator_navegar_menu_completo(extrator):
    """Testa navegação completa do menu."""
    extrator.navegador = Mock()
    extrator.navegador.extrair_texto.return_value = '<a href="/link">Link</a>'
    
    resultado = extrator.navegar_menu_completo("https://exemplo.com", max_links=2)
    
    assert isinstance(resultado, dict)


def test_extrator_extrair_licitacoes(extrator):
    """Testa extração de licitações."""
    extrator.navegador = Mock()
    extrator.navegador.extrair_texto.return_value = '''
        <div class="licitacao">
            <span class="numero">001/2024</span>
            <span class="valor">R$ 10.000,00</span>
        </div>
    '''
    
    licitacoes = extrator.extrair_licitacoes("https://exemplo.com")
    
    assert isinstance(licitacoes, list)


def test_extrator_extrair_contratos(extrator):
    """Testa extração de contratos."""
    extrator.navegador = Mock()
    extrator.navegador.extrair_texto.return_value = '''
        <div class="contrato">
            <span class="numero">CONTR-001</span>
            <span class="empresa">Empresa XYZ</span>
        </div>
    '''
    
    contratos = extrator.extrair_contratos("https://exemplo.com")
    
    assert isinstance(contratos, list)


def test_navegador_esperar_elemento(navegador):
    """Testa espera por elemento."""
    navegador.driver = Mock()
    from selenium.webdriver.common.by import By
    
    navegador.esperar_elemento(By.ID, "teste", timeout=5)
    
    assert navegador.driver.find_element.called


def test_navegador_executar_script(navegador):
    """Testa execução de JavaScript."""
    navegador.driver = Mock()
    navegador.executar_script("window.scrollTo(0, 1000)")
    navegador.driver.execute_script.assert_called_once()


def test_extrator_processar_pagina_licitacao(extrator):
    """Testa processamento de página de licitação específica."""
    extrator.navegador = Mock()
    extrator.navegador.extrair_texto.return_value = "Detalhes da licitação"
    
    resultado = extrator.processar_pagina_licitacao("https://exemplo.com/licitacao/1")
    
    assert isinstance(resultado, dict)


def test_extrator_extrair_empresas(extrator):
    """Testa extração de empresas."""
    extrator.navegador = Mock()
    extrator.navegador.extrair_texto.return_value = '''
        <div class="empresa">
            <span class="cnpj">12.345.678/0001-90</span>
            <span class="nome">Empresa ABC</span>
        </div>
    '''
    
    empresas = extrator.extrair_empresas("https://exemplo.com")
    
    assert isinstance(empresas, list)


def test_navegador_limpar_cookies(navegador):
    """Testa limpeza de cookies."""
    navegador.driver = Mock()
    navegador.limpar_cookies()
    navegador.driver.delete_all_cookies.assert_called_once()


def test_navegador_recarregar_pagina(navegador):
    """Testa recarregamento da página."""
    navegador.driver = Mock()
    navegador.recarregar_pagina()
    navegador.driver.refresh.assert_called_once()
