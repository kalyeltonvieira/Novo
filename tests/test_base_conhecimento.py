"""
Testes unitários para core/base_conhecimento.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.entidades import (
    Documento, EntidadeExtraida, TipoEntidade, TipoDocumento,
    Relacionamento, Alerta, Pessoa, Empresa, TipoAnomalia
)
from core.base_conhecimento import BaseConhecimento


@pytest.fixture
def base():
    """Cria instância da base de conhecimento."""
    return BaseConhecimento(caminho_db="data/test_conhecimento")


class TestAdicionarEntidades:
    """Testes de adição de entidades ao grafo."""

    def test_adiciona_entidade(self, base):
        ent = EntidadeExtraida(
            id="ent1", tipo=TipoEntidade.CNPJ,
            valor="11.222.333/0001-81", normalizado="11222333000181",
            confianca=0.9
        )
        base.adicionar_entidades([ent])
        assert base.graph.has_node("ent1")
        assert base.graph.nodes["ent1"]["tipo"] == "cnpj"

    def test_adiciona_multiplas_entidades(self, base):
        entidades = [
            EntidadeExtraida(
                id=f"ent{i}", tipo=TipoEntidade.PESSOA,
                valor=f"Pessoa {i}", normalizado=f"PESSOA {i}",
                confianca=0.8
            )
            for i in range(5)
        ]
        base.adicionar_entidades(entidades)
        assert base.graph.number_of_nodes() == 5


class TestAdicionarRelacionamentos:
    """Testes de adição de relacionamentos ao grafo."""

    def test_adiciona_relacionamento(self, base):
        rel = Relacionamento(
            id="rel1", tipo="socio",
            entidade_origem="p1", entidade_destino="e1",
            tipo_origem="pessoa", tipo_destino="empresa",
            forca=0.85
        )
        base.adicionar_relacionamentos([rel])
        assert base.graph.has_edge("p1", "e1")
        assert base.graph.edges["p1", "e1"]["tipo"] == "socio"


class TestAdicionarPessoas:
    """Testes de adição de pessoas ao grafo."""

    def test_adiciona_pessoa(self, base):
        pessoa = Pessoa(
            id="p1", nome="João Silva", nome_normalizado="JOAO SILVA",
            cpf="12345678901", cargos=["secretário"]
        )
        base.adicionar_pessoas({"p1": pessoa})
        assert base.graph.has_node("p1")
        assert base.graph.nodes["p1"]["nome"] == "João Silva"
        assert base.graph.nodes["p1"]["tipo_entidade"] == "pessoa"


class TestAdicionarEmpresas:
    """Testes de adição de empresas ao grafo."""

    def test_adiciona_empresa(self, base):
        empresa = Empresa(
            id="e1", nome="Empresa XYZ", nome_normalizado="EMPRESA XYZ",
            cnpj="11222333000181", capital_social=1000000.0
        )
        base.adicionar_empresas({"e1": empresa})
        assert base.graph.has_node("e1")
        assert base.graph.nodes["e1"]["nome"] == "Empresa XYZ"
        assert base.graph.nodes["e1"]["cnpj"] == "11222333000181"


class TestAdicionarAlertas:
    """Testes de adição de alertas ao grafo."""

    def test_adiciona_alerta(self, base):
        alerta = Alerta(
            id="a1", tipo=TipoAnomalia.SUPERFATURAMENTO,
            titulo="Superfaturamento detectado",
            descricao="Valor muito acima da média",
            severidade="alta", score_confianca=0.9
        )
        base.adicionar_alertas([alerta])
        assert base.graph.has_node("a1")
        assert base.graph.nodes["a1"]["tipo"] == "alerta"
        assert base.graph.nodes["a1"]["severidade"] == "alta"


class TestConsultarVizinhanca:
    """Testes de consulta de vizinhança."""

    def test_vizinhanca_entidade_existente(self, base):
        # Adiciona entidades e relacionamento
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
            EntidadeExtraida(id="e1", tipo=TipoEntidade.EMPRESA, valor="Empresa", normalizado="EMPRESA"),
        ])
        base.adicionar_relacionamentos([
            Relacionamento(
                id="rel1", tipo="socio",
                entidade_origem="p1", entidade_destino="e1",
                tipo_origem="pessoa", tipo_destino="empresa",
                forca=0.85
            )
        ])
        vizinhanca = base.consultar_vizinhanca("p1")
        assert vizinhanca["entidade"] is not None
        assert len(vizinhanca["conexoes"]) >= 1

    def test_vizinhanca_entidade_inexistente(self, base):
        vizinhanca = base.consultar_vizinhanca("inexistente")
        assert vizinhanca["entidade"] is None
        assert len(vizinhanca["conexoes"]) == 0


class TestConsultarCaminho:
    """Testes de consulta de caminho entre entidades."""

    def test_caminho_entre_entidades(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
            EntidadeExtraida(id="e1", tipo=TipoEntidade.EMPRESA, valor="Empresa", normalizado="EMPRESA"),
        ])
        base.adicionar_relacionamentos([
            Relacionamento(
                id="rel1", tipo="socio",
                entidade_origem="p1", entidade_destino="e1",
                tipo_origem="pessoa", tipo_destino="empresa",
                forca=0.85
            )
        ])
        caminho = base.consultar_caminho("p1", "e1")
        assert len(caminho) == 1
        assert caminho[0]["entidade_origem"] == "p1"
        assert caminho[0]["entidade_destino"] == "e1"

    def test_caminho_sem_conexao(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
            EntidadeExtraida(id="e1", tipo=TipoEntidade.EMPRESA, valor="Empresa", normalizado="EMPRESA"),
        ])
        caminho = base.consultar_caminho("p1", "e1")
        assert len(caminho) == 0


class TestConsultarEntidadesPorTipo:
    """Testes de consulta por tipo."""

    def test_consulta_pessoas(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
            EntidadeExtraida(id="p2", tipo=TipoEntidade.PESSOA, valor="Maria", normalizado="MARIA"),
            EntidadeExtraida(id="e1", tipo=TipoEntidade.EMPRESA, valor="Empresa", normalizado="EMPRESA"),
        ])
        pessoas = base.consultar_entidades_por_tipo("pessoa")
        assert len(pessoas) == 2

    def test_consulta_empresas(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="e1", tipo=TipoEntidade.EMPRESA, valor="Empresa", normalizado="EMPRESA"),
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
        ])
        empresas = base.consultar_entidades_por_tipo("empresa")
        assert len(empresas) == 1


class TestConsultarEstatisticas:
    """Testes de estatísticas do grafo."""

    def test_estatisticas_grafo_vazio(self, base):
        stats = base.consultar_estatisticas()
        assert stats["total_entidades"] == 0
        assert stats["total_relacionamentos"] == 0

    def test_estatisticas_grafo_com_dados(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
            EntidadeExtraida(id="e1", tipo=TipoEntidade.EMPRESA, valor="Empresa", normalizado="EMPRESA"),
        ])
        base.adicionar_relacionamentos([
            Relacionamento(
                id="rel1", tipo="socio",
                entidade_origem="p1", entidade_destino="e1",
                tipo_origem="pessoa", tipo_destino="empresa",
                forca=0.85
            )
        ])
        stats = base.consultar_estatisticas()
        assert stats["total_entidades"] == 2
        assert stats["total_relacionamentos"] == 1


class TestExportarParaVis:
    """Testes de exportação para visualização."""

    def test_exporta_grafo_vazio(self, base):
        vis = base.exportar_para_vis()
        assert vis["nodes"] == []
        assert vis["edges"] == []

    def test_exporta_grafo_com_dados(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
            EntidadeExtraida(id="e1", tipo=TipoEntidade.EMPRESA, valor="Empresa", normalizado="EMPRESA"),
        ])
        base.adicionar_relacionamentos([
            Relacionamento(
                id="rel1", tipo="socio",
                entidade_origem="p1", entidade_destino="e1",
                tipo_origem="pessoa", tipo_destino="empresa",
                forca=0.85
            )
        ])
        vis = base.exportar_para_vis()
        assert len(vis["nodes"]) == 2
        assert len(vis["edges"]) == 1


class TestSalvarCarregar:
    """Testes de salvar e carregar grafo."""

    def test_salvar_carregar_grafo(self, base, tmp_path):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João", normalizado="JOAO"),
        ])
        
        caminho = os.path.join(tmp_path, "test_grafo")
        base.caminho_db = caminho
        base.salvar()
        
        # Cria nova base e carrega
        base2 = BaseConhecimento(caminho_db=caminho)
        base2.carregar()
        assert base2.graph.has_node("p1")


class TestBuscarSemantica:
    """Testes de busca semântica."""

    def test_busca_texto_existente(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João Silva", normalizado="JOAO SILVA"),
        ])
        resultados = base.buscar_semantica("João")
        assert len(resultados) >= 1

    def test_busca_texto_inexistente(self, base):
        base.adicionar_entidades([
            EntidadeExtraida(id="p1", tipo=TipoEntidade.PESSOA, valor="João Silva", normalizado="JOAO SILVA"),
        ])
        resultados = base.buscar_semantica("Pedro")
        assert len(resultados) == 0
