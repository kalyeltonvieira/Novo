"""
Testes de Workers Assíncronos e Notificações
==============================================
"""

import pytest
from unittest.mock import patch, MagicMock
from workers.tasks import investigar_entidade_task, gerar_relatorio_pdf_task
from core.notificacoes import ServicoNotificacoes


def test_investigar_entidade_task():
    result = investigar_entidade_task("12345678000199", "empresa")
    assert result is not None
    assert result["status"] == "sucesso"
    assert result["entidade_id"] == "12345678000199"


def test_gerar_relatorio_pdf_task():
    result = gerar_relatorio_pdf_task("relatorio_001")
    assert result["status"] == "sucesso"
    assert "relatorio_001.pdf" in result["pdf_path"]


def test_servico_notificacoes_sem_config():
    servico = ServicoNotificacoes()
    # Sem WEBHOOK_URL ou SMTP, deve retornar False graciosamente sem lançar exceção
    assert servico.disparar_alerta_webhook({"titulo": "Teste", "severidade": "alta"}) is False
    assert servico.disparar_email_alerta("Teste Assunto", "Conteudo") is False


@patch("urllib.request.urlopen")
def test_disparo_webhook_com_sucesso(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    servico = ServicoNotificacoes()
    servico.webhook_url = "https://hooks.slack.com/services/test"

    sucesso = servico.disparar_alerta_webhook({
        "titulo": "Nepotismo Grave",
        "descricao": "Detalhes da anomalia",
        "severidade": "critica",
        "valor_envolvido": 250000.0,
        "tipo": "nepotismo"
    })
    assert sucesso is True
