"""
Integrações com APIs Governamentais Reais
==========================================
Integração com APIs públicas de portais governamentais brasileiros:
- PNCP (Portal Nacional de Contratações Públicas)
- Receita Federal (consulta CNPJ)
- CGU (Portal da Transparência - CEIS/CNEP)
- TCU (Tribunal de Contas da União)
- Comprasnet
- SICONFI (Finanças municipais)
"""

import os
import re
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger("ia_analisadora.integracoes_gov")

# Importação do cache de APIs governamentais
try:
    from utils.cache_manager import get_gov_api_cache
    CACHE_AVAILABLE = True
    gov_cache = get_gov_api_cache()
except ImportError:
    CACHE_AVAILABLE = False
    gov_cache = None
    logger.warning("GovAPICache não disponível. Usando requisições diretas.")


class IntegracoesGovernamentais:
    """
    Integração com APIs governamentais brasileiras.
    Todas as APIs são públicas e gratuitas (algumas exigem cadastro para token).
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.timeout = 30
        self.rate_limit_delay = 1.0  # Segundos entre requests
        self.use_cache = CACHE_AVAILABLE and gov_cache is not None

    def _fazer_request(self, url: str, params: dict = None, headers: dict = None, api_name: str = "generic", api_type: str = "default") -> Optional[Any]:
        """Faz request com rate limiting e cache governamental."""
        if self.use_cache:
            cached = gov_cache.get_api_response(
                api_name=api_name,
                endpoint=url,
                params=params,
                api_type=api_type
            )
            if cached:
                logger.debug(f"Cache hit para {api_name} em integracoes_gov")
                return cached.get('response')

        try:
            h = self.session.headers.copy()
            if headers:
                h.update(headers)

            response = self.session.get(url, params=params, headers=h, timeout=self.timeout)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()

            if "json" in content_type:
                result = response.json()
            else:
                result = response.text

            if self.use_cache:
                gov_cache.set_api_response(
                    api_name=api_name,
                    endpoint=url,
                    response=result,
                    params=params,
                    api_type=api_type
                )
            
            return result

        except requests.RequestException as e:
            logger.error(f"Erro ao acessar {url}: {e}")
            return None
        finally:
            time.sleep(self.rate_limit_delay)

    # === PNCP - Portal Nacional de Contratações Públicas ===

    def consultar_pncp_licitacoes(
        self,
        data_inicial: str = None,
        data_final: str = None,
        codigo_orgao: str = None,
        modalidade: str = None,
        pagina: int = 1,
        tamanho_pagina: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Consulta licitações no PNCP.
        API: https://pncp.gov.br/api/consulta/

        Args:
            data_inicial: Formato AAAA-MM-DD
            data_final: Formato AAAA-MM-DD
            codigo_orgao: Código do órgão (ex: 920318 - Prefeitura)
            modalidade: Tipo de licitação
            pagina: Número da página (começa em 1)
            tamanho_pagina: Itens por página (máx 500)
        """
        url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

        params = {
            "pagina": pagina,
            "tamPagina": min(tamanho_pagina, 500),
            "ordemCrescente": False,
        }

        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final
        if codigo_orgao:
            params["codigoOrgao"] = codigo_orgao
        if modalidade:
            params["modalidade"] = modalidade

        resultado = self._fazer_request(url, params=params, api_name='pncp', api_type='licitacao')

        if resultado and isinstance(resultado, dict):
            return resultado.get("data", resultado.get("items", []))
        elif resultado and isinstance(resultado, list):
            return resultado

        return []

    def consultar_pncp_contratos(
        self,
        data_inicial: str = None,
        data_final: str = None,
        pagina: int = 1,
        tamanho_pagina: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Consulta contratos no PNCP.
        """
        url = "https://pncp.gov.br/api/consulta/v1/contratos"

        params = {
            "pagina": pagina,
            "tamPagina": min(tamanho_pagina, 500),
        }

        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final

        resultado = self._fazer_request(url, params=params, api_name='pncp', api_type='licitacao')

        if resultado and isinstance(resultado, dict):
            return resultado.get("data", resultado.get("items", []))
        elif resultado and isinstance(resultado, list):
            return resultado

        return []

    def consultar_pncp_todas_paginas(
        self,
        data_inicial: str = None,
        data_final: str = None,
        max_paginas: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Consulta todas as páginas de licitações do PNCP.
        Navega automaticamente por todas as páginas até esgotar.
        """
        todas_licitacoes = []
        pagina = 1

        while pagina <= max_paginas:
            logger.info(f"PNCP: Buscando página {pagina}...")
            licitacoes = self.consultar_pncp_licitacoes(
                data_inicial=data_inicial,
                data_final=data_final,
                pagina=pagina,
                tamanho_pagina=100
            )

            if not licitacoes:
                break

            todas_licitacoes.extend(licitacoes)
            logger.info(f"PNCP: {len(licitacoes)} licitações na página {pagina}")

            if len(licitacoes) < 100:
                break  # Última página

            pagina += 1

        logger.info(f"PNCP: Total de {len(todas_licitacoes)} licitações encontradas")
        return todas_licitacoes

    # === Receita Federal - Consulta CNPJ ===

    def consultar_cnpj(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Consulta dados cadastrais de um CNPJ na Receita Federal.
        Usa API pública: https://receitaws.com.br/v1/cnpj/{cnpj}

        Retorna dados como:
        - Razão social
        - Situação cadastral (ATIVA/INAPTA/BAIXADA)
        - Capital social
        - Data de abertura
        - Endereço
        - Sócios
        - Atividades (CNAE)
        """
        cnpj_limpo = re.sub(r'\D', '', cnpj)
        if len(cnpj_limpo) != 14:
            return None

        url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"

        resultado = self._fazer_request(url, api_name="receita", api_type="cadastral")

        if resultado and isinstance(resultado, dict):
            if resultado.get("status") == "OK":
                return {
                    "cnpj": cnpj_limpo,
                    "razao_social": resultado.get("nome", ""),
                    "nome_fantasia": resultado.get("fantasia", ""),
                    "situacao_cadastral": resultado.get("situacao", ""),
                    "data_abertura": resultado.get("abertura", ""),
                    "capital_social": resultado.get("capital_social", ""),
                    "porte": resultado.get("porte", ""),
                    "natureza_juridica": resultado.get("natureza_juridica", ""),
                    "endereco": {
                        "logradouro": resultado.get("logradouro", ""),
                        "numero": resultado.get("numero", ""),
                        "complemento": resultado.get("complemento", ""),
                        "bairro": resultado.get("bairro", ""),
                        "municipio": resultado.get("municipio", ""),
                        "uf": resultado.get("uf", ""),
                        "cep": resultado.get("cep", ""),
                    },
                    "telefone": resultado.get("telefone", ""),
                    "email": resultado.get("email", ""),
                    "socios": resultado.get("qsa", []),
                    "atividades_principal": resultado.get("atividade_principal", []),
                    "atividades_secundarias": resultado.get("atividades_secundarias", []),
                }

        return None

    def consultar_cnpj_lote(self, cnpjs: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Consulta múltiplos CNPJs em lote.
        Retorna dict {cnpj: dados}.
        """
        resultados = {}
        for cnpj in cnpjs:
            dados = self.consultar_cnpj(cnpj)
            if dados:
                resultados[cnpj] = dados
            time.sleep(self.rate_limit_delay)  # Rate limit da API
        return resultados

    # === CGU - Portal da Transparência (CEIS/CNEP) ===

    def consultar_ceis(self, cnpj: str = None, cpf: str = None) -> List[Dict[str, Any]]:
        """
        Consulta CEIS (Cadastro de Empresas Inidôneas e Suspensas) na CGU.
        API: https://api.portaldatransparencia.gov.br/api-de-dados/ceis

        Requer chave de API (CGU_API_KEY no .env).
        """
        api_key = os.getenv("CGU_API_KEY")

        if not api_key:
            logger.warning("CGU_API_KEY não configurada. Usando fallback mock.")
            return self._mock_ceis(cnpj)

        url = "https://api.portaldatransparencia.gov.br/api-de-dados/ceis"
        headers = {"chave-api-dados": api_key}

        params = {"pagina": 1}
        if cnpj:
            params["cnpjSancionado"] = re.sub(r'\D', '', cnpj)
        if cpf:
            params["cpfSancionado"] = re.sub(r'\D', '', cpf)

        resultado = self._fazer_request(url, params=params, headers=headers, api_name="cgu", api_type="sancao")

        if resultado and isinstance(resultado, list):
            return resultado

        return []

    def consultar_cnep(self, cnpj: str = None, cpf: str = None) -> List[Dict[str, Any]]:
        """
        Consulta CNEP (Cadastro Nacional de Condenações por Atos de Improbidade).
        """
        api_key = os.getenv("CGU_API_KEY")

        if not api_key:
            return []

        url = "https://api.portaldatransparencia.gov.br/api-de-dados/cnep"
        headers = {"chave-api-dados": api_key}

        params = {"pagina": 1}
        if cnpj:
            params["cnpjSancionado"] = re.sub(r'\D', '', cnpj)
        if cpf:
            params["cpfSancionado"] = re.sub(r'\D', '', cpf)

        resultado = self._fazer_request(url, params=params, headers=headers, api_name="cgu", api_type="sancao")

        if resultado and isinstance(resultado, list):
            return resultado

        return []

    def _mock_ceis(self, cnpj: str) -> List[Dict[str, Any]]:
        """Fallback mock quando não há API key."""
        cnpj_limpo = re.sub(r'\D', '', str(cnpj))
        if cnpj_limpo.endswith("66") or cnpj_limpo.endswith("99"):
            return [{
                "sancionado": True,
                "motivo": "Fraude em licitação anterior (Mock - configure CGU_API_KEY para dados reais)",
                "data_inicio": "2023-01-15",
                "data_fim": "2028-01-15"
            }]
        return []

    # === TCU - Tribunal de Contas da União ===

    def consultar_tcu_acordaos(
        self,
        palavra_chave: str = None,
        ano: int = None,
        pagina: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Consulta acórdãos do TCU.
        API: https://contas.tcu.gov.br/api/
        """
        url = "https://contas.tcu.gov.br/api/consulta/acordos"

        params = {
            "pagina": pagina,
            "tamanhoPagina": 50,
        }

        if palavra_chave:
            params["palavraChave"] = palavra_chave
        if ano:
            params["ano"] = ano

        resultado = self._fazer_request(url, params=params, api_name="cgu", api_type="sancao")

        if resultado and isinstance(resultado, dict):
            return resultado.get("items", resultado.get("data", []))
        elif resultado and isinstance(resultado, list):
            return resultado

        return []

    # === Comprasnet ===

    def consultar_comprasnet(
        self,
        texto_busca: str = None,
        data_inicial: str = None,
        data_final: str = None,
        pagina: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Consulta compras governamentais no Comprasnet.
        """
        url = "https://www.gov.br/compras/pt-br/compras-sisrp/api"

        params = {
            "pagina": pagina,
        }

        if texto_busca:
            params["texto"] = texto_busca
        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final

        resultado = self._fazer_request(url, params=params, api_name="cgu", api_type="sancao")

        if resultado and isinstance(resultado, dict):
            return resultado.get("items", resultado.get("data", []))
        elif resultado and isinstance(resultado, list):
            return resultado

        return []

    # === SICONFI - Finanças Municipais ===

    def consultar_siconfi(
        self,
        codigo_ibge: str = None,
        ano: int = None,
        tipo: str = "receita"
    ) -> List[Dict[str, Any]]:
        """
        Consulta dados financeiros de municípios no SICONFI.
        API: https://apidatalake.tesouro.gov.br/ords/siconfi/
        """
        url = f"https://apidatalake.tesouro.gov.br/ords/siconfi/api/v1/{tipo}"

        params = {
            "ano_exercicio": ano or datetime.now().year,
        }

        if codigo_ibge:
            params["id_municipio"] = codigo_ibge

        resultado = self._fazer_request(url, params=params, api_name="cgu", api_type="sancao")

        if resultado and isinstance(resultado, dict):
            return resultado.get("items", resultado.get("data", []))
        elif resultado and isinstance(resultado, list):
            return resultado

        return []

    # === DOU - Diário Oficial da União ===

    def consultar_dou(
        self,
        texto_busca: str = None,
        data_inicial: str = None,
        data_final: str = None,
        secao: str = None
    ) -> List[Dict[str, Any]]:
        """
        Consulta Diário Oficial da União.
        API: https://queridodiario.ok.org.br/api/
        """
        url = "https://queridodiario.ok.org.br/api/gazettes"

        params = {}

        if texto_busca:
            params["keywords"] = texto_busca
        if data_inicial:
            params["since"] = data_inicial
        if data_final:
            params["until"] = data_final
        if secao:
            params["section"] = secao

        resultado = self._fazer_request(url, params=params, api_name="cgu", api_type="sancao")

        if resultado and isinstance(resultado, dict):
            return resultado.get("gazettes", [])
        elif resultado and isinstance(resultado, list):
            return resultado

        return []

    # === Painel de Preços (Gov.br) ===

    def consultar_painel_precos(self, termo: str = None) -> List[Dict[str, Any]]:
        """
        Consulta o Painel de Preços do Governo Federal.
        API: https://paineis.preco.governo.digital/
        """
        url = "https://paineis.preco.governo.digital/api/v1/pesquisa"

        params = {}
        if termo:
            params["termo"] = termo

        resultado = self._fazer_request(url, params=params, api_name="painel", api_type="financeiro")

        if resultado and isinstance(resultado, dict):
            return resultado.get("items", resultado.get("data", []))
        elif resultado and isinstance(resultado, list):
            return resultado

        return []

    # === Utilitários ===

    def enriquecer_empresa(self, cnpj: str) -> Dict[str, Any]:
        """
        Enriquece dados de uma empresa consultando múltiplas fontes:
        - Receita Federal (dados cadastrais)
        - CEIS (sanções)
        - CNEP (condenações)
        """
        resultado = {
            "cnpj": cnpj,
            "dados_cadastrais": None,
            "sancoes_ceis": [],
            "sancoes_cnep": [],
            "status": "desconhecido"
        }

        # 1. Receita Federal
        dados_cadastrais = self.consultar_cnpj(cnpj)
        if dados_cadastrais:
            resultado["dados_cadastrais"] = dados_cadastrais
            resultado["status"] = dados_cadastrais.get("situacao_cadastral", "desconhecido")

        # 2. CEIS
        ceis = self.consultar_ceis(cnpj=cnpj)
        if ceis:
            resultado["sancoes_ceis"] = ceis

        # 3. CNEP
        cnep = self.consultar_cnep(cnpj=cnpj)
        if cnep:
            resultado["sancoes_cnep"] = cnep

        # Determina se é inidônea
        if resultado["sancoes_ceis"] or resultado["sancoes_cnep"]:
            resultado["inidonea"] = True
        else:
            resultado["inidonea"] = False

        return resultado

    def buscar_codigo_ibge_municipio(self, nome_municipio: str, uf: str = None) -> Optional[str]:
        """
        Busca o código IBGE de um município pelo nome.
        """
        url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

        resultado = self._fazer_request(url, api_name="ibge", api_type="default")

        if resultado and isinstance(resultado, list):
            for municipio in resultado:
                nome = municipio.get("nome", "").lower()
                sigla_uf = municipio.get("microrregiao", {}).get("mesorregiao", {}).get("UF", {}).get("sigla", "")

                if nome == nome_municipio.lower():
                    if uf is None or sigla_uf.upper() == uf.upper():
                        return str(municipio.get("id", ""))

        return None