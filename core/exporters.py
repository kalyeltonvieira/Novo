"""
Exportador Multiformato de Anomalias e Dados de Auditoria
==========================================================
Exporta relatórios em formatos Excel (.xlsx estilizado), GeoJSON e JSON-LD.
"""

import json
from typing import List, Dict, Any, Optional

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class Exportermultiformat:
    """Gerencia a conversão e exportação de anomalias para diversos formatos."""

    @staticmethod
    def exportar_excel(alertas: List[Dict[str, Any]], filepath: str) -> bool:
        """Exporta lista de alertas para um arquivo Excel estilizado."""
        if not OPENPYXL_AVAILABLE:
            # Fallback salva CSV se openpyxl não estiver instalado
            with open(filepath.replace(".xlsx", ".csv"), "w", encoding="utf-8") as f:
                f.write("id,tipo,titulo,severidade,valor_envolvido\n")
                for a in alertas:
                    f.write(f"{a.get('id')},{a.get('tipo')},{a.get('titulo')},{a.get('severidade')},{a.get('valor_envolvido', 0)}\n")
            return True

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Alertas de Anomalias"

        # Estilos
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        center_align = Alignment(horizontal="center", vertical="center")

        headers = ["ID", "Tipo", "Título", "Severidade", "Score Confiança", "Valor Envolvido (R$)", "Status"]
        ws.append(headers)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align

        for alerta in alertas:
            ws.append([
                alerta.get("id", ""),
                alerta.get("tipo", ""),
                alerta.get("titulo", ""),
                str(alerta.get("severidade", "")).upper(),
                alerta.get("score_confianca", 0.0),
                alerta.get("valor_envolvido", 0.0),
                alerta.get("status", "novo")
            ])

        wb.save(filepath)
        return True

    @staticmethod
    def exportar_geojson(entidades_com_coordenadas: List[Dict[str, Any]], filepath: str) -> bool:
        """Exporta locais de anomalias/contratos no padrão GeoJSON para renderização em mapa."""
        features = []
        for item in entidades_com_coordenadas:
            lat = item.get("latitude", -15.793889)
            lng = item.get("longitude", -47.882778)

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                },
                "properties": {
                    "id": item.get("id"),
                    "nome": item.get("nome"),
                    "valor": item.get("valor", 0),
                    "anomalia": item.get("anomalia", "Nenhuma")
                }
            }
            features.append(feature)

        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        return True
