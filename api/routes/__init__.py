"""
Módulo de Rotas da API
=======================
Exporta todas as rotas da API.
"""
from . import dashboard
from . import documentos
from . import chat
from . import navegador
from . import relatorios
from . import ws

__all__ = [
    "dashboard",
    "documentos",
    "chat",
    "navegador",
    "relatorios",
    "ws",
]
