"""
Testes do Banco de Dados Relacional e ORM
==========================================
"""

import pytest
import uuid
from core.database import Base, engine, SessionLocal, init_db
from core.models_db import PessoaDB, EmpresaDB, AlertaDB, DocumentoDB


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    yield


def test_criacao_e_consulta_pessoa():
    db = SessionLocal()
    try:
        p_id = f"p_test_{uuid.uuid4().hex[:8]}"
        pessoa = PessoaDB(
            id=p_id,
            nome="Carlos Oliveira",
            nome_normalizado="CARLOS OLIVEIRA",
            cpf="11122233344",
            cargos=["Vereador"]
        )
        db.add(pessoa)
        db.commit()

        consultado = db.query(PessoaDB).filter(PessoaDB.id == p_id).first()
        assert consultado is not None
        assert consultado.nome == "Carlos Oliveira"
        assert consultado.cargos == ["Vereador"]
    finally:
        db.close()


def test_criacao_e_consulta_empresa():
    db = SessionLocal()
    try:
        emp_id = f"emp_test_{uuid.uuid4().hex[:8]}"
        empresa = EmpresaDB(
            id=emp_id,
            nome="Construtora X LTDA",
            nome_normalizado="CONSTRUTORA X",
            cnpj="12345678000199",
            capital_social=500000.0
        )
        db.add(empresa)
        db.commit()

        consultado = db.query(EmpresaDB).filter(EmpresaDB.id == emp_id).first()
        assert consultado is not None
        assert consultado.capital_social == 500000.0
    finally:
        db.close()


def test_criacao_alerta_db():
    db = SessionLocal()
    try:
        alt_id = f"alt_test_{uuid.uuid4().hex[:8]}"
        alerta = AlertaDB(
            id=alt_id,
            tipo="nepotismo",
            titulo="Suspeita de Nepotismo",
            descricao="Contrato com parente de agente público",
            severidade="critica",
            valor_envolvido=150000.0
        )
        db.add(alerta)
        db.commit()

        consultado = db.query(AlertaDB).filter(AlertaDB.id == alt_id).first()
        assert consultado is not None
        assert consultado.severidade == "critica"
    finally:
        db.close()
