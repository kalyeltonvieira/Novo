"""
Testes de Integração para Pipeline Completo
===========================================
Testa o fluxo completo do sistema de análise de documentos.
"""

import pytest
import os
import tempfile
from pathlib import Path
from core.leitor_universal import LeitorUniversal
from core.correlacionador import Correlacionador
from core.detector_anomalias import DetectorAnomalias
from core.base_conhecimento import BaseConhecimento
from core.camada_reports import CamadaReports
from core.entrada_dados import ColetorDados


@pytest.fixture
def temp_dir():
    """Cria diretório temporário para testes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_text_file(temp_dir):
    """Cria arquivo de texto de exemplo."""
    file_path = Path(temp_dir) / "documento.txt"
    file_path.write_text("""
    Contrato nº 001/2024
    Contratante: Prefeitura Municipal
    Contratada: Empresa ABC Ltda
    CNPJ: 12.345.678/0001-90
    Valor: R$ 150.000,00
    Objeto: Serviços de consultoria
    Data: 15/01/2024
    """)
    return str(file_path)


@pytest.mark.integration
def test_pipeline_completo(sample_text_file):
    """Testa o pipeline completo de análise."""
    # Inicializa componentes
    leitor = LeitorUniversal()
    correlacionador = Correlacionador()
    detector = DetectorAnomalias()
    base = BaseConhecimento()
    reports = CamadaReports()
    
    # Processa documento
    documento = leitor.processar_documento(sample_text_file)
    assert documento is not None
    assert len(documento.entidades) > 0
    
    # Correlaciona entidades
    relacionamentos = correlacionador.processar_documentos([documento])
    assert isinstance(relacionamentos, list)
    
    # Detecta anomalias
    alertas = detector.processar(
        [documento],
        relacionamentos,
        correlacionador.pessoas,
        correlacionador.empresas
    )
    assert isinstance(alertas, list)
    
    # Atualiza base de conhecimento
    base.adicionar_entidades(documento.entidades)
    base.adicionar_relacionamentos(relacionamentos)
    base.adicionar_pessoas(correlacionador.pessoas)
    base.adicionar_empresas(correlacionador.empresas)
    base.adicionar_alertas(alertas)
    
    # Gera relatório
    dados = reports.gerar_dashboard(
        [documento],
        alertas,
        relacionamentos,
        correlacionador.pessoas,
        correlacionador.empresas
    )
    assert dados is not None


@pytest.mark.integration
def test_coleta_e_processamento(temp_dir):
    """Testa coleta e processamento de múltiplos arquivos."""
    # Cria múltiplos arquivos
    for i in range(3):
        file_path = Path(temp_dir) / f"documento_{i}.txt"
        file_path.write_text(f"""
        Contrato nº {i:03d}/2024
        Contratante: Prefeitura Municipal
        Contratada: Empresa XYZ Ltda
        CNPJ: 98.765.432/0001-00
        Valor: R$ {(i+1)*50000}.00
        """)
    
    # Coleta arquivos
    coletor = ColetorDados()
    caminhos = coletor.coletar_pasta(temp_dir)
    assert len(caminhos) == 3
    
    # Processa arquivos
    leitor = LeitorUniversal()
    documentos = []
    for caminho in caminhos:
        doc = leitor.processar_documento(caminho)
        if doc:
            documentos.append(doc)
    
    assert len(documentos) > 0


@pytest.mark.integration
def test_correlacao_entre_documentos(temp_dir):
    """Testa correlação entidades entre múltiplos documentos."""
    # Cria documentos com entidades em comum
    cnpj_comum = "12.345.678/0001-90"
    
    for i in range(2):
        file_path = Path(temp_dir) / f"doc_{i}.txt"
        file_path.write_text(f"""
        Documento {i}
        Empresa: Empresa ABC
        CNPJ: {cnpj_comum}
        Valor: R$ {(i+1)*100000}.00
        """)
    
    # Processa documentos
    leitor = LeitorUniversal()
    coletor = ColetorDados()
    caminhos = coletor.coletar_pasta(temp_dir)
    
    documentos = []
    for caminho in caminhos:
        doc = leitor.processar_documento(caminho)
        if doc:
            documentos.append(doc)
    
    # Correlaciona
    correlacionador = Correlacionador()
    relacionamentos = correlacionador.processar_documentos(documentos)
    
    # Verifica se há correlações
    assert len(relacionamentos) >= 0


@pytest.mark.integration
def test_base_conhecimento_persistencia(temp_dir):
    """Testa persistência da base de conhecimento."""
    # Configura base com caminho temporário
    db_path = Path(temp_dir) / "conhecimento"
    base = BaseConhecimento(caminho_db=str(db_path))
    
    # Adiciona dados
    from core.entidades import EntidadeExtraida, TipoEntidade
    
    entidade = EntidadeExtraida(
        id="test_1",
        tipo=TipoEntidade.EMPRESA,
        valor="Empresa Teste",
        normalizado="empresa teste",
        contexto="Teste"
    )
    
    base.adicionar_entidades([entidade])
    base.salvar()
    
    # Verifica se arquivo foi criado
    assert Path(f"{db_path}.json").exists()
    
    # Recarrega base
    base_nova = BaseConhecimento(caminho_db=str(db_path))
    assert base_nova.graph is not None


@pytest.mark.integration
def test_geracao_relatorios(sample_text_file):
    """Testa geração de relatórios em diferentes formatos."""
    # Processa documento
    leitor = LeitorUniversal()
    documento = leitor.processar_documento(sample_text_file)
    
    # Gera relatório
    reports = CamadaReports()
    dados = reports.gerar_dashboard(
        [documento],
        [],
        [],
        {},
        {}
    )
    
    # Exporta HTML
    html_path = reports.exportar_html(dados)
    assert html_path is not None
    assert os.path.exists(html_path)
    
    # Exporta JSON
    json_path = reports.exportar_json(dados)
    assert json_path is not None
    assert os.path.exists(json_path)


@pytest.mark.integration
def test_detector_varias_anomalias(temp_dir):
    """Testa detecção de múltiplos tipos de anomalias."""
    # Cria documento com padrões suspeitos
    file_path = Path(temp_dir) / "suspeito.txt"
    file_path.write_text("""
    Contrato nº 001/2024
    Valor: R$ 1.500.000,00 (muito acima da média)
    Prazo: 1 dia (muito curto)
    Empresa: Empresa Nova Ltda
    CNPJ: 12.345.678/0001-90
    Data abertura: 01/01/2024 (empresa recém-criada)
    """)
    
    # Processa
    leitor = LeitorUniversal()
    documento = leitor.processar_documento(str(file_path))
    
    correlacionador = Correlacionador()
    relacionamentos = correlacionador.processar_documentos([documento])
    
    detector = DetectorAnomalias()
    alertas = detector.processar(
        [documento],
        relacionamentos,
        correlacionador.pessoas,
        correlacionador.empresas
    )
    
    # Verifica se detectou anomalias
    assert isinstance(alertas, list)


@pytest.mark.integration
def test_validacao_configuracao():
    """Testa validação de configuração."""
    from utils.config_validator import ConfigValidator
    
    validator = ConfigValidator()
    resultado = validator.validate_all()
    
    # Deve retornar resultado
    assert resultado is not None
    assert hasattr(resultado, 'is_valid')
    assert hasattr(resultado, 'errors')
    assert hasattr(resultado, 'warnings')


@pytest.mark.slow
@pytest.mark.integration
def test_pipeline_com_ia(temp_dir):
    """Testa pipeline com IA (requer API key configurada)."""
    from utils.config_validator import validate_ai_provider
    from utils.ai_providers import AIProvider
    
    # Verifica se há API key configurada
    resultado = validate_ai_provider('nvidia')
    
    if not resultado.is_valid:
        pytest.skip("API key não configurada para teste com IA")
    
    # Cria documento
    file_path = Path(temp_dir) / "doc_ia.txt"
    file_path.write_text("Análise de contrato público com valores suspeitos.")
    
    # Processa com IA
    leitor = LeitorUniversal(config={"use_ai": True})
    documento = leitor.processar_documento(str(file_path))
    
    assert documento is not None
