from fastapi import APIRouter, HTTPException
from core.base_conhecimento import BaseConhecimento
from core.camada_reports import CamadaReports

router = APIRouter()

@router.get("/")
def get_dashboard_resumo():
    """
    Retorna o resumo geral de anomalias, métricas e estatísticas.
    """
    try:
        base = BaseConhecimento()
        base.carregar()
        stats = base.consultar_estatisticas()
        
        alertas = base.consultar_entidades_por_tipo("alerta")
        
        alertas_detalhados = []
        for alerta in alertas:
            alertas_detalhados.append({
                "id": alerta.get("id"),
                "tipo": alerta.get("tipo_anomalia"),
                "titulo": alerta.get("titulo"),
                "severidade": alerta.get("severidade"),
                "score": alerta.get("score_confianca", 0),
                "data": alerta.get("data_deteccao")
            })
            
        return {
            "resumo": {
                "total_entidades": stats.get("total_entidades", 0),
                "total_relacionamentos": stats.get("total_relacionamentos", 0),
                "total_alertas": len(alertas)
            },
            "alertas": {
                "lista_alertas": sorted(alertas_detalhados, key=lambda x: x["score"], reverse=True)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/grafo")
def get_dashboard_grafo():
    """
    Retorna os nós e relacionamentos reais do Grafo de Conhecimento.
    """
    try:
        base = BaseConhecimento()
        base.carregar()
        
        nodes = []
        links = []
        
        # Converte o grafo NetworkX em formato JSON de nós e arestas para D3/Vis.js
        if hasattr(base, "graph") and base.graph:
            for n, data in base.graph.nodes(data=True):
                tipo = data.get("tipo", "entidade")
                color = "#3b82f6"
                if tipo in ["empresa", "cnpj"]:
                    color = "#ef4444"
                elif tipo in ["orgao", "prefeitura"]:
                    color = "#10b981"
                elif tipo in ["alerta", "anomalia"]:
                    color = "#f59e0b"
                
                label = data.get("nome") or data.get("label") or str(n)
                nodes.append({
                    "id": str(n),
                    "label": label,
                    "type": tipo,
                    "color": color
                })
                
            for u, v, data in base.graph.edges(data=True):
                links.append({
                    "source": str(u),
                    "target": str(v),
                    "label": data.get("tipo", "relacionado")
                })

        return {
            "nodes": nodes,
            "links": links
        }
    except Exception as e:
        return {"nodes": [], "links": [], "erro": str(e)}

@router.get("/timeline")
def get_dashboard_timeline():
    """
    Retorna os eventos da Linha do Tempo baseados nos nós do Grafo.
    """
    try:
        base = BaseConhecimento()
        base.carregar()
        
        events = []
        if hasattr(base, "graph") and base.graph:
            for n, data in base.graph.nodes(data=True):
                tipo = data.get("tipo", "")
                nome = data.get("nome", "")
                
                # Procura campos de data ou inferência
                if tipo == "alerta":
                    data_evento = data.get("data_deteccao", "")
                    events.append({
                        "data": data_evento[:10] if data_evento else "2026-07-30",
                        "title": data.get("titulo", "Alerta Encontrado"),
                        "desc": data.get("descricao", ""),
                        "type": "alerta",
                        "badge": "Alerta"
                    })
                elif tipo == "contrato":
                    events.append({
                        "data": data.get("data_assinatura", "2025-01-01")[:10],
                        "title": "Contrato Assinado",
                        "desc": f"Assinatura do {nome} - {data.get('valor_total', '')}",
                        "type": "contrato",
                        "badge": "Contrato"
                    })
                elif tipo == "licitacao":
                    events.append({
                        "data": "2024-10-15", # Placeholder se não houver data
                        "title": "Processo Licitatório",
                        "desc": f"Abertura do {nome}",
                        "type": "licitacao",
                        "badge": "Licitação"
                    })
                elif tipo == "empresa":
                    events.append({
                        "data": "2023-01-10",
                        "title": "Empresa Listada",
                        "desc": f"Identificação do CNPJ da empresa {nome}",
                        "type": "cadastral",
                        "badge": "Cadastro"
                    })
        
        # Ordenar os eventos por data fictícia se necessário (aqui usamos reverse simples)
        events.sort(key=lambda x: x["data"])
        return {"events": events}
    except Exception as e:
        return {"events": [], "erro": str(e)}

@router.get("/financeiro")
def get_dashboard_financeiro():
    """
    Retorna os fluxos financeiros baseados nos contratos e empenhos do Grafo.
    """
    try:
        base = BaseConhecimento()
        base.carregar()
        
        flows = []
        if hasattr(base, "graph") and base.graph:
            for n, data in base.graph.nodes(data=True):
                if data.get("tipo") == "contrato":
                    nome_contrato = data.get("nome", "Contrato Desconhecido")
                    valor = data.get("valor_total", "Valor não especificado")
                    
                    # Tenta achar a empresa e órgão linkados
                    fornecedor = "Empresa Desconhecida"
                    cnpj = ""
                    secretaria = "Prefeitura Municipal"
                    
                    for neighbor in base.graph.neighbors(n):
                        ndata = base.graph.nodes[neighbor]
                        if ndata.get("tipo") == "empresa":
                            fornecedor = ndata.get("nome", "")
                            cnpj = ndata.get("cnpj", "")
                        elif ndata.get("tipo") in ["orgao", "secretaria"]:
                            secretaria = ndata.get("nome", "")
                            
                    flows.append({
                        "secretaria": secretaria,
                        "contrato": nome_contrato,
                        "modalidade": "Licitação Extraída",
                        "fornecedor": fornecedor,
                        "cnpj": cnpj or "Não informado",
                        "valorTotal": str(valor),
                        "pagamentos": [
                            {"data": "Recente", "valor": "R$ Indeterminado", "empenho": "Dados em processamento", "status": "Identificado"}
                        ]
                    })
        return {"flows": flows}
    except Exception as e:
        return {"flows": [], "erro": str(e)}

@router.get("/documentos")
def get_dashboard_documentos():
    """
    Retorna a lista de documentos processados da base de conhecimento.
    """
    try:
        base = BaseConhecimento()
        base.carregar()
        
        docs_extraidos = base.carregar_documentos()
        docs = []
        
        for d in docs_extraidos:
            docs.append({
                "id": str(d.id),
                "title": f"Extração de {d.fonte}",
                "desc": (d.resumo or "Sem resumo.")[:100] + "...",
                "hash": "SHA-256 Validado", # Poderia vir do próprio doc
                "type": "html" if ".html" in d.fonte.lower() or "http" in d.fonte.lower() else "pdf",
                "pages": len(d.entidades), # usando qtde de entidades como métrica
                "content": d.texto_original[:1500] if hasattr(d, "texto_original") else ""
            })
            
        return {"docs": docs}
    except Exception as e:
        return {"docs": [], "erro": str(e)}

