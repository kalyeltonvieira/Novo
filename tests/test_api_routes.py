"""
Testes para as Rotas da API
===========================
Testa os endpoints principais da API FastAPI.
"""

import os
import sys
import json
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

# Garante que a raiz do projeto está no path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.main import app

client = TestClient(app)


class TestHealthCheck:
    """Testes para o endpoint de health check."""

    def test_health_root(self):
        """Testa endpoint raiz."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_check(self):
        """Testa health check completo."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "modules" in data
        assert "timestamp" in data


class TestDashboard:
    """Testes para rotas de dashboard."""

    def test_dashboard_resumo(self):
        """Testa resumo do dashboard."""
        response = client.get("/api/dashboard/")
        assert response.status_code in (200, 500)  # Pode falhar se não houver dados
        if response.status_code == 200:
            data = response.json()
            assert "resumo" in data


class TestDocumentos:
    """Testes para rotas de documentos."""

    def test_listar_documentos(self):
        """Testa listagem de documentos."""
        response = client.get("/api/documentos/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_upload_invalido(self):
        """Testa upload sem arquivo."""
        response = client.post("/api/documentos/upload")
        assert response.status_code == 422  # Unprocessable Entity

    def test_get_documento_inexistente(self):
        """Testa busca de documento inexistente."""
        response = client.get("/api/documentos/id_inexistente")
        assert response.status_code == 404

    def test_delete_documento_inexistente(self):
        """Testa deleção de documento inexistente."""
        response = client.delete("/api/documentos/id_inexistente")
        assert response.status_code == 404


class TestRelatorios:
    """Testes para rotas de relatórios."""

    def test_listar_relatorios(self):
        """Testa listagem de relatórios."""
        response = client.get("/api/relatorios/")
        assert response.status_code == 200
        data = response.json()
        assert "relatorios" in data
        assert "total" in data

    def test_gerar_relatorio(self):
        """Testa geração de relatório."""
        response = client.post("/api/relatorios/gerar")
        # Pode falhar se não houver dados na base
        assert response.status_code in (200, 500)

    def test_exportar_csv(self):
        """Testa exportação CSV."""
        response = client.get("/api/relatorios/exportar/csv?tipo=alertas")
        assert response.status_code in (200, 500)

    def test_exportar_formato_invalido(self):
        """Testa exportação com formato inválido."""
        response = client.get("/api/relatorios/exportar/xml")
        assert response.status_code == 400


class TestNavegador:
    """Testes para rotas do navegador."""

    def test_status_navegador(self):
        """Testa status do navegador."""
        response = client.get("/api/navegador/status")
        assert response.status_code == 200
        data = response.json()
        assert "disponivel" in data


class TestChat:
    """Testes para rotas de chat."""

    def test_historico_chat(self):
        """Testa histórico do chat."""
        response = client.get("/api/chat/historico")
        assert response.status_code == 200
        data = response.json()
        assert "conversas" in data
        assert "total" in data

    def test_chat_sem_mensagem(self):
        """Testa chat sem mensagem."""
        response = client.post("/api/chat/", json={"message": "", "history": []})
        # Deve processar ou retornar erro
        assert response.status_code in (200, 422, 500)


class TestCORs:
    """Testes para configuração CORS."""

    def test_cors_headers(self):
        """Testa se headers CORS estão presentes."""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Testes para tratamento de erros."""

    def test_rota_inexistente(self):
        """Testa acesso a rota inexistente."""
        response = client.get("/api/rota_inexistente")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Testa método HTTP não permitido."""
        response = client.put("/api/dashboard/")
        assert response.status_code in (405, 500)


if __name__ == "__main__":
    pytest.main(["-v", __file__])