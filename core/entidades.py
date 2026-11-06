"""
Entidades e Modelos de Dados do Sistema
=========================================
Define todas as classes de dados usadas no pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TipoDocumento(Enum):
    PDF = "pdf"
    IMAGEM = "imagem"
    HTML = "html"
    PLANILHA = "planilha"
    TEXTO = "texto"
    API = "api"
    XML = "xml"
    JSON = "json"


class TipoEntidade(Enum):
    PESSOA = "pessoa"
    EMPRESA = "empresa"
    ORGAO_PUBLICO = "orgao_publico"
    CARGO = "cargo"
    LOCAL = "local"
    CONTRATO = "contrato"
    LICITACAO = "licitacao"
    PROCESSO = "processo"
    VALOR = "valor"
    DATA = "data"
    CNPJ = "cnpj"
    CPF = "cpf"
    ENDERECO = "endereco"
    TELEFONE = "telefone"
    EMAIL = "email"
    OBJETO = "objeto"


class TipoAnomalia(Enum):
    SUPERFATURAMENTO = "superfaturamento"
    NEPOTISMO = "nepotismo"
    CARTEL = "cartel"
    FRACIONAMENTO = "fracionamento"
    EMPRESA_FANTASMA = "empresa_fantasma"
    CONFLITO_INTERESSE = "conflito_interesse"
    PAGAMENTO_SEM_LICITACAO = "pagamento_sem_licitacao"
    PRAZO_CURTO = "prazo_curto"
    EMPRESA_RECEM_CRIADA = "empresa_recem_criada"
    SOCIO_REPETIDO = "socio_repetido"
    VALOR_ACIMA_MEDIA = "valor_acima_media"
    SUSPEITA_FRAUDE = "suspeita_fraude"
    ENDERECO_REPETIDO = "endereco_repetido"


@dataclass
class Documento:
    """Representa um documento processado pelo sistema."""
    id: str
    fonte: str
    tipo: TipoDocumento
    conteudo_original: str
    conteudo_processado: str
    metadados: Dict[str, Any] = field(default_factory=dict)
    data_processamento: datetime = field(default_factory=datetime.now)
    data_documento: Optional[datetime] = None
    orgao_origem: Optional[str] = None
    url_origem: Optional[str] = None
    hash_documento: Optional[str] = None
    entidades: List["EntidadeExtraida"] = field(default_factory=list)
    resumo: Optional[str] = None
    embeddings: Optional[List[float]] = None
    confianca_ocr: float = 0.0


@dataclass
class EntidadeExtraida:
    """Uma entidade extraída de um documento."""
    id: str
    tipo: TipoEntidade
    valor: str
    normalizado: str
    contexto: str = ""
    confianca: float = 1.0
    posicao_inicio: int = 0
    posicao_fim: int = 0
    metadados: Dict[str, Any] = field(default_factory=dict)
    documento_id: Optional[str] = None
    variacoes: List[str] = field(default_factory=list)


@dataclass
class Pessoa:
    """Representa uma pessoa física identificada."""
    id: str
    nome: str
    nome_normalizado: str
    cpf: Optional[str] = None
    cargos: List[str] = field(default_factory=list)
    orgaos_relacionados: List[str] = field(default_factory=list)
    empresas_relacionadas: List[str] = field(default_factory=list)
    parentes: List[str] = field(default_factory=list)
    contratos: List[str] = field(default_factory=list)
    processos: List[str] = field(default_factory=list)
    metadados: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Empresa:
    """Representa uma empresa identificada."""
    id: str
    nome: str
    nome_normalizado: str
    cnpj: Optional[str] = None
    data_abertura: Optional[datetime] = None
    socios: List[Dict[str, Any]] = field(default_factory=list)
    endereco: Optional[str] = None
    capital_social: Optional[float] = None
    funcionarios: Optional[int] = None
    contratos: List[str] = field(default_factory=list)
    licitacoes_participadas: List[str] = field(default_factory=list)
    orgaos_contratantes: List[str] = field(default_factory=list)
    metadados: Dict[str, Any] = field(default_factory=dict)
    alertas: List[str] = field(default_factory=list)
    score_suspeita: float = 0.0


@dataclass
class Contrato:
    """Representa um contrato público."""
    id: str
    numero: Optional[str] = None
    orgao_contratante: str = ""
    contratada: str = ""
    cnpj_contratada: Optional[str] = None
    valor: float = 0.0
    valor_total: float = 0.0
    objeto: str = ""
    data_assinatura: Optional[datetime] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    prazo_dias: Optional[int] = None
    aditivos: List[Dict[str, Any]] = field(default_factory=list)
    modalidade_licitacao: Optional[str] = None
    processo_licitatorio: Optional[str] = None
    metadados: Dict[str, Any] = field(default_factory=dict)
    alertas: List[str] = field(default_factory=list)


@dataclass
class Relacionamento:
    """Representa uma relação entre duas entidades."""
    id: str
    tipo: str  # "socio", "contrato", "parente", "licitacao", "pagamento"
    entidade_origem: str  # id
    entidade_destino: str  # id
    tipo_origem: str
    tipo_destino: str
    forca: float = 1.0
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    valor: Optional[float] = None
    detalhes: str = ""
    documento_id: Optional[str] = None
    metadados: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alerta:
    """Representa um alerta gerado pelo detector de anomalias."""
    id: str
    tipo: TipoAnomalia
    titulo: str
    descricao: str
    severidade: str  # "baixa", "media", "alta", "critica"
    score_confianca: float = 0.0
    entidades_envolvidas: List[str] = field(default_factory=list)
    documentos_relacionados: List[str] = field(default_factory=list)
    data_deteccao: datetime = field(default_factory=datetime.now)
    valor_envolvido: Optional[float] = None
    status: str = "novo"  # "novo", "investigando", "confirmado", "falso_positivo"
    evidencias: List[Dict[str, Any]] = field(default_factory=list)
    metadados: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relatorio:
    """Relatório técnico gerado automaticamente."""
    id: str
    titulo: str
    tipo: str  # "denuncia", "analise", "ranking", "resumo"
    data_geracao: datetime = field(default_factory=datetime.now)
    dados: Dict[str, Any] = field(default_factory=dict)
    graficos: List[str] = field(default_factory=list)
    tabelas: List[Dict[str, Any]] = field(default_factory=list)
    alertas_incluidos: List[str] = field(default_factory=list)
    entidades_incluidas: List[str] = field(default_factory=list)
    pdf_gerado: Optional[str] = None
    metadados: Dict[str, Any] = field(default_factory=dict)