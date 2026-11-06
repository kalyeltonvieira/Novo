import pytest
from unittest.mock import patch, MagicMock
from core.integracoes_gov import IntegracoesGovernamentais
from core.integracoes_gov_completo import IntegracoesGovCompleto

@pytest.fixture
def gov_simples():
    return IntegracoesGovernamentais()

@pytest.fixture
def gov_completo():
    return IntegracoesGovCompleto()

class TestIntegracoesGovernamentais:
    @patch("core.integracoes_gov.IntegracoesGovernamentais._fazer_request")
    def test_consultar_cnpj(self, mock_request, gov_simples):
        mock_request.return_value = {
            "status": "OK",
            "nome": "EMPRESA TESTE S/A",
            "situacao": "ATIVA"
        }
        resultado = gov_simples.consultar_cnpj("12345678901234")
        assert resultado is not None
        assert resultado["razao_social"] == "EMPRESA TESTE S/A"
        assert resultado["situacao_cadastral"] == "ATIVA"

    @patch("core.integracoes_gov.IntegracoesGovernamentais._fazer_request")
    def test_consultar_cnpj_invalido(self, mock_request, gov_simples):
        resultado = gov_simples.consultar_cnpj("123")
        assert resultado is None

    @patch("core.integracoes_gov.IntegracoesGovernamentais._fazer_request")
    def test_consultar_pncp_licitacoes(self, mock_request, gov_simples):
        mock_request.return_value = {
            "data": [{"id": 1, "modalidade": "Pregão"}],
            "totalPaginas": 1
        }
        resultado = gov_simples.consultar_pncp_licitacoes(pagina=1)
        assert len(resultado) == 1
        assert resultado[0]["modalidade"] == "Pregão"

class TestIntegracoesGovCompleto:
    @patch("core.integracoes_gov_completo.IntegracoesGovCompleto._request")
    def test_cgu_despesas(self, mock_request, gov_completo):
        mock_request.return_value = {
            "data": [{"valor": 1000.0, "orgao": "Ministério X"}]
        }
        resultado = gov_completo.cgu_despesas(ano=2023)
        assert len(resultado) == 1
        assert resultado[0]["valor"] == 1000.0
