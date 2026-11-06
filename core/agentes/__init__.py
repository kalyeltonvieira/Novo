"""
Módulo de Agentes Especialistas
===============================
Sistema multi-agente para análise de documentos públicos.
"""

from .base import BaseAgente
from .supervisor import SupervisorRouter
from .especialistas import (
    NavegadorAgente,
    AgenteGrafo,
    AgenteDiarioOficial,
    AgentePayroll,
    AgenteGeospatial,
    AgenteExtrator,
    AgenteRelator,
    AgenteSancoes,
    AgenteBancario,
    AgenteSuperfaturamento,
    AgenteLinhaDoTempo,
)
from .avancados import (
    CrawlerAgente,
    PDFDownloaderAgente,
    CNPJValidatorAgente,
    CrossPortalAgente,
)

__all__ = [
    "BaseAgente",
    "SupervisorRouter",
    # Agentes básicos
    "NavegadorAgente",
    "AgenteGrafo",
    "AgenteDiarioOficial",
    "AgentePayroll",
    "AgenteGeospatial",
    "AgenteExtrator",
    "AgenteRelator",
    "AgenteSancoes",
    "AgenteBancario",
    "AgenteSuperfaturamento",
    "AgenteLinhaDoTempo",
    # Agentes avançados
    "CrawlerAgente",
    "PDFDownloaderAgente",
    "CNPJValidatorAgente",
    "CrossPortalAgente",
]