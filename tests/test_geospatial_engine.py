"""
Testes Unitários da Engine Geospacial 3D
=========================================
"""

import pytest
from core.geospatial_engine import GeospatialEngine


def test_gerar_camada_3d_obras():
    engine = GeospatialEngine()
    obras = [
        {"id": "obra_1", "nome": "Construção de Ponte", "lat": -15.8, "lng": -47.9, "pct_pago": 100, "pct_executado": 10}
    ]
    res = engine.gerar_camada_3d_obras(obras)
    assert res["type"] == "FeatureCollection"
    assert len(res["features"]) == 1
    assert "ALERTA" in res["features"][0]["properties"]["alerta"]
    assert res["features"][0]["geometry"]["coordinates"][2] == 1000  # Z elevation
