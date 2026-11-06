import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()

from core.database import SessionLocal
from core.models_db import ChatSessionDB, ChatMessageDB
import uuid

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    history: List[ChatMessage] = []

class ChatResponse(BaseModel):
    session_id: str
    response: str
    thoughts: List[str] = []
    subagents: List[str] = []
    components: List[Dict[str, Any]] = []


@router.get("/historico")
async def get_historico():
    """Retorna as conversas salvas no banco de dados."""
    db = SessionLocal()
    try:
        sessoes = db.query(ChatSessionDB).order_by(ChatSessionDB.atualizado_em.desc()).all()
        resumo_conversas = []
        for s in sessoes:
            msgs = db.query(ChatMessageDB).filter(ChatMessageDB.session_id == s.id).order_by(ChatMessageDB.criado_em.asc()).all()
            if not msgs:
                continue
            
            # Formata pra o frontend
            c = []
            for m in msgs:
                c.append({
                    "role": m.role,
                    "content": m.content,
                    "thoughts": m.thoughts,
                    "subagents": m.subagents
                })
            
            resumo_conversas.append({
                "id": s.id,
                "title": s.titulo,
                "messages": c
            })
            
        return {
            "total": len(resumo_conversas),
            "conversas": resumo_conversas
        }
    finally:
        db.close()


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    user_text = request.message
    session_id = request.session_id
    
    db = SessionLocal()
    
    if not session_id:
        session_id = str(uuid.uuid4())
        nova_sessao = ChatSessionDB(
            id=session_id,
            titulo=user_text[:32] + ("..." if len(user_text) > 32 else "")
        )
        db.add(nova_sessao)
    else:
        sessao = db.query(ChatSessionDB).filter(ChatSessionDB.id == session_id).first()
        if not sessao:
            session_id = str(uuid.uuid4())
            nova_sessao = ChatSessionDB(
                id=session_id,
                titulo=user_text[:32] + ("..." if len(user_text) > 32 else "")
            )
            db.add(nova_sessao)
    
    # Salva msg do usuario
    msg_user = ChatMessageDB(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="Usuário",
        content=user_text
    )
    db.add(msg_user)
    db.commit()
    
    # Prepara historico para o agente
    raw_historico = []
    msgs_db = db.query(ChatMessageDB).filter(ChatMessageDB.session_id == session_id).order_by(ChatMessageDB.criado_em.asc()).all()
    for m in msgs_db:
        raw_historico.append({"role": m.role, "content": m.content})
    
    resposta_texto = ""
    pensamentos = []
    subagentes_invocados = []
    componentes = []

    try:
        from utils.ai_providers import AIManager, AIProvider, get_ai_manager
        from core.agentes.supervisor import SupervisorRouter
        from core.correlacionador import Correlacionador
        from core.agentes.rag_auditor import AgenteRAG
        from core.agentes.reconhecimento import ReconhecimentoAgente
        from core.agentes.extrator_html_inteligente import VisionScraperAgente
        from core.agentes.extrator_anexos import CacadorAnexosAgente
        from core.agentes.osint_agente import AgenteOSINT
        from core.agentes.cartel_hunter import CartelHunterAgente
        from core.agentes.visao_espacial import VisaoGeoespacialAgente
        from core.agentes.pdf_forensic import ForensicAgente
        from core.agentes.promotor_legal import AgentePromotor
        from core.agentes.offshore_agent import OffshoreAgente
        from core.agentes.especialistas import (
            NavegadorAgente, AgenteGrafo, AgenteGeospatial, AgenteSancoes,
            AgenteBancario, AgenteExtrator, AgenteRelator, AgenteDiarioOficial, AgentePayroll
        )
        from core.agentes.avancados import (
            CrawlerAgente, PDFDownloaderAgente, CNPJValidatorAgente, CrossPortalAgente, ShadowAPIAgente
        )
        from core.leitor_universal import LeitorUniversal
        from core.vector_store import VectorStoreManager
        from api.routes.navegador import get_navegador

        try:
            ai_manager = get_ai_manager()
        except Exception as e_ai:
            print(f"[AVISO] get_ai_manager() falhou, usando AIManager com NVIDIA: {e_ai}")
            ai_manager = AIManager(default_provider=AIProvider.NVIDIA)
            
        correlacionador = Correlacionador()
        documentos_memoria = []
        
        leitor = LeitorUniversal()
        
        vsm = VectorStoreManager()
        
        especialistas = [
            AgenteGrafo(correlacionador),
            AgenteGeospatial(correlacionador),
            AgenteSancoes(correlacionador),
            AgenteBancario(documentos_memoria, ai_manager),
            AgenteExtrator(documentos_memoria, ai_manager),
            AgenteRelator(raw_historico, ai_manager),
            AgenteDiarioOficial(documentos_memoria, ai_manager),
            AgentePayroll(documentos_memoria, ai_manager),
            CNPJValidatorAgente(correlacionador),
            CrossPortalAgente(correlacionador),
            AgenteRAG(vsm),
            ReconhecimentoAgente(),
            AgenteOSINT(),
            CartelHunterAgente(correlacionador),
            VisaoGeoespacialAgente(ai_manager),
            ForensicAgente(),
            AgentePromotor(ai_manager),
            OffshoreAgente()
        ]
        
        # Conecta o mesmo Navegador Selenium usado no Split View
        nav = get_navegador()
        if nav:
            if not nav.driver:
                nav.iniciar()
            especialistas.insert(0, NavegadorAgente(nav))
            especialistas.insert(1, CrawlerAgente(nav))
            especialistas.insert(2, PDFDownloaderAgente(nav, leitor))
            especialistas.insert(3, ShadowAPIAgente(nav))
            especialistas.insert(4, VisionScraperAgente(nav, ai_manager))
            especialistas.insert(5, CacadorAnexosAgente(nav))
        
        supervisor = SupervisorRouter(ai_manager, especialistas)
        
        contexto = "Histórico da conversa:\n"
        for m in request.history[-6:]:
            contexto += f"{m.role}: {m.content}\n"
            
        def ui_callback(msg: str):
            try:
                print(f"[Supervisor UI]: {msg}")
            except Exception:
                pass
            subagentes_invocados.append(msg)
            
        def pensamento_callback(msg: str):
            pensamentos.append(msg)
            
        resposta = supervisor.processar(
            prompt_usuario=user_text,
            contexto_historico=contexto,
            callback_ui=ui_callback,
            callback_pensamento=pensamento_callback
        )
        
        if resposta:
            json_blocks = re.findall(r'```json\s*(.*?)\s*```', resposta, re.DOTALL)
            for j_block in json_blocks:
                try:
                    dados_json = json.loads(j_block)
                    if isinstance(dados_json, dict) and "tipo" in dados_json:
                        componentes.append(dados_json)
                except json.JSONDecodeError:
                    pass

            texto_limpo = re.sub(r'```json\s*(.*?)\s*```', '', resposta, flags=re.DOTALL).strip()
            resposta_texto = texto_limpo if texto_limpo else resposta.strip()
        else:
            resposta_texto = "Não foi possível extrair um relatório detalhado. Tente reformular a pergunta ou verificar se o portal exige autenticação."
        
    except Exception as e:
        print(f"[ERRO] Erro no processamento da IA: {e}")
        import traceback
        traceback.print_exc()
        resposta_texto = f"Ocorreu um erro ao conectar com o serviço de IA: {str(e)}"
            
    # Salva no banco a reposta da IA
    msg_ia = ChatMessageDB(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="IA Analisadora",
        content=resposta_texto,
        thoughts=pensamentos,
        subagents=subagentes_invocados
    )
    db.add(msg_ia)
    
    # Atualiza a sessao
    sessao = db.query(ChatSessionDB).filter(ChatSessionDB.id == session_id).first()
    if sessao:
        sessao.atualizado_em = msg_ia.criado_em
        
    db.commit()
    db.close()

    return ChatResponse(
        session_id=session_id,
        response=resposta_texto,
        thoughts=pensamentos,
        subagents=subagentes_invocados,
        components=componentes
    )
