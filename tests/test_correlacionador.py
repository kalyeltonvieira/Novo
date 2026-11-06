"""
Testes unitários para core/correlacionador.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.entidades import (
    Documento, EntidadeExtraida, TipoEntidade, TipoDocumento,
    Relacionamento, Pessoa, Empresa
)
from core.correlacionador import Correlacionador


@pytest.fixture
def correlacionador():
    return Correlacionador()


def criar_entidade(tipo, valor, posicao=0, doc_id="doc1", contexto=""):
    """Helper para criar entidade."""
    return EntidadeExtraida(
        id=f"{tipo.value}_{valor}_{posicao}",
        tipo=tipo,
        valor=valor,
        normalizado=valor.upper().strip(),
        contexto=contexto or valor,
        posicao_inicio=posicao,
        posicao_fim=posicao + len(valor),
        documento_id=doc_id,
    )


def criar_documento(entidades, fonte="teste.txt"):
    """Helper para criar documento."""
    return Documento(
        id="doc1",
        fonte=fonte,
        tipo=TipoDocumento.TEXTO,
        conteudo_original=" ".join(e.valor for e in entidades),
        conteudo_processado=" ".join(e.valor for e in entidades),
        entidades=entidades,
    )


class TestCorrelacionarPorCNPJ:
    """Testes de correlação por CNPJ."""

    def test_mesmo_cnpj_gera_relacionamento(self, correlacionador):
        ent1 = criar_entidade(TipoEntidade.CNPJ, "11222333000181", posicao=0)
        ent2 = criar_entidade(TipoEntidade.CNPJ, "11222333000181", posicao=100, doc_id="doc2")
        rels = correlacionador._correlacionar_por_cnpj([ent1, ent2])
        assert len(rels) == 1
        assert rels[0].forca == 0.9

    def test_cnpj_diferente_sem_relacionamento(self, correlacionador):
        ent1 = criar_entidade(TipoEntidade.CNPJ, "11222333000181", posicao=0)
        ent2 = criar_entidade(TipoEntidade.CNPJ, "99999999999999", posicao=100)
        rels = correlacionador._correlacionar_por_cnpj([ent1, ent2])
        assert len(rels) == 0


class TestCorrelacionarPorDocumento:
    """Testes de correlação por co-ocorrência."""

    def test_pessoa_empresa_proximos(self, correlacionador):
        pessoa = criar_entidade(TipoEntidade.PESSOA, "João Silva", posicao=0, contexto="João Silva")
        empresa = criar_entidade(TipoEntidade.EMPRESA, "Empresa XYZ", posicao=50, contexto="Empresa XYZ")
        doc = criar_documento([pessoa, empresa])
        rels = correlacionador._correlacionar_por_documento([doc])
        # Deve gerar relacionamento pessoa-empresa
        assert len(rels) >= 1

    def test_empresa_valor_proximos(self, correlacionador):
        empresa = criar_entidade(TipoEntidade.EMPRESA, "Empresa XYZ", posicao=0, contexto="Empresa XYZ")
        valor = criar_entidade(TipoEntidade.VALOR, "R$ 50000", posicao=50, contexto="R$ 50000")
        valor.normalizado = "50000"
        doc = criar_documento([empresa, valor])
        rels = correlacionador._correlacionar_por_documento([doc])
        # Deve gerar relacionamento empresa-valor
        assert len(rels) >= 1


class TestMontarPessoasEmpresas:
    """Testes de montagem de pessoas e empresas."""

    def test_cria_pessoa_com_cargo(self, correlacionador):
        pessoa = criar_entidade(
            TipoEntidade.PESSOA, "João Silva", posicao=0,
            contexto="O secretário João Silva assinou"
        )
        correlacionador._montar_pessoas_e_empresas([pessoa])
        assert len(correlacionador.pessoas) == 1
        pessoa_obj = list(correlacionador.pessoas.values())[0]
        assert "secretário" in pessoa_obj.cargos

    def test_cria_empresa_com_cnpj(self, correlacionador):
        empresa = criar_entidade(TipoEntidade.EMPRESA, "Empresa XYZ", posicao=0, contexto="Empresa XYZ")
        cnpj = criar_entidade(TipoEntidade.CNPJ, "11222333000181", posicao=50, contexto="CNPJ 11222333000181")
        correlacionador._montar_pessoas_e_empresas([empresa, cnpj])
        assert len(correlacionador.empresas) == 1
        empresa_obj = list(correlacionador.empresas.values())[0]
        assert empresa_obj.cnpj == "11222333000181"


class TestSimilaridade:
    """Testes de cálculo de similaridade."""

    def test_textos_iguais(self, correlacionador):
        assert correlacionador._calcular_similaridade("JOAO SILVA", "JOAO SILVA") == 1.0

    def test_textos_diferentes(self, correlacionador):
        assert correlacionador._calcular_similaridade("JOAO SILVA", "MARIA SANTOS") == 0.0

    def test_textos_vazios(self, correlacionador):
        assert correlacionador._calcular_similaridade("", "teste") == 0.0

    def test_similaridade_parcial(self, correlacionador):
        sim = correlacionador._calcular_similaridade("JOAO SILVA SANTOS", "JOAO SILVA")
        # 2 palavras em comum de 3 total -> 2/3
        assert 0 < sim < 1


class TestDeterminarTipoRelacao:
    """Testes de determinação de tipo de relação."""

    def test_detecta_contrato(self, correlacionador):
        assert correlacionador._determinar_tipo_relacao("contrato assinado") == "contrato"

    def test_detecta_socio(self, correlacionador):
        assert correlacionador._determinar_tipo_relacao("é sócio da empresa") == "socio"

    def test_detecta_parente(self, correlacionador):
        assert correlacionador._determinar_tipo_relacao("filho de") == "parente"

    def test_sem_palavra_chave(self, correlacionador):
        assert correlacionador._determinar_tipo_relacao("texto neutro") == "co_ocorrencia"


class TestGetGrafoRelacionamentos:
    """Testes do grafo de relacionamentos."""

    def test_retorna_dict_com_nodes_e_edges(self, correlacionador):
        rel = Relacionamento(
            id="rel1", tipo="socio",
            entidade_origem="p1", entidade_destino="e1",
            tipo_origem="pessoa", tipo_destino="empresa",
            forca=0.85,
        )
        correlacionador.relacionamentos = [rel]
        grafo = correlacionador.get_grafo_relacionamentos()
        assert isinstance(grafo, dict)
        assert "nodes" in grafo
        assert "edges" in grafo
        assert len(grafo["nodes"]) == 2
        assert len(grafo["edges"]) == 1


class TestResumoCorrelacoes:
    """Testes do resumo de correlações."""

    def test_resumo_vazio(self, correlacionador):
        resumo = correlacionador.resumo_correlacoes()
        assert resumo["total_relacionamentos"] == 0
        assert resumo["total_pessoas"] == 0
        assert resumo["total_empresas"] == 0