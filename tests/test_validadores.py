"""
Testes unitários para utils/validadores.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from utils.validadores import validar_cnpj, validar_cpf, formatar_cnpj, formatar_cpf, validar_email


class TestValidarCNPJ:
    """Testes de validação de CNPJ."""

    def test_cnpj_valido_com_formatacao(self):
        # CNPJ válido conhecido: 11.222.333/0001-81
        assert validar_cnpj("11.222.333/0001-81") is True

    def test_cnpj_valido_sem_formatacao(self):
        assert validar_cnpj("11222333000181") is True

    def test_cnpj_invalido_digitos_errados(self):
        assert validar_cnpj("11.222.333/0001-82") is False

    def test_cnpj_tamanho_errado(self):
        assert validar_cnpj("12345678") is False

    def test_cnpj_todos_iguais(self):
        assert validar_cnpj("11111111111111") is False

    def test_cnpj_vazio(self):
        assert validar_cnpj("") is False


class TestValidarCPF:
    """Testes de validação de CPF."""

    def test_cpf_valido_com_formatacao(self):
        # CPF válido conhecido: 529.982.247-25
        assert validar_cpf("529.982.247-25") is True

    def test_cpf_valido_sem_formatacao(self):
        assert validar_cpf("52998224725") is True

    def test_cpf_invalido_digitos_errados(self):
        assert validar_cpf("529.982.247-26") is False

    def test_cpf_tamanho_errado(self):
        assert validar_cpf("123456") is False

    def test_cpf_todos_iguais(self):
        assert validar_cpf("11111111111") is False

    def test_cpf_vazio(self):
        assert validar_cpf("") is False


class TestFormatacao:
    """Testes de formatação."""

    def test_formatar_cnpj(self):
        assert formatar_cnpj("11222333000181") == "11.222.333/0001-81"

    def test_formatar_cnpj_ja_formatado(self):
        assert formatar_cnpj("11.222.333/0001-81") == "11.222.333/0001-81"

    def test_formatar_cnpj_tamanho_errado(self):
        assert formatar_cnpj("123") == "123"

    def test_formatar_cpf(self):
        assert formatar_cpf("52998224725") == "529.982.247-25"

    def test_formatar_cpf_ja_formatado(self):
        assert formatar_cpf("529.982.247-25") == "529.982.247-25"


class TestValidarEmail:
    """Testes de validação de email."""

    def test_email_valido(self):
        assert validar_email("teste@exemplo.com") is True

    def test_email_com_subdominio(self):
        assert validar_email("user@mail.example.org") is True

    def test_email_sem_arroba(self):
        assert validar_email("testeexemplo.com") is False

    def test_email_sem_dominio(self):
        assert validar_email("teste@") is False

    def test_email_vazio(self):
        assert validar_email("") is False