"""
Modelos do Banco de Dados Relacional (SQLAlchemy ORM)
=====================================================
Define as tabelas relacionais do sistema para persistência contínua.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey
from datetime import datetime
from core.database import Base


class PessoaDB(Base):
    __tablename__ = "pessoas"

    id = Column(String, primary_key=True, index=True)
    nome = Column(String, nullable=False, index=True)
    nome_normalizado = Column(String, index=True)
    cpf = Column(String, nullable=True, index=True)
    cargos = Column(JSON, default=list)
    parentes = Column(JSON, default=list)
    empresas_relacionadas = Column(JSON, default=list)
    criado_em = Column(DateTime, default=datetime.utcnow)


class EmpresaDB(Base):
    __tablename__ = "empresas"

    id = Column(String, primary_key=True, index=True)
    nome = Column(String, nullable=False, index=True)
    nome_normalizado = Column(String, index=True)
    cnpj = Column(String, nullable=True, index=True)
    capital_social = Column(Float, default=0.0)
    endereco = Column(Text, nullable=True)
    socios = Column(JSON, default=list)
    contratos = Column(JSON, default=list)
    criado_em = Column(DateTime, default=datetime.utcnow)


class AlertaDB(Base):
    __tablename__ = "alertas"

    id = Column(String, primary_key=True, index=True)
    tipo = Column(String, nullable=False, index=True)
    titulo = Column(String, nullable=False)
    descricao = Column(Text, nullable=False)
    severidade = Column(String, default="media", index=True)
    score_confianca = Column(Float, default=0.5)
    valor_envolvido = Column(Float, default=0.0)
    status = Column(String, default="novo", index=True)
    entidades_relacionadas = Column(JSON, default=list)
    criado_em = Column(DateTime, default=datetime.utcnow)


class DocumentoDB(Base):
    __tablename__ = "documentos"

    id = Column(String, primary_key=True, index=True)
    fonte = Column(String, nullable=False)
    tipo = Column(String, default="TEXTO")
    conteudo_original = Column(Text, nullable=True)
    conteudo_processado = Column(Text, nullable=True)
    metadados = Column(JSON, default=dict)
    criado_em = Column(DateTime, default=datetime.utcnow)


class ChatSessionDB(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True)
    titulo = Column(String, default="Nova Investigação")
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessageDB(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), index=True, nullable=False)
    role = Column(String, nullable=False) # "user", "ia"
    content = Column(Text, nullable=False)
    thoughts = Column(JSON, default=list)
    subagents = Column(JSON, default=list)
    criado_em = Column(DateTime, default=datetime.utcnow)
