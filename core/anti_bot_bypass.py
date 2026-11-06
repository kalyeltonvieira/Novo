"""
Bypass Inteligente Anti-Bot e CAPTCHAs
======================================
Estratégias de navegação humanizada e resolução heurística de verificações públicas.
"""

import random
import time
from typing import Dict, Any, Optional


class AntiBotBypass:
    """Gerenciador de contorno de proteções anti-bot e verificações em portais."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
    ]

    def obter_user_agent_aleatorio(self) -> str:
        """Retorna um User-Agent válido e atualizado para rotação."""
        return random.choice(self.USER_AGENTS)

    def resolver_desafio_numerico(self, expressao_matematica: str) -> Optional[int]:
        """Resolve desafios simples de CAPTCHA numérico (ex: 'Quanto é 5 + 3?')."""
        try:
            # Limpa o texto para isolar a operação
            exp = expressao_matematica.lower().replace("quanto é", "").replace("?", "").strip()
            if "+" in exp:
                parts = exp.split("+")
                return int(parts[0].strip()) + int(parts[1].strip())
            elif "-" in exp:
                parts = exp.split("-")
                return int(parts[0].strip()) - int(parts[1].strip())
        except Exception:
            pass
        return None
