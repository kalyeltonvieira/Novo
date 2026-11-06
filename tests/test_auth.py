"""
Testes de Autenticação e Segurança (JWT & RBAC)
=================================================
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.auth import create_access_token, decode_access_token, hash_password, verify_password

client = TestClient(app)


def test_hashing_senha():
    senha = "senha_secreta_123"
    h = hash_password(senha)
    assert h != senha
    assert verify_password(senha, h) is True
    assert verify_password("senha_errada", h) is False


def test_geracao_e_decodificacao_jwt():
    data = {"sub": "usuario_teste", "role": "auditor"}
    token = create_access_token(data)
    assert token is not None
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "usuario_teste"
    assert payload["role"] == "auditor"


def test_endpoint_login_sucesso():
    response = client.post("/api/token", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_endpoint_login_falha():
    response = client.post("/api/token", json={"username": "admin", "password": "senha_errada_404"})
    assert response.status_code == 401


def test_rota_protegida_com_bearer_token():
    token_resp = client.post("/api/token", json={"username": "admin", "password": "admin123"})
    token = token_resp.json()["access_token"]
    
    # Faz requisição enviando o Bearer Token
    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["sub"] == "admin"
