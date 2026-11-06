"""
Serviço de Notificações e Webhooks Ativos
==========================================
Dispara alertas em tempo real quando anomalias de alta gravidade forem detectadas.
"""

import os
import json
import urllib.request
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any, Optional

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.notificacoes")
    metrics = get_metrics()
except ImportError:
    import logging
    logger = logging.getLogger("core.notificacoes")
    metrics = None


class ServicoNotificacoes:
    """Gerencia envio de alertas via Webhooks (Slack/Discord/Custom) e E-mail."""

    def __init__(self):
        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.email_destinatario = os.getenv("NOTIFICACAO_EMAIL_DESTINO")

    def disparar_alerta_webhook(self, alerta_data: Dict[str, Any]) -> bool:
        """Dispara dados do alerta para o webhook configurado."""
        if not self.webhook_url:
            logger.info("Nenhum WEBHOOK_URL configurado. Pulando disparo de webhook.")
            return False

        try:
            payload = {
                "text": f"🚨 *ANOMALIA DETECTADA [{alerta_data.get('severidade', 'ALTA').upper()}]*",
                "attachments": [
                    {
                        "title": alerta_data.get("titulo", "Alerta de Transparência"),
                        "text": alerta_data.get("descricao", ""),
                        "color": "#ff0000" if alerta_data.get("severidade") == "critica" else "#ff9900",
                        "fields": [
                            {"title": "Valor Envolvido", "value": f"R$ {alerta_data.get('valor_envolvido', 0):,.2f}", "short": True},
                            {"title": "Tipo", "value": alerta_data.get("tipo", "desconhecido"), "short": True}
                        ]
                    }
                ]
            }

            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in (200, 204):
                    logger.info("Webhook disparado com sucesso.")
                    if metrics:
                        metrics.increment("webhooks_disparados_sucesso")
                    return True
        except Exception as e:
            logger.error(f"Erro ao disparar webhook: {str(e)}")
            if metrics:
                metrics.increment("webhooks_disparados_falha")
        return False

    def disparar_email_alerta(self, assunto: str, mensagem: str) -> bool:
        """Dispara e-mail de notificação de emergência via SMTP."""
        if not (self.smtp_server and self.smtp_user and self.email_destinatario):
            logger.info("Configuração SMTP incompleta. Pulando envio de e-mail.")
            return False

        try:
            msg = MIMEText(mensagem, "html")
            msg["Subject"] = f"[Cérebro Transparência] {assunto}"
            msg["From"] = self.smtp_user
            msg["To"] = self.email_destinatario

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                if self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"E-mail enviado com sucesso para {self.email_destinatario}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de alerta: {str(e)}")
            return False
