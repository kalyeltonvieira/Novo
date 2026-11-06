import os
import sys
import time

# Configurar enquadramento seguro de stdout/stderr no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import dashboard, documentos, chat, navegador, relatorios, ws
from collections import defaultdict
# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("api.main")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.api")
    metrics = None
    MONITORING_AVAILABLE = False

app = FastAPI(
    title="IA Analisadora API",
    description="API do Cérebro da Transparência",
    version="1.0.0"
)

# Rate Limiting granular (em memória por IP e categoria de rota)
_rate_limit_store: dict = defaultdict(lambda: defaultdict(list))
RATE_LIMIT_DEFAULTS = {
    "heavy": (200, 60),     # (max_requests, window_seconds) para rotas pesadas (relatorios/gerar, chat)
    "default": (1000, 60),  # limite padrão para demais endpoints
}


def _get_rate_limit_category(path: str) -> str:
    if "/api/navegador/screenshot" in path:
        return "default"
    if any(h in path for h in ["/api/relatorios/gerar", "/api/chat"]):
        return "heavy"
    return "default"


@app.middleware("http")
async def monitoring_and_rate_limit_middleware(request: Request, call_next):
    """Middleware de monitoramento e rate limiting granular por IP e rota."""
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    category = _get_rate_limit_category(path)
    max_requests, window_seconds = RATE_LIMIT_DEFAULTS[category]
    now = time.time()
    window_start = now - window_seconds

    # Filtra requisições da janela
    timestamps = [t for t in _rate_limit_store[client_ip][category] if t > window_start]
    _rate_limit_store[client_ip][category] = timestamps

    if len(timestamps) >= max_requests:
        if MONITORING_AVAILABLE and metrics:
            metrics.increment("api_rate_limit_exceeded", tags={"ip": client_ip, "category": category})
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Muitas requisições para a categoria '{category}'. Aguarde um momento.",
                "retry_after": window_seconds
            },
            headers={
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0"
            }
        )

    _rate_limit_store[client_ip][category].append(now)
    remaining = max_requests - len(_rate_limit_store[client_ip][category])

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    response.headers["X-RateLimit-Limit"] = str(max_requests)
    response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

    if MONITORING_AVAILABLE and metrics:
        metrics.increment("api_requests_total", tags={"path": path, "status": str(response.status_code)})
        metrics.record_timing("api_request_duration", duration, tags={"path": path})

    return response


# Configuração de CORS (permitindo acesso do Next.js local e qualquer origem dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_origin_regex=r"http://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import dashboard, documentos, chat, navegador, relatorios, ws, workflow, exportador

# Inclusão das rotas
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(documentos.router, prefix="/api/documentos", tags=["Documentos"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(navegador.router, prefix="/api/navegador", tags=["Navegador"])
app.include_router(relatorios.router, prefix="/api/relatorios", tags=["Relatórios"])
app.include_router(ws.router, prefix="/api/ws", tags=["WebSocket"])
app.include_router(workflow.router, prefix="/api/workflow", tags=["Workflow"])
app.include_router(exportador.router, prefix="/api/exportar", tags=["Exportação"])


from api.auth import create_access_token, verify_password, hash_password
from api.dependencies import get_current_user
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/token", tags=["Autenticação"])
def login(request: LoginRequest):
    """Endpoint de login que gera token de acesso JWT."""
    if request.username == "admin" and request.password in ["admin123", "admin"]:
        token = create_access_token({"sub": request.username, "role": "admin"})
        return {"access_token": token, "token_type": "bearer", "user": {"username": "admin", "role": "admin"}}
    raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")

@app.get("/api/users/me", tags=["Autenticação"])
def read_current_user(current_user: dict = Depends(get_current_user)):
    """Retorna os dados do usuário atualmente autenticado."""
    return current_user

@app.get("/")
def read_root():
    return {
        "sistema": "Cérebro da Transparência",
        "status": "online",
        "versao": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """
    Health check completo da API.
    Verifica disponibilidade dos módulos principais.
    """
    health_status = {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "modules": {}
    }

    # Verifica core
    try:
        from core.leitor_universal import LeitorUniversal
        health_status["modules"]["leitor"] = "disponivel"
    except Exception as e:
        health_status["modules"]["leitor"] = f"indisponivel: {str(e)}"
        health_status["status"] = "degradado"

    try:
        from core.detector_anomalias import DetectorAnomalias
        health_status["modules"]["detector"] = "disponivel"
    except Exception as e:
        health_status["modules"]["detector"] = f"indisponivel: {str(e)}"
        health_status["status"] = "degradado"

    try:
        from core.base_conhecimento import BaseConhecimento
        base = BaseConhecimento()
        base.carregar()
        stats = base.consultar_estatisticas()
        health_status["modules"]["base_conhecimento"] = "disponivel"
        health_status["estatisticas"] = stats
    except Exception as e:
        health_status["modules"]["base_conhecimento"] = f"indisponivel: {str(e)}"

    # Verifica IA
    try:
        from utils.ai_providers import get_ai_manager
        ai_manager = get_ai_manager()
        client = ai_manager.get_client()
        health_status["modules"]["ia"] = {
            "status": "disponivel" if client and client.is_available() else "indisponivel",
            "provider": ai_manager.default_provider.value if client else "unknown",
        }
        if not client or not client.is_available():
            health_status["status"] = "degradado"
    except Exception as e:
        health_status["modules"]["ia"] = {"status": f"indisponivel: {str(e)}"}
        health_status["status"] = "degradado"

    # Verifica navegador
    try:
        from core.navegador_automatizado import NavegadorAutomatizado
        nav = NavegadorAutomatizado(headless=True)
        health_status["modules"]["navegador"] = "disponivel" if nav else "indisponivel"
    except Exception as e:
        health_status["modules"]["navegador"] = f"indisponivel: {str(e)}"

    return health_status