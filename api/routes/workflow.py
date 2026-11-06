from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time

router = APIRouter()

# Estado global em memória para o workflow
class WorkflowState:
    def __init__(self):
        self.nodes = [
            {
                "id": "node_url",
                "type": "input",
                "title": "Portal da Transparência",
                "subtitle": "Validador de URL",
                "status": "pending",
                "progress": 0,
                "metrics": {},
                "details": "Aguardando entrada..."
            },
            {
                "id": "node_navegador",
                "type": "process",
                "title": "Navegador Autônomo",
                "subtitle": "Crawl & Captura Selenium",
                "status": "pending",
                "progress": 0,
                "metrics": {},
                "details": "Aguardando..."
            },
            {
                "id": "node_leitores",
                "type": "extract",
                "title": "Leitores Especializados",
                "subtitle": "HTML, PDF, Planilhas",
                "status": "pending",
                "progress": 0,
                "metrics": {},
                "details": "Aguardando arquivos do navegador..."
            },
            {
                "id": "node_entidades",
                "type": "entity",
                "title": "Identificador de Entidades",
                "subtitle": "Extrator de CNPJs",
                "status": "pending",
                "progress": 0,
                "metrics": {},
                "details": "Aguardando..."
            },
            {
                "id": "node_correlator",
                "type": "analysis",
                "title": "Correlator & Enriquecimento",
                "subtitle": "Integrações Gov",
                "status": "pending",
                "progress": 0,
                "metrics": {},
                "details": "Aguardando..."
            },
            {
                "id": "node_dossie",
                "type": "output",
                "title": "Gerador de Dossiê",
                "subtitle": "Relatório Final",
                "status": "pending",
                "progress": 0,
                "metrics": {},
                "details": "Aguardando..."
            }
        ]
        self.overall_progress = 0
        self.active_node_id = "node_url"

    def update_node(self, node_id: str, status: str = None, progress: int = None, details: str = None, metrics: dict = None):
        for node in self.nodes:
            if node["id"] == node_id:
                if status is not None: node["status"] = status
                if progress is not None: node["progress"] = progress
                if details is not None: node["details"] = details
                if metrics is not None: node["metrics"].update(metrics)
                
                if status == "running":
                    self.active_node_id = node_id
                
        # Atualiza progresso total
        total = sum(n["progress"] for n in self.nodes)
        self.overall_progress = int(total / len(self.nodes))

global_workflow_state = WorkflowState()

class NodeActionRequest(BaseModel):
    node_id: str
    action: str  # 'pause', 'retry', 'resume'

class NodeUpdateRequest(BaseModel):
    node_id: str
    status: Optional[str] = None
    progress: Optional[int] = None
    details: Optional[str] = None
    metrics: Optional[dict] = None

@router.get("/status")
def get_workflow_status():
    """
    Retorna o status REAL do workflow.
    """
    return {
        "nodes": global_workflow_state.nodes,
        "active_node_id": global_workflow_state.active_node_id,
        "overall_progress": global_workflow_state.overall_progress,
        "timestamp": time.time()
    }

@router.post("/update")
def update_workflow(req: NodeUpdateRequest):
    """
    Endpoint para agentes atualizarem o estado do workflow internamente.
    """
    global_workflow_state.update_node(
        node_id=req.node_id,
        status=req.status,
        progress=req.progress,
        details=req.details,
        metrics=req.metrics
    )
    return {"success": True}

@router.post("/action")
def execute_node_action(req: NodeActionRequest):
    """
    Pausa, retoma ou reinicia um agente/nó específico.
    """
    for node in global_workflow_state.nodes:
        if node["id"] == req.node_id:
            if req.action == "pause":
                node["status"] = "paused"
            elif req.action == "retry":
                node["status"] = "running"
                node["progress"] = 10
            elif req.action == "resume":
                node["status"] = "running"
            return {"success": True, "node": node}
    raise HTTPException(status_code=404, detail="Nó não encontrado.")
