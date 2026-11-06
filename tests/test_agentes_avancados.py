"""
Testes para Agentes Avançados e Integrações Governamentais
============================================================
Testa os novos agentes: CrawlerProfundo, PDFDownloader, CNPJValidator, CrossPortal
e as integrações com APIs governamentais.
"""

import os
import sys
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Garante que a raiz do projeto está no path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestIntegracoesGovernamentais:
    """Testes para core/integracoes_gov.py"""

    def test_init(self):
        """Testa inicialização."""
        from core.integracoes_gov import IntegracoesGovernamentais
        integracoes = IntegracoesGovernamentais()
        assert integracoes is not None
        assert integracoes.timeout == 30

    @patch('core.integracoes_gov.requests.Session.get')
    def test_consultar_cnpj_valido(self, mock_get):
        """Testa consulta de CNPJ válido com mock."""
        from core.integracoes_gov import IntegracoesGovernamentais

        # Mock da resposta da API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "status": "OK",
            "nome": "EMPRESA TESTE LTDA",
            "fantasia": "Empresa Teste",
            "situacao": "ATIVA",
            "abertura": "01/01/2020",
            "capital_social": "100000",
            "natureza_juridica": "2062",
            "porte": "DEMAIS",
            "logradouro": "RUA TESTE",
            "numero": "123",
            "municipio": "SAO PAULO",
            "uf": "SP",
            "cep": "01000000",
            "qsa": [{"nome": "JOAO SILVA"}],
        }
        mock_get.return_value = mock_response

        integracoes = IntegracoesGovernamentais()
        resultado = integracoes.consultar_cnpj("11.222.333/0001-81")

        assert resultado is not None
        assert resultado["razao_social"] == "EMPRESA TESTE LTDA"
        assert resultado["situacao_cadastral"] == "ATIVA"
        assert len(resultado["socios"]) == 1

    def test_consultar_cnpj_invalido(self):
        """Testa CNPJ inválido."""
        from core.integracoes_gov import IntegracoesGovernamentais
        integracoes = IntegracoesGovernamentais()
        resultado = integracoes.consultar_cnpj("00000000000000")
        assert resultado is None

    @patch('core.integracoes_gov.requests.Session.get')
    def test_consultar_ceis_sem_api_key(self, mock_get):
        """Testa CEIS sem API key (deve usar mock)."""
        from core.integracoes_gov import IntegracoesGovernamentais

        with patch.dict(os.environ, {}, clear=True):
            integracoes = IntegracoesGovernamentais()
            resultado = integracoes.consultar_ceis(cnpj="12345678000199")
            # Sem API key, retorna mock (pode ser vazio ou com sanção)
            assert isinstance(resultado, list)

    @patch('core.integracoes_gov.requests.Session.get')
    def test_consultar_pncp_licitacoes(self, mock_get):
        """Testa consulta PNCP com mock."""
        from core.integracoes_gov import IntegracoesGovernamentais

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "data": [
                {"objetoCompra": "Compra de material", "cnpjFornecedor": "12345678000199"}
            ]
        }
        mock_get.return_value = mock_response

        integracoes = IntegracoesGovernamentais()
        resultado = integracoes.consultar_pncp_licitacoes(
            data_inicial="2024-01-01",
            data_final="2024-12-31"
        )

        assert isinstance(resultado, list)
        assert len(resultado) == 1

    def test_enriquecer_empresa(self):
        """Testa enriquecimento de empresa."""
        from core.integracoes_gov import IntegracoesGovernamentais

        integracoes = IntegracoesGovernamentais()

        with patch.object(integracoes, 'consultar_cnpj', return_value=None):
            with patch.object(integracoes, 'consultar_ceis', return_value=[]):
                with patch.object(integracoes, 'consultar_cnep', return_value=[]):
                    resultado = integracoes.enriquecer_empresa("12345678000199")

                    assert resultado is not None
                    assert resultado["cnpj"] == "12345678000199"
                    assert resultado["inidonea"] is False


