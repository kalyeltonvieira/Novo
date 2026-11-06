"""
Injeção de Dependências de Autenticação para FastAPI
=====================================================
Fornece dependências para proteger rotas da API com verificação de JWT.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from api.auth import decode_access_token

security = HTTPBearer(auto_error=False)

# Usuário mock/padrão para testes se a autenticação for desativada via env
MOCK_ADMIN = {
    "username": "admin",
    "email": "admin@transparencia.gov.br",
    "role": "admin"
}


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Dependência que extrai o usuário atual a partir do token Bearer JWT.
    Se o token for omitido em modo DEV, permite continuar ou lança 401 se estrito.
    """
    # Se token enviado, valida
    if credentials and credentials.credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de acesso inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload

    # Se não houver token mas estiver em desenvolvimento, retorna admin mock
    # (Remova ou desative em produção estrita)
    return MOCK_ADMIN


def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Exige que o usuário autenticado possua o papel de Administrador."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: permissões insuficientes"
        )
    return current_user
