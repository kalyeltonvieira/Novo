"""
Coletor de Dados - Camada de Entrada
=====================================
Responsável por receber documentos de múltiplas fontes:
- Arquivos locais (PDF, imagens, planilhas, etc.)
- URLs e web scraping
- Portais da transparência
- APIs públicas
- Diários oficiais
- Dados do TCU, estadual, municipal
"""

import os
import json
import csv
import glob
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .entidades import Documento, TipoDocumento

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.entrada_dados")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.entrada")
    metrics = None
    MONITORING_AVAILABLE = False


class ColetorDados:
    """
    Coletor de dados de múltiplas fontes públicas.
    
    Este módulo é responsável por coletar documentos de diversas fontes:
    - Arquivos locais (PDF, imagens, planilhas, etc.)
    - URLs e web scraping
    - Portais da transparência
    - APIs públicas governamentais
    - Diários oficiais
    - Dados do TCU, estadual e municipal
    
    Attributes:
        config (Dict[str, Any]): Configurações do coletor
        historico (List[Dict]): Histórico de coletas realizadas
        session (requests.Session): Sessão HTTP para requisições
    
    Example:
        >>> coletor = ColetorDados()
        >>> arquivos = coletor.coletar_pasta("documentos")
        >>> dados_url = coletor.coletar_url("https://exemplo.com")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.historico = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def coletar_arquivo(self, caminho: str) -> str:
        """
        Adiciona um arquivo local para processamento.
        
        Args:
            caminho: Caminho do arquivo a ser coletado
        
        Returns:
            Caminho do arquivo validado
        
        Raises:
            FileNotFoundError: Se o arquivo não existir
        """
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        self.historico.append({
            "tipo": "arquivo",
            "origem": caminho,
            "timestamp": datetime.now(),
        })
        return caminho

    def coletar_pasta(self, pasta: str, extensoes: Optional[List[str]] = None) -> List[str]:
        """
        Coleta todos os arquivos de uma pasta recursivamente.
        
        Args:
            pasta: Caminho da pasta a ser varrida
            extensoes: Lista de extensões (ex: ["*.pdf", "*.png"])
                      Se None, usa padrão: PDF, PNG, JPG, HTML, TXT, CSV, XLSX
        
        Returns:
            Lista de caminhos de arquivos encontrados
        """
        if extensoes is None:
            extensoes = ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.html", "*.txt", "*.csv", "*.xlsx"]

        arquivos = []
        for ext in extensoes:
            padrao = os.path.join(pasta, "**", ext)
            arquivos.extend(glob.glob(padrao, recursive=True))

        for caminho in arquivos:
            self.historico.append({
                "tipo": "arquivo",
                "origem": caminho,
                "timestamp": datetime.now(),
            })

        return arquivos

    def coletar_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Coleta conteúdo de uma URL via HTTP GET.
        
        Args:
            url: URL a ser coletada
        
        Returns:
            Dicionário com conteúdo e metadados, ou None se falhar
        
        Returns dict:
            - url: URL original
            - conteudo: Conteúdo da resposta
            - status_code: Código HTTP
            - headers: Cabeçalhos da resposta
        """
        try:
            response = self.session.get(url, timeout=30, verify=False)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()

            resultado = {
                "url": url,
                "tipo": "url",
                "conteudo": response.text,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": content_type,
            }

            self.historico.append({
                "tipo": "url",
                "origem": url,
                "timestamp": datetime.now(),
                "status": response.status_code,
            })

            return resultado

        except requests.RequestException as e:
            print(f"[ERRO] Falha ao acessar URL {url}: {e}")
            return None

    def coletar_api(self, url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """Coleta dados de uma API pública."""
        try:
            h = self.session.headers.copy()
            if headers:
                h.update(headers)

            response = self.session.get(url, params=params, headers=h, timeout=30, verify=False)
            response.raise_for_status()

            resultado = response.json()

            self.historico.append({
                "tipo": "api",
                "origem": url,
                "timestamp": datetime.now(),
                "status": response.status_code,
            })

            return resultado

        except requests.RequestException as e:
            print(f"[ERRO] Falha ao acessar API {url}: {e}")
            return None

    def coletar_portal_transparencia(self, url_base: str, parametros: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Coleta dados de portais da transparência.
        Tenta identificar se é JSON, tabela HTML ou API.
        """
        resultados = []
        dados = self.coletar_url(url_base)

        if not dados:
            return resultados

        try:
            # Tenta parsear como JSON
            data = json.loads(dados["conteudo"])
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
        except (json.JSONDecodeError, ValueError):
            pass

        # Tenta parsear como HTML table
        soup = BeautifulSoup(dados["conteudo"], "html.parser")
        tabelas = soup.find_all("table")
        for tabela in tabelas:
            linhas = []
            cabecalhos = [th.get_text(strip=True) for th in tabela.find_all("th")]

            for tr in tabela.find_all("tr"):
                celulas = [td.get_text(strip=True) for td in tr.find_all("td")]
                if celulas and cabecalhos:
                    linha = dict(zip(cabecalhos, celulas))
                    linhas.append(linha)
                elif celulas:
                    linhas.append(celulas)

            if linhas:
                resultados.extend(linhas)

        return resultados

    def coletar_diario_oficial(self, url: str, data_inicio: str = None, data_fim: str = None) -> List[str]:
        """
        Coleta edições de diários oficiais.
        Retorna lista de URLs de PDFs encontrados.
        """
        pdfs_encontrados = []

        try:
            response = self.session.get(url, timeout=30, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Encontra links para PDF
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if ".pdf" in href.lower():
                    if href.startswith("http"):
                        pdf_url = href
                    else:
                        from urllib.parse import urljoin
                        pdf_url = urljoin(url, href)
                    pdfs_encontrados.append(pdf_url)

        except Exception as e:
            print(f"[ERRO] Diário Oficial: {e}")

        return pdfs_encontrados

    def coletar_tcu(self, tipo: str = "licitacoes", ano: int = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Coleta dados do Tribunal de Contas da União (TCU).
        Utiliza APIs públicas do TCU.
        """
        if ano is None:
            ano = datetime.now().year

        urls_api = {
            "licitacoes": f"https://api.tcu.gov.br/licitacoes/{ano}",
            "contratos": f"https://api.tcu.gov.br/contratos/{ano}",
            "empresas": f"https://api.tcu.gov.br/empresas-punidas",
            "irregularidades": f"https://api.tcu.gov.br/contas-irregulares",
        }

        url = urls_api.get(tipo)
        if not url:
            print(f"[ERRO] Tipo TCU inválido: {tipo}")
            return []

        dados = self.coletar_api(url, params=kwargs)
        if isinstance(dados, list):
            return dados
        elif isinstance(dados, dict):
            return [dados]
        return []

    def coletar_dados_estaduais(self, estado: str, tipo: str = "licitacoes", **kwargs) -> List[Dict[str, Any]]:
        """
        Coleta dados de portais estaduais de transparência.
        estado: sigla (SP, RJ, MG, etc.)
        """
        # Mapa básico de portais estaduais
        portais = {
            "SP": "https://www.transparencia.sp.gov.br",
            "RJ": "https://www.transparencia.rj.gov.br",
            "MG": "https://www.transparencia.mg.gov.br",
            "BA": "https://www.transparencia.ba.gov.br",
            "PR": "https://www.transparencia.pr.gov.br",
            "RS": "https://www.transparencia.rs.gov.br",
            "PE": "https://www.transparencia.pe.gov.br",
            "CE": "https://www.transparencia.ce.gov.br",
            "PA": "https://www.transparencia.pa.gov.br",
            "AM": "https://www.transparencia.am.gov.br",
        }

        url_base = portais.get(estado.upper())
        if not url_base:
            print(f"[AVISO] Portal de {estado} não mapeado. Usando busca genérica.")
            url_base = f"https://www.transparencia.{estado.lower()}.gov.br"

        return self.coletar_portal_transparencia(url_base, kwargs)

    def coletar_texto(self, texto: str, fonte: str = "texto_direto") -> Dict[str, Any]:
        """Adiciona texto diretamente."""
        resultado = {
            "tipo": "texto",
            "origem": fonte,
            "conteudo": texto,
            "timestamp": datetime.now(),
        }

        self.historico.append({
            "tipo": "texto",
            "origem": fonte,
            "timestamp": datetime.now(),
        })

        return resultado

    def importar_planilha(self, caminho: str) -> List[Dict[str, Any]]:
        """Importa dados de planilha Excel ou CSV."""
        dados = []

        try:
            if caminho.endswith((".xlsx", ".xls")):
                df = pd.read_excel(caminho, dtype=str)
            elif caminho.endswith(".csv"):
                encoding = self._detectar_encoding(caminho)
                df = pd.read_csv(caminho, encoding=encoding, dtype=str)
            else:
                print(f"[ERRO] Formato não suportado: {caminho}")
                return []

            dados = df.fillna("").to_dict("records")

            self.historico.append({
                "tipo": "planilha",
                "origem": caminho,
                "linhas": len(dados),
                "timestamp": datetime.now(),
            })

        except Exception as e:
            print(f"[ERRO] Falha ao importar planilha: {e}")

        return dados

    def buscar_google(self, query: str, num_resultados: int = 10) -> List[Dict[str, str]]:
        """
        Busca documentos no Google (web scraping).
        Retorna lista de {titulo, link, snippet}
        """
        resultados = []
        try:
            params = {
                "q": query,
                "num": num_resultados,
                "hl": "pt-BR",
            }
            response = self.session.get(
                "https://www.google.com/search",
                params=params,
                timeout=30,
                verify=False,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for div in soup.find_all("div", class_="g"):
                link = div.find("a")
                titulo = div.find("h3")
                snippet = div.find("div", class_="VwiC3b")

                if link and titulo:
                    resultados.append({
                        "titulo": titulo.get_text(strip=True),
                        "link": link.get("href", ""),
                        "snippet": snippet.get_text(strip=True) if snippet else "",
                    })

        except Exception as e:
            print(f"[ERRO] Busca Google: {e}")

        return resultados

    def get_historico(self) -> List[Dict[str, Any]]:
        """Retorna histórico de coletas."""
        return self.historico

    def _detectar_encoding(self, caminho: str) -> str:
        """Detecta encoding do arquivo."""
        import chardet
        with open(caminho, "rb") as f:
            resultado = chardet.detect(f.read(10000))
        return resultado.get("encoding", "utf-8")