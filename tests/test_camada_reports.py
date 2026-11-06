"""
Testes unitários para core/camada_reports.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime
from core.entidades import (
    Documento, EntidadeExtraida, TipoEntidade, TipoDocumento,
    Relacionamento, Alerta, Pessoa, Empresa, TipoAnomalia
)
from core.camada_reports import CamadaReports


@pytest.fixture
def reports():
    """Cria instância da camada de reports."""
    return CamadaReports(config={"output_dir": "data/test_reports"})


def criar_documento_com_entidades(entidades, fonte="teste.txt"):
    """Helper para criar documento."""
    return Documento(
        id="doc1",
        fonte=fonte,
        tipo=TipoDocumento.TEXTO,
        conteudo_original="teste",
        conteudo_processado="teste",
        entidades=entidades,
    )


class TestGerarResumo:
    """Testes de geração de resumo."""

    def test_resumo_documento_vazio(self, reports):
        doc = criar_documento_com_entidades([])
        resumo = reports._gerar_resumo([doc], [])
        assert resumo["total_documentos"] == 1
        assert resumo["total_entidades"] == 0
        assert resumo["total_alertas"] == 0

    def test_resumo_com_valores(self, reports):
        entidades = [
            EntidadeExtraida(
                id="val1", tipo=TipoEntidade.VALOR,
                valor="R$ 1000", normalizado="1000",
                documento_id="doc1"
            ),
            EntidadeExtraida(
                id="val2", tipo=TipoEntidade.VALOR,
                valor="R$ 2000", normalizado="2000",
                documento_id="doc1"
            ),
        ]
        doc = criar_documento_com_entidades(entidades)
        resumo = reports._gerar_resumo([doc], [])
        assert resumo["total_entidades"] == 2
        assert resumo["valor_total_envolvido"] == 3000


class TestResumoAlertas:
    """Testes de resumo de alertas."""

    def test_resumo_alertas_vazio(self, reports):
        resumo = reports._resumo_alertas([])
        assert resumo["total"] == 0
        assert len(resumo["por_tipo"]) == 0

    def test_resumo_alertas_com_dados(self, reports):
        alertas = [
            Alerta(
                id="a1", tipo=TipoAnomalia.SUPERFATURAMENTO,
                titulo="Superfaturamento", descricao="Teste",
                severidade="alta", score_confianca=0.9
            ),
            Alerta(
                id="a2", tipo=TipoAnomalia.NEPOTISMO,
                titulo="Nepotismo", descricao="Teste",
                severidade="critica", score_confianca=0.8
            ),
        ]
        resumo = reports._resumo_alertas(alertas)
        assert resumo["total"] == 2
        assert "superfaturamento" in resumo["por_tipo"]
        assert "nepotismo" in resumo["por_tipo"]
        assert resumo["por_severidade"]["alta"] == 1
        assert resumo["por_severidade"]["critica"] == 1


class TestGerarRankings:
    """Testes de geração de rankings."""

    def test_ranking_empresas(self, reports):
        empresas = {
            "e1": Empresa(
                id="e1", nome="Empresa A", nome_normalizado="EMPRESA A",
                contratos=["c1", "c2"]
            ),
            "e2": Empresa(
                id="e2", nome="Empresa B", nome_normalizado="EMPRESA B",
                contratos=["c1"]
            ),
        }
        rankings = reports._gerar_rankings([], {}, empresas)
        assert len(rankings["fornecedores"]) == 2
        assert rankings["fornecedores"][0]["nome"] == "Empresa A"
        assert rankings["fornecedores"][0]["contratos"] == 2

    def test_ranking_maiores_contratos(self, reports):
        entidades = [
            EntidadeExtraida(
                id="val1", tipo=TipoEntidade.VALOR,
                valor="R$ 50000", normalizado="50000",
                documento_id="doc1"
            ),
            EntidadeExtraida(
                id="val2", tipo=TipoEntidade.VALOR,
                valor="R$ 100000", normalizado="100000",
                documento_id="doc1"
            ),
        ]
        doc = criar_documento_com_entidades(entidades)
        rankings = reports._gerar_rankings([doc], {}, {})
        assert len(rankings["maiores_contratos"]) == 2
        assert rankings["maiores_contratos"][0]["valor"] == 100000


class TestGerarDadosGraficos:
    """Testes de geração de dados para gráficos."""

    def test_graficos_alertas_por_tipo(self, reports):
        alertas = [
            Alerta(
                id="a1", tipo=TipoAnomalia.SUPERFATURAMENTO,
                titulo="Superfaturamento", descricao="Teste",
                severidade="alta", score_confianca=0.9
            ),
            Alerta(
                id="a2", tipo=TipoAnomalia.SUPERFATURAMENTO,
                titulo="Superfaturamento 2", descricao="Teste",
                severidade="media", score_confianca=0.7
            ),
        ]
        graficos = reports._gerar_dados_graficos([], alertas)
        assert graficos["alertas_por_tipo"]["superfaturamento"] == 2

    def test_graficos_distribuicao_valores(self, reports):
        entidades = [
            EntidadeExtraida(
                id="val1", tipo=TipoEntidade.VALOR,
                valor="R$ 1000", normalizado="1000",
                documento_id="doc1"
            ),
            EntidadeExtraida(
                id="val2", tipo=TipoEntidade.VALOR,
                valor="R$ 2000", normalizado="2000",
                documento_id="doc1"
            ),
        ]
        doc = criar_documento_com_entidades(entidades)
        graficos = reports._gerar_dados_graficos([doc], [])
        assert graficos["distribuicao_valores"]["media"] == 1500
        assert graficos["distribuicao_valores"]["total"] == 3000


class TestGerarTabelas:
    """Testes de geração de tabelas."""

    def test_tabela_alertas_recentes(self, reports):
        alertas = [
            Alerta(
                id="a1", tipo=TipoAnomalia.SUPERFATURAMENTO,
                titulo="Superfaturamento", descricao="Teste",
                severidade="alta", score_confianca=0.9
            ),
        ]
        tabelas = reports._gerar_tabelas(alertas, {}, {})
        assert len(tabelas["alertas_recentes"]) == 1
        assert tabelas["alertas_recentes"][0]["titulo"] == "Superfaturamento"

    def test_tabela_empresas_suspeitas(self, reports):
        empresas = {
            "e1": Empresa(
                id="e1", nome="Empresa A", nome_normalizado="EMPRESA A",
                score_suspeita=0.8, alertas=["a1", "a2"]
            ),
        }
        tabelas = reports._gerar_tabelas([], empresas, {})
        assert len(tabelas["empresas_suspeitas"]) == 1
        assert tabelas["empresas_suspeitas"][0]["score"] == "0.80"


class TestGerarLinhaTempo:
    """Testes de geração de linha do tempo."""

    def test_linha_tempo_com_documentos(self, reports):
        doc = criar_documento_com_entidades([])
        linha_tempo = reports._gerar_linha_tempo([doc], [])
        assert len(linha_tempo) == 1
        assert linha_tempo[0]["tipo"] == "documento"

    def test_linha_tempo_com_alertas(self, reports):
        alerta = Alerta(
            id="a1", tipo=TipoAnomalia.SUPERFATURAMENTO,
            titulo="Superfaturamento", descricao="Teste",
            severidade="alta", score_confianca=0.9
        )
        linha_tempo = reports._gerar_linha_tempo([], [alerta])
        assert len(linha_tempo) == 1
        assert linha_tempo[0]["tipo"] == "alerta"


class TestGerarMapaGastos:
    """Testes de geração de mapa de gastos."""

    def test_mapa_gastos_por_uf(self, reports):
        doc = Documento(
            id="doc1", fonte="teste", tipo=TipoDocumento.TEXTO,
            conteudo_original="teste", conteudo_processado="teste",
            metadados={"uf": "SP"},
            entidades=[
                EntidadeExtraida(
                    id="val1", tipo=TipoEntidade.VALOR,
                    valor="R$ 1000", normalizado="1000",
                    documento_id="doc1"
                ),
            ],
        )
        mapa = reports._gerar_mapa_gastos([doc], {})
        assert mapa["gastos_por_uf"]["SP"] == 1000


class TestOrganizarEvidencias:
    """Testes de organização de evidências."""

    def test_organiza_evidencias_por_tipo(self, reports):
        alertas = [
            Alerta(
                id="a1", tipo=TipoAnomalia.SUPERFATURAMENTO,
                titulo="Superfaturamento", descricao="Teste",
                severidade="alta", score_confianca=0.9
            ),
            Alerta(
                id="a2", tipo=TipoAnomalia.NEPOTISMO,
                titulo="Nepotismo", descricao="Teste",
                severidade="critica", score_confianca=0.8
            ),
        ]
        evidencias = reports._organizar_evidencias(alertas)
        assert "superfaturamento" in evidencias
        assert "nepotismo" in evidencias
        assert len(evidencias["superfaturamento"]) == 1


class TestExportarJson:
    """Testes de exportação JSON."""

    def test_exporta_json(self, reports, tmp_path):
        dados = {"teste": "valor"}
        reports.output_dir = tmp_path
        caminho = reports.exportar_json(dados, "teste")
        assert os.path.exists(caminho)
        
        import json
        with open(caminho, "r", encoding="utf-8") as f:
            carregado = json.load(f)
        assert carregado["teste"] == "valor"


class TestGerarRelatorioGeral:
    """Testes de geração de relatório geral."""

    def test_gera_relatorio_geral(self, reports):
        dados = {
            "resumo": {"total_documentos": 1},
            "alertas": {"lista_alertas": []},
        }
        relatorio = reports.gerar_relatorio_geral(dados)
        assert relatorio.tipo == "analise"
        assert relatorio.titulo == "Relatório Geral de Análise de Documentos Públicos"
        assert relatorio.id is not None


class TestDescricaoTipoAlerta:
    """Testes de descrição de tipo de alerta."""

    def test_descricao_superfaturamento(self, reports):
        desc = reports._descricao_tipo_alerta("superfaturamento")
        assert "média" in desc.lower()

    def test_descricao_tipo_inexistente(self, reports):
        desc = reports._descricao_tipo_alerta("tipo_inexistente")
        assert desc == "Anomalia detectada automaticamente"


class TestGerarDashboard:
    """Testes de geração completa de dashboard."""

    def test_gera_dashboard_completo(self, reports):
        doc = criar_documento_com_entidades([])
        alerta = Alerta(
            id="a1", tipo=TipoAnomalia.SUPERFATURAMENTO,
            titulo="Superfaturamento", descricao="Teste",
            severidade="alta", score_confianca=0.9
        )
        dashboard = reports.gerar_dashboard(
            documentos=[doc],
            alertas=[alerta],
            relacionamentos=[],
            pessoas={},
            empresas={}
        )
        assert "resumo" in dashboard
        assert "alertas" in dashboard
        assert "rankings" in dashboard
        assert "graficos" in dashboard
        assert dashboard["resumo"]["total_documentos"] == 1
        assert dashboard["alertas"]["total"] == 1
