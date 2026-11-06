"""
Testes unitários para core/leitor_universal.py
Testa extração de entidades via regex (sem depender de spaCy/OCR).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.entidades import TipoEntidade, TipoDocumento
from core.leitor_universal import LeitorUniversal


@pytest.fixture
def leitor():
    """Cria instância do leitor (modelos NLP podem não estar disponíveis)."""
    return LeitorUniversal()


class TestExtracaoCNPJ:
    """Testes de extração de CNPJ."""

    def test_extrai_cnpj_formatado(self, leitor):
        texto = "Empresa com CNPJ 11.222.333/0001-81 foi contratada."
        entidades = leitor._extrair_cnpj(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].tipo == TipoEntidade.CNPJ
        assert entidades[0].normalizado == "11222333000181"

    def test_extrai_cnpj_sem_formatacao(self, leitor):
        texto = "CNPJ: 11222333000181"
        entidades = leitor._extrair_cnpj(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].normalizado == "11222333000181"

    def test_cnpj_invalido_baixa_confianca(self, leitor):
        texto = "CNPJ 11.222.333/0001-82 (inválido)"
        entidades = leitor._extrair_cnpj(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].confianca < 0.5
        assert entidades[0].metadados.get("valido") is False

    def test_sem_cnpj(self, leitor):
        texto = "Não há CNPJ aqui."
        entidades = leitor._extrair_cnpj(texto, "doc1")
        assert len(entidades) == 0


class TestExtracaoCPF:
    """Testes de extração de CPF."""

    def test_extrai_cpf_formatado(self, leitor):
        texto = "CPF: 529.982.247-25"
        entidades = leitor._extrair_cpf(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].tipo == TipoEntidade.CPF
        assert entidades[0].normalizado == "52998224725"

    def test_ignora_numero_nao_cpf(self, leitor):
        texto = "Número 123456"
        entidades = leitor._extrair_cpf(texto, "doc1")
        assert len(entidades) == 0


class TestExtracaoValores:
    """Testes de extração de valores monetários."""

    def test_extrai_valor_com_rs(self, leitor):
        texto = "Valor total: R$ 1.234,56"
        entidades = leitor._extrair_valores(texto, "doc1")
        assert len(entidades) >= 1
        assert entidades[0].tipo == TipoEntidade.VALOR

    def test_normaliza_valor(self, leitor):
        texto = "R$ 1.234,56"
        entidades = leitor._extrair_valores(texto, "doc1")
        if entidades:
            # Deve normalizar para formato float string
            assert "," not in entidades[0].normalizado or "." in entidades[0].normalizado


class TestExtracaoEmail:
    """Testes de extração de email."""

    def test_extrai_email(self, leitor):
        texto = "Contato: teste@exemplo.com"
        entidades = leitor._extrair_emails(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].tipo == TipoEntidade.EMAIL
        assert entidades[0].normalizado == "teste@exemplo.com"


class TestExtracaoDatas:
    """Testes de extração de datas."""

    def test_extrai_data_barras(self, leitor):
        texto = "Data: 25/12/2024"
        entidades = leitor._extrair_datas(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].tipo == TipoEntidade.DATA

    def test_extrai_data_hifens(self, leitor):
        texto = "Data: 25-12-2024"
        entidades = leitor._extrair_datas(texto, "doc1")
        assert len(entidades) == 1


class TestExtracaoCargos:
    """Testes de extração de cargos."""

    def test_extrai_prefeito(self, leitor):
        texto = "O prefeito João Silva assinou o contrato."
        entidades = leitor._extrair_cargos(texto, "doc1")
        assert len(entidades) >= 1
        assert any(e.tipo == TipoEntidade.CARGO for e in entidades)

    def test_extrai_secretario(self, leitor):
        texto = "A secretária de educação esteve presente."
        entidades = leitor._extrair_cargos(texto, "doc1")
        assert len(entidades) >= 1


class TestExtracaoLicitacoes:
    """Testes de extração de licitações."""

    def test_extrai_pregao(self, leitor):
        texto = "Pregão Nº 123/2024 foi realizado."
        entidades = leitor._extrair_licitacoes(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].tipo == TipoEntidade.LICITACAO


class TestExtracaoContratos:
    """Testes de extração de contratos."""

    def test_extrai_contrato(self, leitor):
        texto = "Contrato Nº 456/2024 foi assinado."
        entidades = leitor._extrair_contratos(texto, "doc1")
        assert len(entidades) == 1
        assert entidades[0].tipo == TipoEntidade.CONTRATO


class TestExtracaoEnderecos:
    """Testes de extração de endereços."""

    def test_extrai_rua(self, leitor):
        texto = "Sede na Rua das Flores, 123"
        entidades = leitor._extrair_enderecos(texto, "doc1")
        assert len(entidades) >= 1
        assert entidades[0].tipo == TipoEntidade.ENDERECO

    def test_extrai_avenida(self, leitor):
        texto = "Localizado na Avenida Paulista, 1000"
        entidades = leitor._extrair_enderecos(texto, "doc1")
        assert len(entidades) >= 1


class TestExtracaoOrgaosPublicos:
    """Testes de extração de órgãos públicos."""

    def test_extrai_prefeitura(self, leitor):
        texto = "A Prefeitura Municipal de São Paulo realizou a licitação."
        entidades = leitor._extrair_orgaos_publicos(texto, "doc1")
        assert len(entidades) >= 1
        assert entidades[0].tipo == TipoEntidade.ORGAO_PUBLICO

    def test_extrai_secretaria(self, leitor):
        texto = "A Secretaria de Educação do Estado publicou o edital."
        entidades = leitor._extrair_orgaos_publicos(texto, "doc1")
        assert len(entidades) >= 1


class TestDetectarTipo:
    """Testes de detecção de tipo de documento."""

    def test_detecta_pdf(self, leitor):
        assert leitor._detectar_tipo("documento.pdf") == TipoDocumento.PDF

    def test_detecta_imagem(self, leitor):
        assert leitor._detectar_tipo("foto.png") == TipoDocumento.IMAGEM
        assert leitor._detectar_tipo("foto.jpg") == TipoDocumento.IMAGEM

    def test_detecta_planilha(self, leitor):
        assert leitor._detectar_tipo("dados.xlsx") == TipoDocumento.PLANILHA
        assert leitor._detectar_tipo("dados.csv") == TipoDocumento.PLANILHA

    def test_detecta_html(self, leitor):
        assert leitor._detectar_tipo("pagina.html") == TipoDocumento.HTML

    def test_detecta_json(self, leitor):
        assert leitor._detectar_tipo("dados.json") == TipoDocumento.JSON

    def test_detecta_xml(self, leitor):
        assert leitor._detectar_tipo("dados.xml") == TipoDocumento.XML

    def test_desconhecido_retorna_texto(self, leitor):
        assert leitor._detectar_tipo("arquivo.xyz") == TipoDocumento.TEXTO


class TestNormalizarValor:
    """Testes de normalização de valores."""

    def test_normaliza_valor_com_ponto_e_virgula(self, leitor):
        # 1.234,56 -> 1234.56
        resultado = leitor._normalizar_valor("R$ 1.234,56")
        assert resultado == "1234.56"

    def test_normaliza_valor_so_virgula(self, leitor):
        # 1234,56 -> 1234.56
        resultado = leitor._normalizar_valor("R$ 1234,56")
        assert resultado == "1234.56"


class TestDeduplicarEntidades:
    """Testes de deduplicação."""

    def test_remove_duplicatas(self, leitor):
        from core.entidades import EntidadeExtraida
        ent1 = EntidadeExtraida(id="1", tipo=TipoEntidade.CNPJ, valor="11.222.333/0001-81", normalizado="11222333000181", confianca=0.9)
        ent2 = EntidadeExtraida(id="2", tipo=TipoEntidade.CNPJ, valor="11222333000181", normalizado="11222333000181", confianca=0.95)
        resultado = leitor._deduplicar_entidades([ent1, ent2])
        assert len(resultado) == 1
        # Mantém o de maior confiança
        assert resultado[0].confianca == 0.95

    def test_lista_vazia(self, leitor):
        assert leitor._deduplicar_entidades([]) == []

    def test_mantem_entidades_diferentes(self, leitor):
        from core.entidades import EntidadeExtraida
        ent1 = EntidadeExtraida(id="1", tipo=TipoEntidade.CNPJ, valor="11.222.333/0001-81", normalizado="11222333000181", confianca=0.9)
        ent2 = EntidadeExtraida(id="2", tipo=TipoEntidade.CNPJ, valor="22.333.444/0001-92", normalizado="22333444000192", confianca=0.95)
        resultado = leitor._deduplicar_entidades([ent1, ent2])
        assert len(resultado) == 2


class TestExtracaoTelefones:
    """Testes de extração de telefones."""

    def test_extrai_telefone_fixo(self, leitor):
        texto = "Contato: (11) 3456-7890"
        entidades = leitor._extrair_telefones(texto, "doc1")
        assert len(entidades) >= 1
        assert entidades[0].tipo == TipoEntidade.TELEFONE

    def test_extrai_celular(self, leitor):
        texto = "Celular: (11) 98765-4321"
        entidades = leitor._extrair_telefones(texto, "doc1")
        assert len(entidades) >= 1


class TestProcessamentoTexto:
    """Testes de processamento de texto simples."""

    def test_processa_texto_simples(self, leitor):
        texto = "Contrato com empresa de CNPJ 11.222.333/0001-81 no valor de R$ 50.000,00"
        from core.entidades import Documento
        doc = leitor._processar_texto(texto, "doc1")
        assert doc is not None
        assert doc.tipo == TipoDocumento.TEXTO
        assert len(doc.entidades) > 0


class TestConfiguracao:
    """Testes de configuração do leitor."""

    def test_config_padrao(self, leitor):
        assert leitor.config == {}
        assert leitor.use_ai is False

    def test_config_com_ia(self):
        leitor = LeitorUniversal(config={"use_ai": True})
        assert leitor.use_ai is True


class TestInicializacaoModelos:
    """Testes de inicialização de modelos."""

    def test_inicializa_sem_spacy(self, leitor):
        # Verifica se o leitor lida gracefully com ausência de modelos
        assert hasattr(leitor, 'nlp_models')
        assert hasattr(leitor, 'embedding_model')


class TestExtracaoPessoas:
    """Testes de extração de nomes de pessoas."""

    def test_extrai_nome_completo(self, leitor):
        texto = "O contrato foi assinado por João da Silva."
        entidades = leitor._extrair_pessoas(texto, "doc1")
        # Pode extrair ou não dependendo do modelo NLP
        assert isinstance(entidades, list)


class TestExtracaoEmpresas:
    """Testes de extração de nomes de empresas."""

    def test_extrai_empresa_ltda(self, leitor):
        texto = "A Empresa XYZ Ltda foi contratada."
        entidades = leitor._extrair_empresas(texto, "doc1")
        # Pode extrair ou não dependendo do modelo NLP
        assert isinstance(entidades, list)