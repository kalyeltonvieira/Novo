"""
Rastreio Offshore e Detector de Laranjas
========================================
Identifica vínculos de sócios com paraísos fiscais e suspeitas de laranjas de baixa renda.
"""

from typing import Dict, Any, List

PARAÍSOS_FISCAIS_CONHECIDOS = [
    "panama", "british virgin islands", "bvi", "delaware", "cayman islands",
    "bahamas", "luxembourg", "seychelles", "monaco", "andorra"
]


class OffshoreChecker:
    """Verificador de conexões com paraísos fiscais e laranjas em licitações."""

    def verificar_socio_offshore(self, socio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica se o sócio ou empresa possui residência/registro em paraíso fiscal."""
        pais = str(socio_data.get("pais_residencia", "")).lower()
        endereco = str(socio_data.get("endereco", "")).lower()
        
        is_offshore = any(p in pais or p in endereco for p in PARAÍSOS_FISCAIS_CONHECIDOS)

        # Checagem de suspeita de laranja (renda baixa + contrato milionário)
        renda_estimada = socio_data.get("renda_estimada", 100000.0)
        contrato_valor = socio_data.get("valor_contrato_empresa", 0.0)
        
        suspeita_laranja = False
        if renda_estimada < 3000.0 and contrato_valor > 500000.0:
            suspeita_laranja = True

        return {
            "socio_id": socio_data.get("id"),
            "nome": socio_data.get("nome"),
            "is_offshore": is_offshore,
            "suspeita_laranja": suspeita_laranja,
            "alerta": "ALERTA: Sócio residente em paraíso fiscal ou com perfil de laranja" if (is_offshore or suspeita_laranja) else "Regular"
        }
