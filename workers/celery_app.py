"""
Configuração da Instância do Celery
====================================
Broker e Backend configurados para utilizar o Redis existente no ambiente.
"""

import os

# Tenta importar Celery; se não estiver instalado em dev local, provê fallback mock
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if CELERY_AVAILABLE:
    celery_app = Celery(
        "transparencia_workers",
        broker=REDIS_URL,
        backend=REDIS_URL
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="America/Sao_Paulo",
        enable_utc=True,
    )
    
    # Configuração de Agendamentos (Celery Beat) para Monitoramento Ativo
    celery_app.conf.beat_schedule = {
        'ronda-monitoramento-diario-meia-noite': {
            'task': 'workers.celery_app.ronda_diaria_monitoramento',
            'schedule': 86400.0, # Rodar a cada 24 horas (em config real usaria crontab(minute=0, hour=0))
        },
    }
else:
    class CeleryMock:
        def task(self, *args, **kwargs):
            def decorator(func):
                def delay(*fargs, **fkwargs):
                    # Em dev sem Celery instalado, executa síncrono e retorna mock result
                    res = func(*fargs, **fkwargs)
                    return MockTaskResult(res)
                func.delay = delay
                return func
            return decorator

    class MockTaskResult:
        def __init__(self, result):
            self.id = "mock_task_id_123"
            self.result = result
            self.status = "SUCCESS"

        def get(self, timeout=None):
            return self.result

    celery_app = CeleryMock()


@celery_app.task(name="workers.celery_app.ronda_diaria_monitoramento")
def ronda_diaria_monitoramento():
    """
    Ronda Diária de Monitoramento Ativo.
    Puxa alvos cadastrados (ex: CNPJs rastreados) e consulta bases como
    Comprasnet ou CGU para verificar novas atividades desde o dia anterior.
    """
    print("[MONITORAMENTO ATIVO] Iniciando ronda diária...")
    # Aqui conectaríamos no banco para pegar os Alvos
    alvos_mock = ["12.345.678/0001-90", "00.000.000/0001-91"]
    
    alertas_enviados = 0
    for alvo in alvos_mock:
        print(f"  - Verificando novidades para o CNPJ: {alvo}")
        # Simulando uma verificação que encontrou uma nova licitação suspeita
        import random
        if random.random() > 0.7:
            # Invocar Notificações
            from core.notificacoes import Notificador
            noti = Notificador()
            noti.enviar_alerta_urgente(
                f"Nova atividade suspeita do Alvo Monitorado {alvo}",
                "Identificamos que este CNPJ, marcado em nossa lista de monitoramento, acaba de ser listado em uma nova Ata de Registro de Preços no Diário Oficial."
            )
            alertas_enviados += 1
            
    print(f"[MONITORAMENTO ATIVO] Ronda finalizada. {alertas_enviados} alertas despachados para a War Room.")
    return True
