import asyncio
import base64
import time
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

try:
    from core.navegador_automatizado import NavegadorAutomatizado
    NAVEGADOR_AVAILABLE = True
except ImportError:
    NAVEGADOR_AVAILABLE = False

router = APIRouter()

# Instância global compartilhada do navegador headless
_navegador_instancia = None

# Cache e throttling para screenshots
_last_screenshot_time = 0
_last_screenshot_bytes = None
_last_screenshot_url = None
SCREENSHOT_THROTTLE_MS = 500  # Mínimo 500ms entre capturas
SCREENSHOT_CACHE_SECONDS = 2  # Reusa screenshot por 2 segundos

def get_navegador():
    global _navegador_instancia
    if NAVEGADOR_AVAILABLE and _navegador_instancia is None:
        try:
            _navegador_instancia = NavegadorAutomatizado(headless=True)
        except Exception:
            _navegador_instancia = None
    return _navegador_instancia

class NavegarRequest(BaseModel):
    url: str

@router.get("/status")
async def get_status():
    nav = get_navegador()
    return {
        "disponivel": NAVEGADOR_AVAILABLE,
        "ativo": nav is not None and nav.driver is not None,
        "url_atual": nav.driver.current_url if (nav and nav.driver) else None
    }

@router.post("/navegar")
async def navegar(req: NavegarRequest):
    nav = get_navegador()
    if not nav:
        return {"sucesso": False, "erro": "Navegador Selenium não disponível."}
    
    if not nav.driver:
        sucesso_init = nav.iniciar()
        if not sucesso_init:
            return {"sucesso": False, "erro": "Falha ao iniciar o navegador Chrome/Edge."}
            
    sucesso = nav.navegar(req.url)
    screenshot_b64 = None
    if sucesso:
        screenshot_bytes = nav.capturar_tela()
        if screenshot_bytes:
            screenshot_b64 = "data:image/png;base64," + base64.b64encode(screenshot_bytes).decode('utf-8')
            
    return {
        "sucesso": sucesso,
        "url": req.url,
        "screenshot": screenshot_b64
    }

@router.get("/screenshot")
async def get_screenshot():
    """Retorna screenshot com throttling e cache para evitar rate limiting."""
    global _last_screenshot_time, _last_screenshot_bytes, _last_screenshot_url
    
    nav = get_navegador()
    if not nav or not nav.driver:
        return {"ativo": False, "screenshot": None}
    
    current_time = time.time()
    current_url = nav.driver.current_url
    
    # Verifica se pode reusar cache (mesma URL e dentro do tempo de cache)
    time_since_last = (current_time - _last_screenshot_time) * 1000
    if (_last_screenshot_bytes is not None and 
        _last_screenshot_url == current_url and 
        time_since_last < SCREENSHOT_CACHE_SECONDS * 1000):
        b64 = "data:image/png;base64," + base64.b64encode(_last_screenshot_bytes).decode('utf-8')
        return {
            "ativo": True,
            "url": current_url,
            "screenshot": b64,
            "cached": True
        }
    
    # Throttling: aguarda tempo mínimo entre capturas
    if time_since_last < SCREENSHOT_THROTTLE_MS:
        await asyncio.sleep((SCREENSHOT_THROTTLE_MS - time_since_last) / 1000)
    
    try:
        screenshot_bytes = nav.capturar_tela()
        if screenshot_bytes:
            _last_screenshot_bytes = screenshot_bytes
            _last_screenshot_time = time.time()
            _last_screenshot_url = current_url
            b64 = "data:image/png;base64," + base64.b64encode(screenshot_bytes).decode('utf-8')
            return {
                "ativo": True,
                "url": current_url,
                "screenshot": b64,
                "cached": False
            }
        return {"ativo": True, "url": current_url, "screenshot": None}
    except Exception as e:
        return {"ativo": False, "erro": str(e), "screenshot": None}
