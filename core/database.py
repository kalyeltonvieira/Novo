"""
Gerenciador de Banco de Dados Relacional (SQLAlchemy)
=====================================================
Suporta PostgreSQL em produção e SQLite em modo de desenvolvimento local.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# String de conexão (PostgreSQL por padrão ou SQLite fallback)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./transparencia.db"
)

# SQLite exige args específicos de conexão para multithreading
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependência para obter uma sessão do banco de dados em endpoints ou tarefas."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria todas as tabelas no banco de dados se não existirem."""
    Base.metadata.create_all(bind=engine)
