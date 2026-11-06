"""
Plataforma de Auditoria Colaborativa (Crowd Audit Community)
============================================================
Permite que cidadãos e auditores colaborem na validação e anotação de investigações.
"""

from typing import Dict, Any, List


class CrowdAuditManager:
    """Gerencia notas, votos e colaborações comunitárias em investigações."""

    def __init__(self):
        self.anotacoes: List[Dict[str, Any]] = []

    def adicionar_anotacao(self, alerta_id: str, usuario: str, comentario: str, voto: str = "concordo") -> Dict[str, Any]:
        """Registra a contribuição de um auditor cidadão."""
        anotacao = {
            "alerta_id": alerta_id,
            "usuario": usuario,
            "comentario": comentario,
            "voto": voto
        }
        self.anotacoes.append(anotacao)
        return {"status": "sucesso", "anotacao": anotacao}

    def obter_anotacoes_alerta(self, alerta_id: str) -> List[Dict[str, Any]]:
        """Retorna todas as contribuições salvas para determinado alerta."""
        return [a for a in self.anotacoes if a["alerta_id"] == alerta_id]
