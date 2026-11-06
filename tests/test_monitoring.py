"""
Testes unitários para utils/monitoring.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from utils.monitoring import StructuredLogger, MetricsCollector, get_logger, get_metrics


class TestStructuredLogger:
    """Testes do logger estruturado."""

    def test_criar_logger(self):
        """Testa criação de logger."""
        logger = StructuredLogger("test_logger")
        assert logger.name == "test_logger"
        assert logger.context == {}

    def test_set_context(self):
        """Testa definição de contexto."""
        logger = StructuredLogger("test_logger")
        logger.set_context(user_id="123", request_id="abc")
        assert logger.context == {"user_id": "123", "request_id": "abc"}

    def test_clear_context(self):
        """Testa limpeza de contexto."""
        logger = StructuredLogger("test_logger")
        logger.set_context(user_id="123")
        logger.clear_context()
        assert logger.context == {}

    def test_log_info(self):
        """Testa log de nível INFO."""
        logger = StructuredLogger("test_logger")
        # Não deve lançar erro
        logger.info("Mensagem de teste")

    def test_log_error(self):
        """Testa log de nível ERROR."""
        logger = StructuredLogger("test_logger")
        logger.error("Mensagem de erro", error_code=500)

    def test_log_com_contexto(self):
        """Testa log com contexto."""
        logger = StructuredLogger("test_logger")
        logger.set_context(user_id="123")
        logger.info("Mensagem com contexto")
        assert logger.context == {"user_id": "123"}

    def test_config_log_level(self):
        """Testa configuração de nível de log."""
        logger = StructuredLogger("test_logger", log_level="DEBUG")
        assert logger.logger.level == 10  # DEBUG level


class TestMetricsCollector:
    """Testes do coletor de métricas."""

    def test_criar_coletor(self):
        """Testa criação de coletor."""
        metrics = MetricsCollector()
        assert metrics.metrics == {"counters": {}, "gauges": {}, "histograms": {}}

    def test_increment_counter(self):
        """Testa incremento de contador."""
        metrics = MetricsCollector()
        metrics.increment("test_counter")
        assert metrics.metrics["counters"]["test_counter"]["value"] == 1

    def test_increment_counter_custom_value(self):
        """Testa incremento com valor customizado."""
        metrics = MetricsCollector()
        metrics.increment("test_counter", value=5)
        assert metrics.metrics["counters"]["test_counter"]["value"] == 5

    def test_increment_counter_multiple(self):
        """Testa múltiplos incrementos."""
        metrics = MetricsCollector()
        metrics.increment("test_counter")
        metrics.increment("test_counter")
        assert metrics.metrics["counters"]["test_counter"]["value"] == 2

    def test_set_gauge(self):
        """Testa definição de gauge."""
        metrics = MetricsCollector()
        metrics.set_gauge("test_gauge", 42.5)
        assert metrics.metrics["gauges"]["test_gauge"]["value"] == 42.5

    def test_set_gauge_override(self):
        """Testa sobrescrita de gauge."""
        metrics = MetricsCollector()
        metrics.set_gauge("test_gauge", 10.0)
        metrics.set_gauge("test_gauge", 20.0)
        assert metrics.metrics["gauges"]["test_gauge"]["value"] == 20.0

    def test_record_timing(self):
        """Testa registro de timing."""
        metrics = MetricsCollector()
        metrics.record_timing("test_timer", 1.5)
        assert len(metrics.metrics["histograms"]["test_timer"]["values"]) == 1
        assert metrics.metrics["histograms"]["test_timer"]["values"][0] == 1.5

    def test_record_timing_multiple(self):
        """Testa múltiplos registros de timing."""
        metrics = MetricsCollector()
        metrics.record_timing("test_timer", 1.0)
        metrics.record_timing("test_timer", 2.0)
        metrics.record_timing("test_timer", 3.0)
        assert len(metrics.metrics["histograms"]["test_timer"]["values"]) == 3

    def test_get_metrics(self):
        """Testa obtenção de métricas."""
        metrics = MetricsCollector()
        metrics.increment("test_counter")
        metrics.set_gauge("test_gauge", 42.0)
        result = metrics.get_metrics()
        assert "counters" in result
        assert "gauges" in result
        assert "histograms" in result

    def test_get_metrics_with_stats(self):
        """Testa estatísticas de histogramas."""
        metrics = MetricsCollector()
        metrics.record_timing("test_timer", 1.0)
        metrics.record_timing("test_timer", 2.0)
        metrics.record_timing("test_timer", 3.0)
        result = metrics.get_metrics()
        assert "stats" in result["histograms"]["test_timer"]
        assert result["histograms"]["test_timer"]["stats"]["count"] == 3
        assert result["histograms"]["test_timer"]["stats"]["min"] == 1.0
        assert result["histograms"]["test_timer"]["stats"]["max"] == 3.0

    def test_reset_metrics(self):
        """Testa reset de métricas."""
        metrics = MetricsCollector()
        metrics.increment("test_counter")
        metrics.reset()
        assert metrics.metrics == {"counters": {}, "gauges": {}, "histograms": {}}


class TestGlobalFunctions:
    """Testes de funções globais."""

    def test_get_logger(self):
        """Testa obtenção de logger global."""
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"

    def test_get_metrics(self):
        """Testa obtenção de métricas globais."""
        metrics = get_metrics()
        assert metrics is not None
        assert isinstance(metrics, MetricsCollector)

    def test_metrics_singleton(self):
        """Testa que métricas são singleton."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        assert metrics1 is metrics2


class TestJsonFormatter:
    """Testes do formatador JSON."""

    def test_json_formatter_output(self):
        """Testa que formatador produz JSON válido."""
        from utils.monitoring import JsonFormatter
        import logging
        import json
        
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        result = formatter.format(record)
        # Deve ser JSON válido
        parsed = json.loads(result)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
