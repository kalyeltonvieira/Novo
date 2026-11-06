"""
Módulo de Monitoramento e Logging Centralizado
================================================
Fornece funcionalidades de logging estruturado, métricas e monitoramento
para toda a aplicação.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import os


class StructuredLogger:
    """
    Logger estruturado com suporte a JSON e múltiplos handlers.
    
    Este logger centraliza todos os logs da aplicação, permitindo:
    - Formatação em JSON para análise posterior
    - Múltiplos níveis de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Handlers para console, arquivo e serviços externos
    - Contexto adicional em cada log (user_id, request_id, etc.)
    
    Attributes:
        name (str): Nome do logger
        logger (logging.Logger): Instância do logger Python
        context (Dict[str, Any]): Contexto padrão para todos os logs
    """
    
    def __init__(self, name: str, log_level: str = "INFO", log_dir: str = "data/logs"):
        """
        Inicializa o logger estruturado.
        
        Args:
            name: Nome do logger (geralmente o nome do módulo)
            log_level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Diretório para armazenar logs em arquivo
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.context: Dict[str, Any] = {}
        
        # Evita duplicação de handlers
        if not self.logger.handlers:
            self._setup_handlers(log_dir)
    
    def _setup_handlers(self, log_dir: str) -> None:
        """Configura handlers para console e arquivo."""
        # Cria diretório de logs se não existir
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Handler de console com formatação simples
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Handler de arquivo com formatação JSON
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"{self.name}.log")
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = JsonFormatter()
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
    
    def set_context(self, **kwargs) -> None:
        """
        Define contexto adicional para todos os logs subsequentes.
        
        Args:
            **kwargs: Pares chave-valor para contexto (ex: user_id, request_id)
        """
        self.context.update(kwargs)
    
    def clear_context(self) -> None:
        """Limpa o contexto adicional."""
        self.context.clear()
    
    def _log(self, level: int, message: str, **kwargs) -> None:
        """
        Método interno para log com contexto.
        
        Args:
            level: Nível de log (logging.DEBUG, etc.)
            message: Mensagem do log
            **kwargs: Dados adicionais para o log
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "level": logging.getLevelName(level),
            **self.context,
            **kwargs
        }
        self.logger.log(level, json.dumps(log_data))
    
    def debug(self, message: str, **kwargs) -> None:
        """Log no nível DEBUG."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log no nível INFO."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log no nível WARNING."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log no nível ERROR."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log no nível CRITICAL."""
        self._log(logging.CRITICAL, message, **kwargs)


class JsonFormatter(logging.Formatter):
    """
    Formatter que converte logs em formato JSON.
    
    Útil para análise posterior com ferramentas como ELK, Splunk, etc.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formata o registro de log como JSON.
        
        Args:
            record: Registro de log do Python
            
        Returns:
            String JSON do log formatado
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Adiciona exceção se existir
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class MetricsCollector:
    """
    Coletor de métricas para monitoramento da aplicação.
    
    Coleta métricas como:
    - Contadores (número de requisições, erros, etc.)
    - Gauges (valores atuais como memória, CPU)
    - Histograms (distribuição de tempos, tamanhos)
    - Timers (duração de operações)
    
    Attributes:
        metrics (Dict[str, Any]): Dicionário de métricas coletadas
    """
    
    def __init__(self):
        """Inicializa o coletor de métricas."""
        self.metrics: Dict[str, Any] = {
            "counters": {},
            "gauges": {},
            "histograms": {},
        }
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Incrementa um contador.
        
        Args:
            name: Nome da métrica
            value: Valor a incrementar (padrão: 1)
            tags: Tags adicionais para categorização
        """
        if name not in self.metrics["counters"]:
            self.metrics["counters"][name] = {"value": 0, "tags": tags or {}}
        self.metrics["counters"][name]["value"] += value
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Define o valor de um gauge.
        
        Args:
            name: Nome da métrica
            value: Valor atual
            tags: Tags adicionais para categorização
        """
        self.metrics["gauges"][name] = {"value": value, "tags": tags or {}}
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Registra uma medição de tempo.
        
        Args:
            name: Nome da métrica
            duration: Duração em segundos
            tags: Tags adicionais para categorização
        """
        if name not in self.metrics["histograms"]:
            self.metrics["histograms"][name] = {"values": [], "tags": tags or {}}
        self.metrics["histograms"][name]["values"].append(duration)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Retorna todas as métricas coletadas.
        
        Returns:
            Dicionário com todas as métricas
        """
        # Calcula estatísticas para histogramas
        for name, data in self.metrics["histograms"].items():
            values = data["values"]
            if values:
                data["stats"] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                }
        
        return self.metrics
    
    def reset(self) -> None:
        """Reseta所有 métricas."""
        self.metrics = {
            "counters": {},
            "gauges": {},
            "histograms": {},
        }


# Instância global do coletor de métricas
_global_metrics = MetricsCollector()


def get_logger(name: str) -> StructuredLogger:
    """
    Obtém ou cria um logger estruturado.
    
    Args:
        name: Nome do logger (geralmente __name__ do módulo)
    
    Returns:
        Instância de StructuredLogger
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = os.getenv("LOG_DIR", "data/logs")
    return StructuredLogger(name, log_level, log_dir)


def get_metrics() -> MetricsCollector:
    """
    Obtém a instância global do coletor de métricas.
    
    Returns:
        Instância de MetricsCollector
    """
    return _global_metrics
