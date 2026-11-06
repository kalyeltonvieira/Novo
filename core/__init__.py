"""
Módulo Core - Pipeline de Análise de Documentos Públicos
=======================================================
Leitor Universal → Correlacionador → Detector de Anomalias → Base de Conhecimento → Reports
"""

from .entrada_dados import ColetorDados
from .leitor_universal import LeitorUniversal
from .correlacionador import Correlacionador
from .detector_anomalias import DetectorAnomalias
from .base_conhecimento import BaseConhecimento
from .camada_reports import CamadaReports
from .navegador_automatizado import NavegadorAutomatizado
from .integracoes_gov import IntegracoesGovernamentais

__all__ = [
    "ColetorDados",
    "LeitorUniversal",
    "Correlacionador",
    "DetectorAnomalias",
    "BaseConhecimento",
    "CamadaReports",
    "NavegadorAutomatizado",
    "IntegracoesGovernamentais",
]
