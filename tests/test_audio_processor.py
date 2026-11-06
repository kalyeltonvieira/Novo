"""
Testes Unitários do Processador de Áudio
=========================================
"""

import pytest
from core.audio_processor import AudioProcessor


def test_audio_processor_sem_arquivo():
    ap = AudioProcessor()
    res = ap.transcrever_audio("audio_inexistente.mp3")
    assert res["status"] == "erro"


def test_analisar_suspeitas_fala():
    ap = AudioProcessor()
    suspeitas = ap._analisar_suspeitas_fala("Conversa entre concorrentes para dividir o lote no pregão.")
    assert len(suspeitas) >= 1
    assert "dividir o lote" in suspeitas[0]
