"""
WebSocket Routes - API
======================
Streaming de respostas do chat via WebSocket.
"""

import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

router = APIRouter()

# Conexões WebSocket ativas
active_connections: Set[WebSocket] = set()


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket para chat em tempo real.
    Envia mensagens do usuário e recebe respostas streamadas do supervisor.
    """
    await websocket.accept()
    active_connections.add(websocket)

    try:
        while True:
            # Recebe mensagem do cliente
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_text = message_data.get("message", "")
            history = message_data.get("history", [])

            # Confirma recebimento
            await websocket.send_json({
                "type": "status",
                "content": "Processando mensagem..."
            })

            try:
                from utils.ai_providers import AIManager, AIProvider, get_ai_manager
                from core.agentes.supervisor import SupervisorRouter
                from core.correlacionador import Correlacionador
                from core.agentes.especialistas import (
                    NavegadorAgente, AgenteGrafo, AgenteGeospatial, AgenteSancoes,
                    AgenteBancario, AgenteExtrator, AgenteRelator, AgenteDiarioOficial, AgentePayroll
                )
                from api.routes.navegador import get_navegador

                try:
                    ai_manager = get_ai_manager()
                except Exception:
                    ai_manager = AIManager(default_provider=AIProvider.NVIDIA)

                correlacionador = Correlacionador()
                documentos_memoria = []

                especialistas = [
                    AgenteGrafo(correlacionador),
                    AgenteGeospatial(correlacionador),
                    AgenteSancoes(correlacionador),
                    AgenteBancario(documentos_memoria, ai_manager),
                    AgenteExtrator(documentos_memoria, ai_manager),
                    AgenteRelator(history, ai_manager),
                    AgenteDiarioOficial(documentos_memoria, ai_manager),
                    AgentePayroll(documentos_memoria, ai_manager)
                ]

                nav = get_navegador()
                if nav:
                    if not nav.driver:
                        nav.iniciar()
                    especialistas.insert(0, NavegadorAgente(nav))

                supervisor = SupervisorRouter(ai_manager, especialistas)

                # Callbacks para streaming via WebSocket
                async def ui_callback(msg: str):
                    await websocket.send_json({
                        "type": "subagent",
                        "content": msg
                    })

                async def pensamento_callback(msg: str):
                    await websocket.send_json({
                        "type": "thought",
                        "content": msg
                    })

                # Processa a mensagem (de forma síncrona por enquanto)
                resposta = supervisor.processar(
                    prompt_usuario=user_text,
                    contexto_historico="\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in history[-6:]]),
                    callback_ui=lambda msg: asyncio.run_coroutine_threadsafe(
                        ui_callback(msg), asyncio.get_event_loop()
                    ),
                    callback_pensamento=lambda msg: asyncio.run_coroutine_threadsafe(
                        pensamento_callback(msg), asyncio.get_event_loop()
                    )
                )

                if resposta:
                    await websocket.send_json({
                        "type": "response",
                        "content": resposta
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "content": "Não foi possível obter uma resposta."
                    })

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Erro ao processar: {str(e)}"
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections.discard(websocket)


@router.get("/status")
async def ws_status():
    """Retorna o número de conexões WebSocket ativas."""
    return {
        "conexoes_ativas": len(active_connections),
        "websocket_endpoint": "/api/ws/chat"
    }