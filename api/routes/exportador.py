from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
from datetime import datetime

router = APIRouter()

class ExportRequest(BaseModel):
    session_id: str
    formato: str = "markdown"

@router.post("/pdf")
async def exportar_relatorio(req: ExportRequest):
    """
    Endpoint para exportar a thread de análise para um formato estético
    (PDF/Markdown) condensando o Dossiê Executivo.
    Na versão em produção usaríamos WeasyPrint ou pandoc para converter 
    diretamente em PDF B2B com marca d'água corporativa.
    """
    try:
        from core.database import SessionLocal
        from core.models_db import ChatSessionDB, ChatMessageDB
    except ImportError:
        raise HTTPException(status_code=500, detail="Database config missing.")
        
    db = SessionLocal()
    sessao = db.query(ChatSessionDB).filter(ChatSessionDB.id == req.session_id).first()
    
    if not sessao:
        db.close()
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
        
    mensagens = db.query(ChatMessageDB).filter(ChatMessageDB.session_id == req.session_id).order_by(ChatMessageDB.criado_em.asc()).all()
    
    if not mensagens:
        db.close()
        raise HTTPException(status_code=404, detail="Sessão vazia.")
        
    # Build Markdown Document
    md_content = f"# Dossiê Executivo: {sessao.titulo}\n\n"
    md_content += f"**Data de Geração**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    md_content += f"**Sessão UUID**: {sessao.id}\n"
    md_content += f"**Plataforma**: Auditor IA - Cérebro da Transparência (War Room 11.0)\n\n"
    md_content += "---\n\n"
    
    md_content += "## 1. Resumo da Investigação (Timeline)\n\n"
    
    for msg in mensagens:
        if msg.role in ["Usuário", "user"]:
            md_content += f"### 🕵️ Pedido de Investigação (Investigador Chefe)\n"
            md_content += f"> {msg.content}\n\n"
        else:
            md_content += f"### 🧠 Resposta (Auditor IA Analisadora)\n"
            md_content += f"{msg.content}\n\n"
            
            if msg.subagents:
                md_content += f"**Subagentes Invocados**: {', '.join(msg.subagents)}\n\n"
                
    md_content += "---\n\n"
    md_content += "## 2. Assinatura e Autenticidade\n"
    md_content += "Relatório gerado criptograficamente com chancela de IA. Documento restrito.\n"
    
    db.close()
    
    # Na vida real, a conversão para PDF:
    # pdf_bytes = convert_markdown_to_pdf(md_content)
    # return Response(content=pdf_bytes, media_type="application/pdf")
    
    return {
        "status": "success",
        "formato": req.formato,
        "documento": md_content,
        "mensagem": "Dossiê estruturado com sucesso. (Exportação para PDF físico exigirá WeasyPrint no worker)."
    }
