"""
Validadores - Utilitários de Validação
=======================================
Valida documentos brasileiros (CNPJ, CPF) e outros formatos.
"""

import re
from typing import Optional


def validar_cnpj(cnpj: str) -> bool:
    """
    Valida CNPJ verificando dígitos verificadores.
    Aceita com ou sem formatação (pontos, barras, hífens).
    """
    # Remove formatação
    cnpj_limpo = re.sub(r"[^\d]", "", cnpj)

    # CNPJ tem 14 dígitos
    if len(cnpj_limpo) != 14:
        return False

    # Rejeita sequências repetidas (ex: 11111111111111)
    if cnpj_limpo == cnpj_limpo[0] * 14:
        return False

    # Validação do primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj_limpo[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    dv1 = 0 if resto < 2 else 11 - resto

    if int(cnpj_limpo[12]) != dv1:
        return False

    # Validação do segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj_limpo[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    dv2 = 0 if resto < 2 else 11 - resto

    return int(cnpj_limpo[13]) == dv2


def validar_cpf(cpf: str) -> bool:
    """
    Valida CPF verificando dígitos verificadores.
    Aceita com ou sem formatação (pontos, hífens).
    """
    # Remove formatação
    cpf_limpo = re.sub(r"[^\d]", "", cpf)

    # CPF tem 11 dígitos
    if len(cpf_limpo) != 11:
        return False

    # Rejeita sequências repetidas (ex: 11111111111)
    if cpf_limpo == cpf_limpo[0] * 11:
        return False

    # Validação do primeiro dígito verificador
    soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    dv1 = 0 if resto == 10 else resto

    if int(cpf_limpo[9]) != dv1:
        return False

    # Validação do segundo dígito verificador
    soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    dv2 = 0 if resto == 10 else resto

    return int(cpf_limpo[10]) == dv2


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX."""
    cnpj_limpo = re.sub(r"[^\d]", "", cnpj)
    if len(cnpj_limpo) != 14:
        return cnpj
    return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"


def formatar_cpf(cpf: str) -> str:
    """Formata CPF no padrão XXX.XXX.XXX-XX."""
    cpf_limpo = re.sub(r"[^\d]", "", cpf)
    if len(cpf_limpo) != 11:
        return cpf
    return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"


def validar_email(email: str) -> bool:
    """Valida formato de email."""
    padrao = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(padrao, email))