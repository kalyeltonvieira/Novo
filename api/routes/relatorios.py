"""
Rotas de Relatórios - API
=========================
Endpoints para gerar e consultar relatórios.
"""

import os
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.camada_reports import CamadaReports
from core.base_conhecimento import BaseConhecimento
from core.entidades import Documento, Alerta, TipoAnomalia

router = APIRouter()


class RelatorioResponse(BaseModel):
    id: str
    titulo: str
    tipo: str
    data_geracao: str
    caminho_html: Optional[str] = None
    caminho_json: Optional[str] = None
    total_alertas: int = 0
    total_documentos: int = 0


@router.get("/")
async def listar_relatorios():
    """Lista todos os relatórios gerados."""
    reports_dir = os.path.join("data", "reports")
    if not os.path.exists(reports_dir):
        return {"relatorios": [], "total": 0}

    relatorios = []
    for arquivo in sorted(os.listdir(reports_dir), reverse=True):
        caminho = os.path.join(reports_dir, arquivo)
        if os.path.isfile(caminho):
            ext = os.path.splitext(arquivo)[1].lower()
            if ext in (".html", ".json"):
                stats = os.stat(caminho)
                relatorios.append({
                    "nome": arquivo,
                    "caminho": caminho,
                    "tipo": ext.replace(".", ""),
                    "tamanho_bytes": stats.st_size,
                    "data_modificacao": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                })

    return {"relatorios": relatorios, "total": len(relatorios)}


@router.get("/gerar")
@router.post("/gerar", response_model=RelatorioResponse)
async def gerar_relatorio(formato: Optional[str] = Query("html")):
    """
    Gera um novo relatório com base nos dados atuais da base de conhecimento.
    """
    try:
        base = BaseConhecimento()
        base.carregar()

        stats = base.consultar_estatisticas()
        alertas_data = base.consultar_entidades_por_tipo("alerta")
        documentos_data = base.carregar_documentos()

        # Constrói dados para o dashboard
        alertas = []
        for a in alertas_data[:100]:
            alertas.append({
                "id": a.get("id", ""),
                "tipo": a.get("tipo_anomalia", "desconhecido"),
                "titulo": a.get("titulo", ""),
                "descricao": a.get("descricao", ""),
                "severidade": a.get("severidade", "media"),
                "score_confianca": a.get("score_confianca", 0),
                "data_deteccao": a.get("data_deteccao", ""),
                "status": a.get("status", "novo"),
            })

        docs = []
        for d in documentos_data[:50]:
            docs.append({
                "id": d.id,
                "fonte": d.fonte,
                "tipo": d.tipo.value,
                "data_processamento": d.data_processamento.isoformat(),
                "entidades": len(d.entidades),
                "resumo": (d.resumo or "")[:200],
            })

        dados_dashboard = {
            "resumo": {
                "total_documentos": len(documentos_data),
                "total_entidades": stats.get("total_entidades", 0),
                "total_alertas": len(alertas_data),
                "total_relacionamentos": stats.get("total_relacionamentos", 0),
                "data_analise": datetime.now().strftime("%d/%m/%Y %H:%M"),
            },
            "alertas": {
                "total": len(alertas),
                "lista_alertas": alertas[:50],
            },
            "documentos": docs,
            "estatisticas": stats,
        }

        # Gera relatório
        reports = CamadaReports()
        caminho_html = reports.exportar_html(dados_dashboard)
        caminho_json = reports.exportar_json(dados_dashboard)

        return RelatorioResponse(
            id=f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            titulo="Relatório de Análise",
            tipo="analise",
            data_geracao=datetime.now().isoformat(),
            caminho_html=caminho_html,
            caminho_json=caminho_json,
            total_alertas=len(alertas),
            total_documentos=len(documentos_data),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar relatório: {str(e)}")


@router.get("/exportar/{formato}")
async def exportar_dados(
    formato: str,
    tipo: str = Query("todos", description="Tipo de dados: todos, alertas, entidades, empresas, pessoas"),
):
    """
    Exporta dados em CSV ou Excel.
    formato: 'csv' ou 'xlsx'
    tipo: 'todos', 'alertas', 'entidades', 'empresas', 'pessoas'
    """
    from utils.data_export import DataExporter
    from core.correlacionador import Correlacionador

    if formato not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="Formato deve ser 'csv' ou 'xlsx'")

    try:
        base = BaseConhecimento()
        base.carregar()
        documentos = base.carregar_documentos()

        correlacionador = Correlacionador()
        for doc in documentos:
            correlacionador._montar_pessoas_e_empresas(doc.entidades)

        alertas_data = base.consultar_entidades_por_tipo("alerta")
        alertas = []
        for a in alertas_data:
            alertas.append(Alerta(
                id=a.get("id", ""),
                tipo=TipoAnomalia.SUPERFATURAMENTO,
                titulo=a.get("titulo", ""),
                descricao=a.get("descricao", ""),
                severidade=a.get("severidade", "media"),
                score_confianca=a.get("score_confianca", 0),
            ))

        exporter = DataExporter()
        arquivos = []

        if tipo in ("todos", "alertas"):
            arquivos.append(exporter.export_alertas_csv(alertas))
        if tipo in ("todos", "entidades"):
            for doc in documentos:
                arquivos.append(exporter.export_entidades_csv(doc.entidades))
        if tipo in ("todos", "empresas"):
            arquivos.append(exporter.export_empresas_csv(correlacionador.empresas))
        if tipo in ("todos", "pessoas"):
            arquivos.append(exporter.export_pessoas_csv(correlacionador.pessoas))
        if tipo == "todos" and formato == "xlsx":
            arquivos.append(exporter.export_all_to_excel(documentos, alertas, [], correlacionador.pessoas, correlacionador.empresas))

        return {
            "sucesso": True,
            "arquivos_gerados": arquivos,
            "formato": formato,
            "tipo": tipo,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao exportar dados: {str(e)}")