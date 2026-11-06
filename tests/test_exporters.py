"""
Testes de Exportação Multiformato (Excel e GeoJSON)
===================================================
"""

import os
import json
import pytest
import tempfile
from core.exporters import Exportermultiformat


def test_exportar_excel():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_alertas.xlsx")
        alertas = [
            {"id": "a1", "tipo": "nepotismo", "titulo": "Parentesco", "severidade": "critica", "score_confianca": 0.9, "valor_envolvido": 100000.0, "status": "novo"}
        ]
        ok = Exportermultiformat.exportar_excel(alertas, filepath)
        assert ok is True
        assert os.path.exists(filepath) or os.path.exists(filepath.replace(".xlsx", ".csv"))


def test_exportar_geojson():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_map.geojson")
        entidades = [
            {"id": "e1", "nome": "Empresa X", "latitude": -23.5505, "longitude": -46.6333, "valor": 50000, "anomalia": "Fracionamento"}
        ]
        ok = Exportermultiformat.exportar_geojson(entidades, filepath)
        assert ok is True
        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["type"] == "FeatureCollection"
            assert len(data["features"]) == 1
            assert data["features"][0]["geometry"]["coordinates"] == [-46.6333, -23.5505]