class TestPersistenciaDados:
    """Testes para core/persistencia_dados.py"""

    def test_init(self, tmp_path):
        """Testa inicialização."""
        from core.persistencia_dados import PersistenciaDados
        persistencia = PersistenciaDados(base_dir=str(tmp_path / "crawled"))
        assert persistencia.base_dir.exists()

    def test_salvar_e_carregar_crawl(self, tmp_path):
        """Testa salvar e carregar crawl."""
        from core.persistencia_dados import PersistenciaDados

        persistencia = PersistenciaDados(base_dir=str(tmp_path / "crawled"))

        dados = {
            "total_registros": 100,
            "secoes": {"licitacoes": {"total_registros": 50}},
            "pdfs_encontrados": [{"url": "http://exemplo.com/doc.pdf"}],
            "erros": [],
        }

        caminho = persistencia.salvar_crawl(
            url_portal="https://transparencia.exemplo.gov.br",
            dados=dados
        )

        assert os.path.exists(caminho)

        # Lista crawls
        crawls = persistencia.listar_crawls()
        assert len(crawls) == 1
        assert crawls[0]["total_registros"] == 100

    def test_salvar_investigacao_completa(self, tmp_path):
        """Testa salvar investigação completa."""
        from core.persistencia_dados import PersistenciaDados

        persistencia = PersistenciaDados(base_dir=str(tmp_path / "crawled"))

        caminho = persistencia.salvar_investigacao_completa(
            url_portal="https://transparencia.exemplo.gov.br",
            dados_crawl={"total_registros": 50},
            dados_empresas={"empresa1": {"nome": "Teste"}},
            alertas=[{"tipo": "superfaturamento", "severidade": "alta"}],
            laudo="Laudo de auditoria..."
        )

        assert os.path.exists(caminho)

        investigacoes = persistencia.listar_investigacoes()
        assert len(investigacoes) == 1
        assert investigacoes[0]["total_alertas"] == 1
        assert investigacoes[0]["tem_laudo"] is True

    def test_limpar_dados_antigos(self, tmp_path):
        """Testa limpeza de dados antigos."""
        from core.persistencia_dados import PersistenciaDados
        from datetime import timedelta

        persistencia = PersistenciaDados(base_dir=str(tmp_path / "crawled"))

        # Cria arquivo antigo
        arquivo_antigo = persistencia.base_dir / "antigo.json"
        with open(arquivo_antigo, "w") as f:
            f.write("{}")

        # Modifica data para 60 dias atrás
        import time
        data_antiga = time.time() - (60 * 24 * 60 * 60)
        os.utime(arquivo_antigo, (data_antiga, data_antiga))

        # Cria arquivo recente
        arquivo_recente = persistencia.base_dir / "recente.json"
        with open(arquivo_recente, "w") as f:
            f.write("{}")

        # Limpa dados com mais de 30 dias
        removidos = persistencia.limpar_dados_antigos(dias=30)

        assert removidos == 1
        assert not arquivo_antigo.exists()
        assert arquivo_recente.exists()

    def test_estatisticas(self, tmp_path):
        """Testa estatísticas."""
        from core.persistencia_dados import PersistenciaDados

        persistencia = PersistenciaDados(base_dir=str(tmp_path / "crawled"))

        # Cria alguns arquivos
        persistencia.salvar_crawl("https://exemplo.gov.br", {"total_registros": 10})
        persistencia.salvar_investigacao_completa(
            "https://exemplo.gov.br",
            {"total_registros": 10},
            {},
            [],
            "laudo"
        )

        stats = persistencia.get_estatisticas()
        assert stats["total_crawls"] >= 1
        assert stats["total_investigacoes"] == 1


class TestCrawlerAgente:
    """Testes para CrawlerAgente (avancados.py)"""

    def test_init(self):
        """Testa inicialização do CrawlerAgente."""
        from core.agentes.avancados import CrawlerAgente

        navegador_mock = Mock()
        agente = CrawlerAgente(navegador_mock)

        assert agente.nome == "CrawlerProfundo"
        assert agente.max_paginas == 50

    def test_filtrar_links_relevantes(self):
        """Testa filtragem de links relevantes."""
        from core.agentes.avancados import CrawlerAgente

        navegador_mock = Mock()
        agente = CrawlerAgente(navegador_mock)

        links = [
            {"nome": "Licitações", "url": "https://exemplo.gov.br/licitacoes"},
            {"nome": "Contratos", "url": "https://exemplo.gov.br/contratos"},
            {"nome": "Contato", "url": "https://exemplo.gov.br/contato"},
            {"nome": "Despesas", "url": "https://exemplo.gov.br/despesas"},
        ]

        relevantes = agente._filtrar_links_relevantes(links)

        assert len(relevantes) == 3  # Licitações, Contratos, Despesas
        assert "Contato" not in [l["nome"] for l in relevantes]

    def test_encontrar_proxima_pagina(self):
        """Testa detecção de próxima página."""
        from core.agentes.avancados import CrawlerAgente
        from bs4 import BeautifulSoup

        navegador_mock = Mock()
        agente = CrawlerAgente(navegador_mock)

        # HTML com botão "Próxima"
        html = '<html><body><a href="?pagina=2">Próxima</a></body></html>'
        soup = BeautifulSoup(html, "html.parser")

        proxima = agente._encontrar_proxima_pagina(soup, "https://exemplo.gov.br/lista")
        assert proxima is not None
        assert "pagina=2" in proxima

    def test_encontrar_proxima_pagina_inexistente(self):
        """Testa quando não há próxima página."""
        from core.agentes.avancados import CrawlerAgente
        from bs4 import BeautifulSoup

        navegador_mock = Mock()
        agente = CrawlerAgente(navegador_mock)

        html = '<html><body><p>Sem paginação</p></body></html>'
        soup = BeautifulSoup(html, "html.parser")

        proxima = agente._encontrar_proxima_pagina(soup, "https://exemplo.gov.br/lista")
        assert proxima is None


