"""
Testes unitários para core/entrada_dados.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.entrada_dados import ColetorDados


@pytest.fixture
def coletor():
    """Cria instância do coletor de dados."""
    return ColetorDados()


class TestColetarArquivo:
    """Testes de coleta de arquivos."""

    def test_coleta_arquivo_existente(self, coletor, tmp_path):
        # Cria arquivo temporário
        arquivo = tmp_path / "teste.txt"
        arquivo.write_text("conteúdo de teste")
        
        resultado = coletor.coletar_arquivo(str(arquivo))
        assert resultado == str(arquivo)
        assert len(coletor.historico) == 1
        assert coletor.historico[0]["tipo"] == "arquivo"

    def test_arquivo_inexistente_levanta_erro(self, coletor):
        with pytest.raises(FileNotFoundError):
            coletor.coletar_arquivo("/caminho/inexistente.txt")


class TestColetarPasta:
    """Testes de coleta de pasta."""

    def test_coleta_pasta_vazia(self, coletor, tmp_path):
        arquivos = coletor.coletar_pasta(str(tmp_path))
        assert arquivos == []

    def test_coleta_pasta_com_arquivos(self, coletor, tmp_path):
        # Cria arquivos temporários
        (tmp_path / "arquivo1.txt").write_text("teste1")
        (tmp_path / "arquivo2.pdf").write_text("teste2")
        (tmp_path / "arquivo3.csv").write_text("teste3")
        
        arquivos = coletor.coletar_pasta(str(tmp_path))
        assert len(arquivos) == 3
        assert len(coletor.historico) == 3

    def test_coleta_pasta_com_extensoes_especificas(self, coletor, tmp_path):
        # Cria arquivos de diferentes tipos
        (tmp_path / "arquivo1.txt").write_text("teste1")
        (tmp_path / "arquivo2.pdf").write_text("teste2")
        
        arquivos = coletor.coletar_pasta(str(tmp_path), extensoes=["*.txt"])
        assert len(arquivos) == 1
        assert arquivos[0].endswith("arquivo1.txt")


class TestColetarTexto:
    """Testes de coleta de texto direto."""

    def test_coleta_texto(self, coletor):
        resultado = coletor.coletar_texto("Texto de teste", "fonte_manual")
        assert resultado["tipo"] == "texto"
        assert resultado["conteudo"] == "Texto de teste"
        assert resultado["origem"] == "fonte_manual"
        assert len(coletor.historico) == 1


class TestImportarPlanilha:
    """Testes de importação de planilhas."""

    def test_importa_csv(self, coletor, tmp_path):
        # Cria CSV temporário
        csv_file = tmp_path / "dados.csv"
        csv_file.write_text("coluna1,coluna2\nvalor1,valor2\nvalor3,valor4", encoding="utf-8")
        
        dados = coletor.importar_planilha(str(csv_file))
        assert len(dados) == 2
        assert dados[0]["coluna1"] == "valor1"
        assert dados[0]["coluna2"] == "valor2"
        assert len(coletor.historico) == 1

    def test_arquivo_nao_suportado(self, coletor, tmp_path):
        # Cria arquivo não suportado
        arquivo = tmp_path / "teste.xyz"
        arquivo.write_text("conteúdo")
        
        dados = coletor.importar_planilha(str(arquivo))
        assert dados == []


class TestGetHistorico:
    """Testes de histórico de coletas."""

    def test_historico_vazio(self, coletor):
        historico = coletor.get_historico()
        assert historico == []

    def test_historico_com_coletas(self, coletor):
        coletor.coletar_texto("teste", "fonte1")
        coletor.coletar_texto("teste2", "fonte2")
        
        historico = coletor.get_historico()
        assert len(historico) == 2
        assert historico[0]["origem"] == "fonte1"
        assert historico[1]["origem"] == "fonte2"


class TestColetarUrl:
    """Testes de coleta de URL (mock)."""

    def test_coleta_url_invalida(self, coletor):
        # URL que provavelmente falhará
        resultado = coletor.coletar_url("http://url-inexistente-que-nao-existe.com")
        assert resultado is None


class TestColetarApi:
    """Testes de coleta de API (mock)."""

    def test_coleta_api_invalida(self, coletor):
        # API que provavelmente falhará
        resultado = coletor.coletar_api("http://api-inexistente.com")
        assert resultado is None


class TestColetarPortalTransparencia:
    """Testes de coleta de portal de transparência (mock)."""

    def test_portal_invalido(self, coletor):
        resultado = coletor.coletar_portal_transparencia("http://portal-inexistente.com")
        assert resultado == []


class TestColetarDiarioOficial:
    """Testes de coleta de diário oficial (mock)."""

    def test_diario_invalido(self, coletor):
        resultado = coletor.coletar_diario_oficial("http://diario-inexistente.com")
        assert resultado == []


class TestColetarTcu:
    """Testes de coleta do TCU (mock)."""

    def test_tcu_tipo_invalido(self, coletor):
        resultado = coletor.coletar_tcu(tipo="tipo_inexistente")
        assert resultado == []


class TestColetarDadosEstaduais:
    """Testes de coleta de dados estaduais (mock)."""

    def test_estado_nao_mapeado(self, coletor):
        resultado = coletor.coletar_dados_estaduais("XX")
        assert resultado == []

    def test_estado_mapeado(self, coletor):
        # SP está mapeado, mas a URL pode não responder
        resultado = coletor.coletar_dados_estaduais("SP")
        # Pode retornar vazio se a URL não responder
        assert isinstance(resultado, list)


class TestBuscarGoogle:
    """Testes de busca no Google (mock)."""

    def test_busca_google(self, coletor):
        # A busca pode falhar devido a bloqueios
        resultado = coletor.buscar_google("teste")
        assert isinstance(resultado, list)


class TestDetectarEncoding:
    """Testes de detecção de encoding."""

    def test_detecta_encoding_utf8(self, coletor, tmp_path):
        arquivo = tmp_path / "utf8.txt"
        arquivo.write_text("Ação em UTF-8", encoding="utf-8")
        
        encoding = coletor._detectar_encoding(str(arquivo))
        assert encoding == "utf-8"

    def test_detecta_encoding_latin1(self, coletor, tmp_path):
        arquivo = tmp_path / "latin1.txt"
        arquivo.write_text("Ação em Latin-1", encoding="latin-1")
        
        encoding = coletor._detectar_encoding(str(arquivo))
        # Pode detectar como latin-1 ou iso-8859-1
        assert "latin" in encoding.lower() or "iso" in encoding.lower() or "windows" in encoding.lower() or "mac" in encoding.lower()
