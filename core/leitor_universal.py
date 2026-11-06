"""
Leitor Universal - Camada de Extração de Informações
=====================================================
Transforma qualquer documento (PDF, imagem, HTML, etc.) em dados estruturados.
Utiliza OCR, NLP, Embeddings e Sumarização.
"""

import os
import re
import hashlib
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pdfplumber
import requests
from bs4 import BeautifulSoup

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

from .entidades import (
    Documento, EntidadeExtraida, TipoDocumento, TipoEntidade
)

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.leitor_universal")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.leitor")
    metrics = None
    MONITORING_AVAILABLE = False

# Importação opcional do gerenciador de IA
try:
    from utils.ai_providers import get_ai_manager
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("Módulo de IA não disponível. Usando apenas spaCy local.")


class LeitorUniversal:
    """
    Pipeline de processamento de documentos universais.
    
    Este módulo é responsável por transformar qualquer tipo de documento
    (PDF, imagem, HTML, planilha, XML, JSON, texto) em dados estruturados
    através de OCR, NLP, embeddings e sumarização.
    
    Attributes:
        config (Dict[str, Any]): Configurações do processador
        nlp_models (Dict[str, Any]): Modelos NLP carregados (spaCy, etc.)
        embedding_model (Any): Modelo de embeddings (sentence-transformers)
        use_ai (bool): Se True, utiliza LLM APIs para processamento avançado
        ai_manager (Any): Gerenciador de provedores de IA
    
    Example:
        >>> leitor = LeitorUniversal(config={"use_ai": True})
        >>> documento = leitor.processar_documento("contrato.pdf")
        >>> print(f"Entidades extraídas: {len(documento.entidades)}")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        if MONITORING_AVAILABLE:
            metrics.increment("leitor_inicializado")
        self.config = config or {}
        self.nlp_models = {}
        self.embedding_model = None
        self.use_ai = self.config.get("use_ai", False)  # Se True, usa LLM APIs
        self.ai_manager = None
        if AI_AVAILABLE and self.use_ai:
            self.ai_manager = get_ai_manager()
        self._inicializar_modelos()

    def _inicializar_modelos(self) -> None:
        """
        Inicializa os modelos NLP conforme disponibilidade do sistema.
        
        Tenta carregar:
        - spaCy: Modelo pt_core_news_lg ou pt_core_news_md
        - sentence-transformers: Modelo paraphrase-multilingual-MiniLM-L12-v2
        
        Registra warnings se os modelos não estiverem disponíveis.
        """
        try:
            import spacy
            try:
                self.nlp_models["spacy"] = spacy.load("pt_core_news_lg")
            except OSError:
                try:
                    self.nlp_models["spacy"] = spacy.load("pt_core_news_md")
                except OSError:
                    logger.warning("Modelo spaCy pt não encontrado. Use: python -m spacy download pt_core_news_lg")
                    self.nlp_models["spacy"] = None
        except ImportError:
            logger.warning("spaCy não instalado. Use: pip install spacy")
            self.nlp_models["spacy"] = None

        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        except ImportError:
            logger.warning("sentence-transformers não instalado. Embeddings desabilitados.")
            self.embedding_model = None

    def processar_documento(self, caminho: str, **kwargs) -> Optional[Documento]:
        """
        Processa um documento e extrai entidades estruturadas.
        
        Args:
            caminho: Caminho do arquivo a ser processado
            **kwargs: Argumentos adicionais específicos por tipo de documento
        
        Returns:
            Documento processado com entidades extraídas, ou None se falhar
        
        Raises:
            FileNotFoundError: Se o arquivo não existir
            ValueError: Se o tipo de documento não for suportado
        """
        tipo = self._detectar_tipo(caminho)
        doc_id = str(uuid.uuid4())

        if tipo == TipoDocumento.PDF:
            conteudo, metadados, confianca = self._processar_pdf(caminho)
            if confianca < 0.5:
                texto_ocr, confianca_ocr = self._ocr_pdf(caminho)
                if confianca_ocr > confianca:
                    conteudo = texto_ocr
                    confianca = confianca_ocr
                    metadados["ocr_aplicado"] = True
        elif tipo == TipoDocumento.IMAGEM:
            conteudo, metadados, confianca = self._processar_imagem(caminho)
        elif tipo == TipoDocumento.HTML:
            conteudo, metadados, confianca = self._processar_html(caminho)
        elif tipo == TipoDocumento.PLANILHA:
            conteudo, metadados, confianca = self._processar_planilha(caminho)
        elif tipo == TipoDocumento.XML:
            conteudo, metadados, confianca = self._processar_xml(caminho)
        elif tipo == TipoDocumento.JSON:
            conteudo, metadados, confianca = self._processar_json(caminho)
        elif tipo == TipoDocumento.TEXTO:
            conteudo, metadados, confianca = self._processar_texto(caminho)
        else:
            conteudo, metadados, confianca = self._processar_texto(caminho)

        entidades = self._extrair_entidades(conteudo, doc_id)
        resumo = self._sumarizar(conteudo)
        embeddings = self._gerar_embeddings(conteudo) if self.embedding_model else None

        hash_doc = hashlib.sha256(conteudo.encode()).hexdigest()

        return Documento(
            id=doc_id,
            fonte=caminho,
            tipo=tipo,
            conteudo_original=conteudo,
            conteudo_processado=self._limpar_texto(conteudo),
            metadados=metadados,
            entidades=entidades,
            resumo=resumo,
            embeddings=embeddings,
            confianca_ocr=confianca,
            hash_documento=hash_doc,
            data_documento=metadados.get("data_documento"),
            orgao_origem=metadados.get("orgao_origem"),
        )

    def _detectar_tipo(self, caminho: str) -> TipoDocumento:
        ext = os.path.splitext(caminho)[1].lower()
        mapa = {
            ".pdf": TipoDocumento.PDF,
            ".png": TipoDocumento.IMAGEM,
            ".jpg": TipoDocumento.IMAGEM,
            ".jpeg": TipoDocumento.IMAGEM,
            ".tiff": TipoDocumento.IMAGEM,
            ".bmp": TipoDocumento.IMAGEM,
            ".html": TipoDocumento.HTML,
            ".htm": TipoDocumento.HTML,
            ".xlsx": TipoDocumento.PLANILHA,
            ".xls": TipoDocumento.PLANILHA,
            ".csv": TipoDocumento.PLANILHA,
            ".txt": TipoDocumento.TEXTO,
            ".xml": TipoDocumento.XML,
            ".json": TipoDocumento.JSON,
            ".docx": TipoDocumento.TEXTO,  # Será tratado como texto
            ".doc": TipoDocumento.TEXTO,
        }
        return mapa.get(ext, TipoDocumento.TEXTO)

    def _extrair_entidades(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        entidades = []

        # Se IA está habilitada e disponível, usa LLM para extração avançada
        if self.use_ai and self.ai_manager:
            entidades_ai = self._extrair_entidades_ai(texto, doc_id)
            if entidades_ai:
                entidades.extend(entidades_ai)
                logger.info(f"Extraídas {len(entidades_ai)} entidades usando IA")

        # Sempre usa spaCy local como complemento
        if self.nlp_models.get("spacy"):
            nlp = self.nlp_models["spacy"]
            try:
                doc = nlp(texto[:100000])
                for ent in doc.ents:
                    tipo_map = {
                        "PER": TipoEntidade.PESSOA,
                        "ORG": TipoEntidade.EMPRESA,
                        "LOC": TipoEntidade.LOCAL,
                        "MONEY": TipoEntidade.VALOR,
                        "DATE": TipoEntidade.DATA,
                        "MISC": TipoEntidade.OBJETO,
                    }
                    tipo = tipo_map.get(ent.label_, TipoEntidade.OBJETO)
                    entidades.append(EntidadeExtraida(
                        id=str(uuid.uuid4()),
                        tipo=tipo,
                        valor=ent.text,
                        normalizado=self._normalizar_texto(ent.text),
                        contexto=texto[max(0, ent.start_char - 50):ent.end_char + 50],
                        confianca=ent._.get("confidence", 0.8) if hasattr(ent, "_") else 0.8,
                        posicao_inicio=ent.start_char,
                        posicao_fim=ent.end_char,
                        documento_id=doc_id,
                    ))
            except Exception as e:
                logger.warning(f"spaCy NER falhou: {e}")

        # Extraições específicas com regex (sempre executadas)
        entidades.extend(self._extrair_cnpj(texto, doc_id))
        entidades.extend(self._extrair_cpf(texto, doc_id))
        entidades.extend(self._extrair_valores(texto, doc_id))
        entidades.extend(self._extrair_emails(texto, doc_id))
        entidades.extend(self._extrair_telefones(texto, doc_id))
        entidades.extend(self._extrair_datas(texto, doc_id))
        entidades.extend(self._extrair_cargos(texto, doc_id))
        entidades.extend(self._extrair_licitacoes(texto, doc_id))
        entidades.extend(self._extrair_contratos(texto, doc_id))
        entidades.extend(self._extrair_enderecos(texto, doc_id))
        entidades.extend(self._extrair_orgaos_publicos(texto, doc_id))

        entidades = self._deduplicar_entidades(entidades)
        return entidades

    def _extrair_entidades_ai(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        """
        Extrai entidades usando LLM (IA) quando disponível.
        Retorna lista de entidades extraídas pelo modelo de IA.
        """
        if not self.ai_manager:
            return []
        
        try:
            # Limita texto para não exceder limites da API
            texto_limitado = texto[:50000]
            
            resultado = self.ai_manager.analyze_text(
                texto=texto_limitado,
                task="extract_entities",
                temperature=0.3,  # Baixa temperatura para mais precisão
                max_tokens=2000,
            )
            
            if not resultado:
                return []
            
            # Parseia resultado JSON da IA
            import json
            try:
                # Tenta extrair JSON do resultado
                if "```json" in resultado:
                    json_str = resultado.split("```json")[1].split("```")[0].strip()
                elif "```" in resultado:
                    json_str = resultado.split("```")[1].split("```")[0].strip()
                else:
                    json_str = resultado
                
                dados = json.loads(json_str)
                
                entidades = []
                if isinstance(dados, list):
                    for item in dados:
                        tipo_str = item.get("tipo", "objeto")
                        tipo_map = {
                            "pessoa": TipoEntidade.PESSOA,
                            "empresa": TipoEntidade.EMPRESA,
                            "valor": TipoEntidade.VALOR,
                            "data": TipoEntidade.DATA,
                            "cnpj": TipoEntidade.CNPJ,
                            "cpf": TipoEntidade.CPF,
                            "cargo": TipoEntidade.CARGO,
                            "orgao_publico": TipoEntidade.ORGAO_PUBLICO,
                            "local": TipoEntidade.LOCAL,
                            "endereco": TipoEntidade.ENDERECO,
                            "contrato": TipoEntidade.CONTRATO,
                            "licitacao": TipoEntidade.LICITACAO,
                        }
                        tipo = tipo_map.get(tipo_str.lower(), TipoEntidade.OBJETO)
                        
                        entidades.append(EntidadeExtraida(
                            id=str(uuid.uuid4()),
                            tipo=tipo,
                            valor=item.get("valor", ""),
                            normalizado=self._normalizar_texto(item.get("valor", "")),
                            contexto=item.get("contexto", "")[:200],
                            confianca=0.9,  # Alta confiança para IA
                            documento_id=doc_id,
                            metadados={"source": "ai_llm"},
                        ))
                
                logger.info(f"IA extraiu {len(entidades)} entidades")
                return entidades
                
            except json.JSONDecodeError:
                logger.warning("IA não retornou JSON válido, usando apenas spaCy")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao extrair entidades com IA: {e}")
            return []

    # --- Processamento por formato ---

    def _processar_pdf(self, caminho: str) -> Tuple[str, Dict[str, Any], float]:
        texto = ""
        metadados = {}
        try:
            with pdfplumber.open(caminho) as pdf:
                metadados["paginas"] = len(pdf.pages)
                metadados["titulo"] = pdf.metadata.get("Title", "")
                metadados["autor"] = pdf.metadata.get("Author", "")
                for pagina in pdf.pages:
                    page_text = pagina.extract_text() or ""
                    texto += page_text + "\n"
            confianca = 0.8 if len(texto.strip()) > 50 else 0.3
            return texto, metadados, confianca
        except Exception as e:
            logger.error(f"Falha ao processar PDF {caminho}: {e}")
            return "", metadados, 0.0

    def _ocr_pdf(self, caminho: str) -> Tuple[str, float]:
        try:
            imagens = convert_from_path(caminho, dpi=300)
            texto_completo = ""
            for img in imagens:
                texto = pytesseract.image_to_string(img, lang="por")
                texto_completo += texto + "\n"
            confianca = 0.7 if len(texto_completo.strip()) > 50 else 0.2
            return texto_completo, confianca
        except Exception as e:
            logger.error(f"OCR PDF falhou: {e}")
            return "", 0.0

    def _processar_imagem(self, caminho: str) -> Tuple[str, Dict[str, Any], float]:
        try:
            imagem = Image.open(caminho)
            texto = pytesseract.image_to_string(imagem, lang="por")
            confianca = 0.7 if len(texto.strip()) > 20 else 0.2
            return texto, {"formato": imagem.format, "tamanho": imagem.size}, confianca
        except Exception as e:
            logger.error(f"OCR imagem falhou: {e}")
            return "", {}, 0.0

    def _processar_html(self, caminho: str) -> Tuple[str, Dict[str, Any], float]:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            texto = soup.get_text(separator="\n", strip=True)
            titulo = soup.title.string if soup.title else ""
            return texto, {"titulo": titulo}, 1.0
        except Exception as e:
            logger.error(f"Falha ao processar HTML: {e}")
            return "", {}, 0.0

    def _processar_texto(self, caminho: str) -> Tuple[str, Dict[str, Any], float]:
        ext = os.path.splitext(caminho)[1].lower()

        # DOCX
        if ext in (".docx", ".doc") and DocxDocument is not None:
            try:
                doc = DocxDocument(caminho)
                texto = "\n".join(p.text for p in doc.paragraphs)
                metadados = {
                    "paragrafos": len(doc.paragraphs),
                    "tabelas": len(doc.tables),
                }
                return texto, metadados, 0.9
            except Exception as e:
                logger.error(f"Falha ao processar DOCX {caminho}: {e}")
                return "", {}, 0.0

        # TXT
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return f.read(), {}, 1.0
        except UnicodeDecodeError:
            try:
                with open(caminho, "r", encoding="latin-1") as f:
                    return f.read(), {}, 0.9
            except Exception as e:
                logger.error(f"Falha ao ler texto: {e}")
                return "", {}, 0.0

    def _processar_planilha(self, caminho: str) -> Tuple[str, Dict[str, Any], float]:
        try:
            import pandas as pd
            if caminho.lower().endswith((".xlsx", ".xls")):
                df = pd.read_excel(caminho, dtype=str)
            else:
                df = pd.read_csv(caminho, dtype=str, encoding="utf-8", sep=None, engine="python")
            df = df.fillna("")
            conteudo = df.to_string(index=False)
            metadados = {
                "linhas": len(df),
                "colunas": list(df.columns),
                "tipo_planilha": os.path.splitext(caminho)[1].lower().lstrip("."),
            }
            return conteudo, metadados, 0.9
        except Exception as e:
            logger.error(f"Falha ao processar planilha {caminho}: {e}")
            return "", {}, 0.0

    def _processar_xml(self, caminho: str) -> Tuple[str, Dict[str, Any], float]:
        try:
            from xml.etree import ElementTree as ET
            tree = ET.parse(caminho)
            root = tree.getroot()
            textos = [elem.text for elem in root.iter() if elem.text and elem.text.strip()]
            conteudo = "\n".join(textos)
            return conteudo, {"root_tag": root.tag}, 0.9
        except Exception as e:
            logger.error(f"Falha ao processar XML {caminho}: {e}")
            return "", {}, 0.0

    def _processar_json(self, caminho: str) -> Tuple[str, Dict[str, Any], float]:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            conteudo = json.dumps(dados, ensure_ascii=False, indent=2)
            return conteudo, {"tipo_json": type(dados).__name__}, 0.9
        except Exception as e:
            logger.error(f"Falha ao processar JSON {caminho}: {e}")
            return "", {}, 0.0

    # --- Extratores por regex ---

    def _extrair_cnpj(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        from utils.validadores import validar_cnpj
        padrao = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}"
        entidades = []
        for match in re.finditer(padrao, texto):
            normalizado = re.sub(r"[^\d]", "", match.group())
            valido = validar_cnpj(normalizado)
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.CNPJ,
                valor=match.group(),
                normalizado=normalizado,
                contexto=texto[max(0, match.start() - 50):match.end() + 50],
                confianca=0.95 if valido else 0.3,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
                metadados={"valido": valido},
            ))
        return entidades

    def _extrair_cpf(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        from utils.validadores import validar_cpf
        padrao = r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11}"
        entidades = []
        for match in re.finditer(padrao, texto):
            normalizado = re.sub(r"[^\d]", "", match.group())
            if len(normalizado) != 11:
                continue
            valido = validar_cpf(normalizado)
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.CPF,
                valor=match.group(),
                normalizado=normalizado,
                contexto=texto[max(0, match.start() - 50):match.end() + 50],
                confianca=0.95 if valido else 0.3,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
                metadados={"valido": valido},
            ))
        return entidades

    def _extrair_valores(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = r"(?:R\$|RS|r\$)\s*[\d.,]+\s*(?:mil|milhão|milhões|bi|trião)?|\b[\d]{1,3}(?:\.\d{3})*(?:,\d{2})\b"
        entidades = []
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.VALOR,
                valor=match.group(),
                normalizado=self._normalizar_valor(match.group()),
                contexto=texto[max(0, match.start() - 50):match.end() + 50],
                confianca=0.85,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
            ))
        return entidades

    def _extrair_emails(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        entidades = []
        for match in re.finditer(padrao, texto):
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.EMAIL,
                valor=match.group(),
                normalizado=match.group().lower(),
                confianca=0.9,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
            ))
        return entidades

    def _extrair_telefones(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = r"(?:\+?\d{2})?\s*\(?\d{2}\)?\s*\d{4,5}[- ]?\d{4}"
        entidades = []
        for match in re.finditer(padrao, texto):
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.TELEFONE,
                valor=match.group(),
                normalizado=re.sub(r"[^\d]", "", match.group()),
                confianca=0.85,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
            ))
        return entidades

    def _extrair_datas(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = r"\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}"
        entidades = []
        for match in re.finditer(padrao, texto):
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.DATA,
                valor=match.group(),
                normalizado=match.group(),
                confianca=0.9,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
            ))
        return entidades

    def _extrair_cargos(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        cargos_lista = [
            "secretário", "secretária", "diretor", "diretora", "presidente",
            "coordenador", "coordenadora", "gerente", "supervisor", "supervisora",
            "chefe", "ministro", "ministra", "prefeito", "prefeita",
            "governador", "governadora", "vereador", "vereadora",
            "deputado", "deputada", "senador", "senadora",
            "procurador", "procuradora", "advogado", "advogada",
        ]
        entidades = []
        for cargo in cargos_lista:
            padrao = rf"\b{re.escape(cargo)}\b"
            for match in re.finditer(padrao, texto, re.IGNORECASE):
                entidades.append(EntidadeExtraida(
                    id=str(uuid.uuid4()),
                    tipo=TipoEntidade.CARGO,
                    valor=match.group(),
                    normalizado=self._normalizar_texto(match.group()),
                    contexto=texto[max(0, match.start() - 50):match.end() + 50],
                    confianca=0.8,
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    documento_id=doc_id,
                ))
        return entidades

    def _extrair_licitacoes(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = r"(?:pregão|licitação|concorrência|tomada\s+de\s+preços|convite)\s*(?:n[ºo°\.]?\s*)?(\d+/\d{4}|\d+)"
        entidades = []
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.LICITACAO,
                valor=match.group(),
                normalizado=self._normalizar_texto(match.group()),
                contexto=texto[max(0, match.start() - 50):match.end() + 50],
                confianca=0.85,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
            ))
        return entidades

    def _extrair_contratos(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = r"contrato\s*(?:n[ºo°\.]?\s*)?(\d+/\d{4}|\d+)"
        entidades = []
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            entidades.append(EntidadeExtraida(
                id=str(uuid.uuid4()),
                tipo=TipoEntidade.CONTRATO,
                valor=match.group(),
                normalizado=self._normalizar_texto(match.group()),
                contexto=texto[max(0, match.start() - 50):match.end() + 50],
                confianca=0.85,
                posicao_inicio=match.start(),
                posicao_fim=match.end(),
                documento_id=doc_id,
            ))
        return entidades

    def _extrair_enderecos(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = r"(?:rua|avenida|av\.|praça|alameda|travessa|rodovia)\s+[^,\n]{3,50},?\s*\d{0,5}"
        entidades = []
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            valor = match.group().strip()
            if len(valor) > 10:
                entidades.append(EntidadeExtraida(
                    id=str(uuid.uuid4()),
                    tipo=TipoEntidade.ENDERECO,
                    valor=valor,
                    normalizado=self._normalizar_texto(valor),
                    contexto=texto[max(0, match.start() - 50):match.end() + 50],
                    confianca=0.7,
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    documento_id=doc_id,
                ))
        return entidades

    def _extrair_orgaos_publicos(self, texto: str, doc_id: str) -> List[EntidadeExtraida]:
        padrao = (
            r"(?:prefeitura(?:\s+municipal)?(?:\s+de\s+[^,\n]{2,30})?|"
            r"secretaria(?:\s+municipal|\s+estadual)?(?:\s+de\s+[^,\n]{2,30})?|"
            r"ministério(?:\s+de\s+[^,\n]{2,30})?|"
            r"câmara(?:\s+municipal)?(?:\s+de\s+[^,\n]{2,30})?|"
            r"governo(?:\s+do\s+estado)?(?:\s+de\s+[^,\n]{2,30})?|"
            r"tribunal(?:\s+de\s+[^,\n]{2,30})?|"
            r"universidade(?:\s+federal|\s+estadual)?(?:\s+de\s+[^,\n]{2,30})?)"
        )
        entidades = []
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            valor = match.group().strip()
            if len(valor) > 8:
                entidades.append(EntidadeExtraida(
                    id=str(uuid.uuid4()),
                    tipo=TipoEntidade.ORGAO_PUBLICO,
                    valor=valor,
                    normalizado=self._normalizar_texto(valor),
                    contexto=texto[max(0, match.start() - 50):match.end() + 50],
                    confianca=0.8,
                    posicao_inicio=match.start(),
                    posicao_fim=match.end(),
                    documento_id=doc_id,
                ))
        return entidades

    def _normalizar_valor(self, valor: str) -> str:
        valor = re.sub(r'[Rr$§\s]', '', valor)
        if ',' in valor and '.' in valor:
            if valor.index(',') > valor.index('.'):
                valor = valor.replace('.', '').replace(',', '.')
            else:
                valor = valor.replace(',', '')
        elif ',' in valor:
            valor = valor.replace(',', '.')
        return valor

    def _normalizar_texto(self, texto: str) -> str:
        texto = texto.upper().strip()
        texto = texto.translate(str.maketrans(
            "ÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇÑ",
            "AAAAAEEEEIIIIOOOOOUUUUCN"
        ))
        texto = re.sub(r'[^A-Z0-9\s]', '', texto)
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

    def _limpar_texto(self, texto: str) -> str:
        texto = re.sub(r'\s+', ' ', texto)
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        texto = re.sub(r'[^\S\n]+', ' ', texto)
        return texto.strip()

    def _deduplicar_entidades(self, entidades: List[EntidadeExtraida]) -> List[EntidadeExtraida]:
        if not entidades:
            return []
        grupos = {}
        for ent in entidades:
            chave = (ent.tipo.value, ent.normalizado[:100])
            if chave not in grupos:
                grupos[chave] = ent
            else:
                if ent.confianca > grupos[chave].confianca:
                    grupos[chave] = ent
        return list(grupos.values())

    def processar_url(self, url: str, **kwargs) -> Optional[Documento]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            doc_id = str(uuid.uuid4())

            if "pdf" in content_type:
                caminho_temp = os.path.join("data", "temp_web.pdf")
                os.makedirs("data", exist_ok=True)
                with open(caminho_temp, "wb") as f:
                    f.write(response.content)
                return self.processar_documento(caminho_temp)

            soup = BeautifulSoup(response.text, "html.parser")
            conteudo = soup.get_text(separator="\n", strip=True)
            titulo = soup.title.string if soup.title else url

            entidades = self._extrair_entidades(conteudo, doc_id)
            resumo = self._sumarizar(conteudo)
            embeddings = self._gerar_embeddings(conteudo) if self.embedding_model else None

            return Documento(
                id=doc_id, fonte=url, tipo=TipoDocumento.HTML,
                conteudo_original=conteudo, conteudo_processado=self._limpar_texto(conteudo),
                metadados={"titulo": titulo, "url": url},
                entidades=entidades, resumo=resumo, embeddings=embeddings,
                confianca_ocr=1.0, url_origem=url,
            )
        except Exception as e:
            logger.error(f"Falha ao processar URL {url}: {e}")
            return None

    def processar_texto_direto(self, texto: str, fonte: str = "texto_direto", **kwargs) -> Documento:
        doc_id = str(uuid.uuid4())
        entidades = self._extrair_entidades(texto, doc_id)
        resumo = self._sumarizar(texto)
        embeddings = self._gerar_embeddings(texto) if self.embedding_model else None

        return Documento(
            id=doc_id, fonte=fonte, tipo=TipoDocumento.TEXTO,
            conteudo_original=texto, conteudo_processado=self._limpar_texto(texto),
            metadados={}, entidades=entidades, resumo=resumo, embeddings=embeddings,
            confianca_ocr=1.0,
        )

    def processar_lote(self, caminhos: List[str], max_workers: int = 4) -> List[Documento]:
        documentos = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.processar_documento, p): p for p in caminhos}
            for future in as_completed(futures):
                try:
                    doc = future.result()
                    if doc:
                        documentos.append(doc)
                except Exception as e:
                    logger.error(f"Falha ao processar {futures[future]}: {e}")
        return documentos

    def _sumarizar(self, texto: str, max_sentencas: int = 5) -> str:
        if not texto.strip():
            return ""

        if self.nlp_models.get("spacy"):
            try:
                nlp = self.nlp_models["spacy"]
                doc = nlp(texto[:50000])
                sentencas = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 20]

                if len(sentencas) <= max_sentencas:
                    return " ".join(sentencas)

                from collections import Counter
                palavras = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct]
                freq = Counter(palavras)

                scores = {}
                for i, sentenca in enumerate(sentencas):
                    sent_doc = nlp(sentenca)
                    score = sum(freq.get(token.lemma_.lower(), 0) for token in sent_doc
                               if not token.is_stop and not token.is_punct)
                    score *= (1.5 if i < 2 else 1.0)
                    scores[i] = score

                top_idx = sorted(scores, key=scores.get, reverse=True)[:max_sentencas]
                top_idx.sort()
                return " ".join(sentencas[i] for i in top_idx)
            except Exception as e:
                logger.warning(f"Sumarização falhou: {e}")

        return " ".join(texto.split(".")[:max_sentencas]) + "."

    def _gerar_embeddings(self, texto: str) -> List[float]:
        if not self.embedding_model or not texto.strip():
            return []
        try:
            embeddings = self.embedding_model.encode(texto[:2000])
            return embeddings.tolist()
        except Exception as e:
            logger.warning(f"Embeddings falhou: {e}")
            return []