class TestCNPJValidatorAgente:
    """Testes para CNPJValidatorAgente"""

    def test_init(self):
        """Testa inicialização."""
        from core.agentes.avancados import CNPJValidatorAgente
        from core.correlacionador import Correlacionador

        correlacionador = Correlacionador()
        agente = CNPJValidatorAgente(correlacionador)

        assert agente.nome == "CNPJValidator"
        assert agente.integracoes is not None

    def test_processar_sem_empresas(self):
        """Testa processamento sem empresas no correlacionador."""
        from core.agentes.avancados import CNPJValidatorAgente
        from core.correlacionador import Correlacionador

        correlacionador = Correlacionador()
        agente = CNPJValidatorAgente(correlacionador)

        resultado = agente.processar("Verifique as empresas")
        assert "Nenhuma empresa" in resultado

    def test_processar_com_cnpj_direto(self):
        """Testa processamento com CNPJ fornecido diretamente."""
        from core.agentes.avancados import CNPJValidatorAgente
        from core.correlacionador import Correlacionador

        correlacionador = Correlacionador()
        agente = CNPJValidatorAgente(correlacionador)

        # Mock da integração
        with patch.object(agente.integracoes, 'enriquecer_empresa') as mock_enriquecer:
            mock_enriquecer.return_value = {
                "dados_cadastrais": {
                    "razao_social": "EMPRESA TESTE",
                    "situacao_cadastral": "ATIVA",
                    "data_abertura": "01/01/2020",
                    "capital_social": "100000",
                    "socios": [{"nome": "João"}],
                    "endereco": {"logradouro": "Rua A", "numero": "1", "municipio": "SP", "uf": "SP"},
                },
                "inidonea": False,
                "sancoes_ceis": [],
                "sancoes_cnep": [],
            }

            resultado = agente.processar("Verifique CNPJ 11.222.333/0001-81")
            assert "EMPRESA TESTE" in resultado
            assert "ATIVA" in resultado


class TestCrossPortalAgente:
    """Testes para CrossPortalAgente"""

    def test_init(self):
        """Testa inicialização."""
        from core.agentes.avancados import CrossPortalAgente
        from core.correlacionador import Correlacionador

        correlacionador = Correlacionador()
        agente = CrossPortalAgente(correlacionador)

        assert agente.nome == "CrossPortal"

    def test_processar_sem_empresas(self):
        """Testa processamento sem empresas."""
        from core.agentes.avancados import CrossPortalAgente
        from core.correlacionador import Correlacionador

        correlacionador = Correlacionador()
        agente = CrossPortalAgente(correlacionador)

        resultado = agente.processar("Cruze os dados")
        assert "Nenhuma empresa" in resultado


class TestPDFDownloaderAgente:
    """Testes para PDFDownloaderAgente"""

    def test_init(self):
        """Testa inicialização."""
        from core.agentes.avancados import PDFDownloaderAgente

        navegador_mock = Mock()
        agente = PDFDownloaderAgente(navegador_mock)

        assert agente.nome == "PDFDownloader"
        assert os.path.exists(agente.download_dir)

    def test_processar_sem_pdfs(self):
        """Testa processamento sem URLs de PDF."""
        from core.agentes.avancados import PDFDownloaderAgente

        navegador_mock = Mock()
        agente = PDFDownloaderAgente(navegador_mock)

        resultado = agente.processar("Analise os documentos")
        assert "Nenhuma URL de PDF" in resultado


if __name__ == "__main__":
    pytest.main(["-v", __file__])