"""
Configuração de Logging - Utilitário Centralizado
===================================================
Substitui prints espalhados por logging estruturado.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def configurar_logging(nome: str = "ia_analisadora", nivel: str = None) -> logging.Logger:
    """
    Configura e retorna um logger centralizado.

    Args:
        nome: Nome do logger
        nivel: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Se None, lê da variável LOG_LEVEL ou usa INFO.

    Returns:
        Logger configurado
    """
    if nivel is None:
        nivel = os.environ.get("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger(nome)

    # Evita duplicar handlers se já configurado
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, nivel, logging.INFO))

    # Formato
    formato = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formato)
    console_handler.setLevel(getattr(logging, nivel, logging.INFO))
    logger.addHandler(console_handler)

    # Handler arquivo (rotativo)
    try:
        os.makedirs("data/logs", exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join("data/logs", "app.log"),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formato)
        file_handler.setLevel(getattr(logging, nivel, logging.INFO))
        logger.addHandler(file_handler)
    except Exception:
        # Se não conseguir criar arquivo, só usa console
        pass

    return logger


def get_logger(nome: str = "ia_analisadora") -> logging.Logger:
    """Retorna logger configurado (atalho para configurar_logging)."""
    return configurar_logging(nome)