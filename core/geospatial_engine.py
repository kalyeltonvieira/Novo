"""
Engine Geospacial 3D e Rastreamento de Obras Públicas
======================================================
Converte endereços e coordenadas em dados de mapa 3D (KML/GeoJSON).
"""

import json
from typing import Dict, Any, List


class GeospatialEngine:
    """Mapeamento geográfico e análise espacial de obras públicas."""

    def gerar_camada_3d_obras(self, obras: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera um contrato GeoJSON com elevação 3D representando percentual executado vs pago."""
        features = []
        for obra in obras:
            lat = obra.get("lat", -15.793889)
            lng = obra.get("lng", -47.882778)
            pct_pago = obra.get("pct_pago", 100)
            pct_executado = obra.get("pct_executado", 20)

            # Inconsistência de obra fantasma (pago muito superior ao executado)
            alerta_obra = "ALERTA: Obra com pagamento muito superior à execução física" if (pct_pago - pct_executado) > 40 else "Normal"

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat, pct_pago * 10]  # Z axis = Altura visual 3D
                },
                "properties": {
                    "id": obra.get("id"),
                    "nome": obra.get("nome"),
                    "pct_pago": pct_pago,
                    "pct_executado": pct_executado,
                    "alerta": alerta_obra
                }
            }
            features.append(feature)

        return {
            "type": "FeatureCollection",
            "features": features
        }
