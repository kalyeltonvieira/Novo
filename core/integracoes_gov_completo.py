"""
Integrações COMPLETAS com APIs Governamentais Brasileiras
===========================================================
Integração com todas as APIs públicas governamentais disponíveis para
investigação de transparência e detecção de fraudes.

Categorias:
1. Transparência e Contratações (PNCP, CGU, Comprasnet, SIASG)
2. Dados Cadastrais (Receita Federal, Correios, IBGE)
3. Legislativo (Câmara, Senado)
4. Eleições (TSE)
5. Financeiro (BACEN, SICONFI, BNDES)
6. Reguladoras (ANATEL, ANP, ANEEL, ANTT, ANS, ANA)
7. Judicial (CNJ, STF, JusBrasil)
8. Social (DATASUS, CNES, INEP, IBAMA)
"""

import os
import re
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger("ia_analisadora.integracoes_completo")

# Importação do cache de APIs governamentais
try:
    from utils.cache_manager import get_gov_api_cache
    CACHE_AVAILABLE = True
    gov_cache = get_gov_api_cache()
except ImportError:
    CACHE_AVAILABLE = False
    gov_cache = None
    logger.warning("GovAPICache não disponível. Usando requisições diretas.")


class IntegracoesGovCompleto:
    """
    Integração completa com todas as APIs governamentais brasileiras.
    Organizada por categoria para facilitar uso.
    
    Usa cache distribuído (Redis) quando disponível para reduzir chamadas às APIs.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.timeout = 30
        self.rate_limit = 1.0
        self.use_cache = CACHE_AVAILABLE and gov_cache is not None

    def _request(self, url: str, params: dict = None, headers: dict = None, api_name: str = "generic", api_type: str = "default") -> Optional[Any]:
        """
        Faz request com rate limiting e cache.
        
        Args:
            url: URL da requisição
            params: Parâmetros da query
            headers: Headers adicionais
            api_name: Nome da API para cache (ex: 'pncp', 'cgu')
            api_type: Tipo de API para definir TTL (cadastral, licitacao, etc.)
        """
        # Tenta obter do cache primeiro
        if self.use_cache:
            cache_key = f"{api_name}:{url}:{str(params)}"
            cached = gov_cache.get_api_response(
                api_name=api_name,
                endpoint=url,
                params=params,
                api_type=api_type
            )
            if cached:
                logger.debug(f"Cache hit para {api_name}")
                return cached.get('response')
        
        # Faz requisição se não estiver em cache
        try:
            h = self.session.headers.copy()
            if headers:
                h.update(headers)
            resp = self.session.get(url, params=params, headers=h, timeout=self.timeout)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "").lower()
            if "json" in ct:
                result = resp.json()
            else:
                result = resp.text
            
            # Armazena no cache
            if self.use_cache:
                gov_cache.set_api_response(
                    api_name=api_name,
                    endpoint=url,
                    response=result,
                    params=params,
                    api_type=api_type
                )
            
            return result
        except Exception as e:
            logger.error(f"Erro {url}: {e}")
            return None
        finally:
            time.sleep(self.rate_limit)

    # ================================================================
    # 1. TRANSPARÊNCIA E CONTRATAÇÕES
    # ================================================================

    # --- PNCP ---
    def pncp_licitacoes(self, data_ini=None, data_fim=None, orgao=None, pagina=1):
        """PNCP - Portal Nacional de Contratações Públicas."""
        url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
        params = {"pagina": pagina, "tamPagina": 100}
        if data_ini: params["dataInicial"] = data_ini
        if data_fim: params["dataFinal"] = data_fim
        if orgao: params["codigoOrgao"] = orgao
        r = self._request(url, params, api_name="pncp", api_type="licitacao")
        return r.get("data", r) if isinstance(r, dict) else r or []

    def pncp_contratos(self, data_ini=None, data_fim=None, pagina=1):
        """PNCP - Contratos."""
        url = "https://pncp.gov.br/api/consulta/v1/contratos"
        params = {"pagina": pagina, "tamPagina": 100}
        if data_ini: params["dataInicial"] = data_ini
        if data_fim: params["dataFinal"] = data_fim
        r = self._request(url, params, api_name="pncp", api_type="licitacao")
        return r.get("data", r) if isinstance(r, dict) else r or []

    def pncp_orgaos(self):
        """PNCP - Lista todos os órgãos cadastrados."""
        url = "https://pncp.gov.br/api/consulta/v1/orgaos"
        r = self._request(url, api_name="pncp", api_type="cadastral")
        return r if isinstance(r, list) else r.get("data", []) if isinstance(r, dict) else []

    # --- CGU Portal da Transparência ---
    def cgu_despesas(self, orgao=None, ano=None, mes=None, pagina=1):
        """CGU - Despesas públicas."""
        key = os.getenv("CGU_API_KEY", "")
        url = "https://api.portaldatransparencia.gov.br/api-de-dados/despesas"
        headers = {"chave-api-dados": key} if key else {}
        params = {"pagina": pagina}
        if orgao: params["codigoOrgao"] = orgao
        if ano: params["ano"] = ano
        if mes: params["mes"] = mes
        r = self._request(url, params, headers, api_name="cgu", api_type="financeiro")
        return r if isinstance(r, list) else r.get("data", []) if isinstance(r, dict) else []

    def cgu_transferencias(self, municipio=None, uf=None, ano=None, pagina=1):
        """CGU - Transferências constitucionais."""
        key = os.getenv("CGU_API_KEY", "")
        url = "https://api.portaldatransparencia.gov.br/api-de-dados/transferencias"
        headers = {"chave-api-dados": key} if key else {}
        params = {"pagina": pagina}
        if municipio: params["nomeMunicipio"] = municipio
        if uf: params["siglaUF"] = uf
        if ano: params["ano"] = ano
        r = self._request(url, params, headers, api_name="cgu", api_type="financeiro")
        return r if isinstance(r, list) else []

    def cgu_servidores(self, nome=None, orgao=None, pagina=1):
        """CGU - Servidores públicos e remunerações."""
        key = os.getenv("CGU_API_KEY", "")
        url = "https://api.portaldatransparencia.gov.br/api-de-dados/servidores"
        headers = {"chave-api-dados": key} if key else {}
        params = {"pagina": pagina}
        if nome: params["nome"] = nome
        if orgao: params["codigoOrgao"] = orgao
        r = self._request(url, params, headers, api_name="cgu", api_type="cadastral")
        return r if isinstance(r, list) else []

    def cgu_ceis(self, cnpj=None, cpf=None, pagina=1):
        """CGU - CEIS (Empresas Inidôneas)."""
        key = os.getenv("CGU_API_KEY", "")
        url = "https://api.portaldatransparencia.gov.br/api-de-dados/ceis"
        headers = {"chave-api-dados": key} if key else {}
        params = {"pagina": pagina}
        if cnpj: params["cnpjSancionado"] = re.sub(r'\D', '', cnpj)
        if cpf: params["cpfSancionado"] = re.sub(r'\D', '', cpf)
        r = self._request(url, params, headers, api_name="cgu", api_type="sancao")
        return r if isinstance(r, list) else []

    def cgu_cnep(self, cnpj=None, cpf=None, pagina=1):
        """CGU - CNEP (Improbidade Administrativa)."""
        key = os.getenv("CGU_API_KEY", "")
        url = "https://api.portaldatransparencia.gov.br/api-de-dados/cnep"
        headers = {"chave-api-dados": key} if key else {}
        params = {"pagina": pagina}
        if cnpj: params["cnpjSancionado"] = re.sub(r'\D', '', cnpj)
        if cpf: params["cpfSancionado"] = re.sub(r'\D', '', cpf)
        r = self._request(url, params, headers, api_name="cgu", api_type="sancao")
        return r if isinstance(r, list) else []

    def cgu_ceafim(self, cnpj=None, cpf=None, pagina=1):
        """CGU - CEAFIM (Sanções Financeiras)."""
        key = os.getenv("CGU_API_KEY", "")
        url = "https://api.portaldatransparencia.gov.br/api-de-dados/ceafim"
        headers = {"chave-api-dados": key} if key else {}
        params = {"pagina": pagina}
        if cnpj: params["cnpjSancionado"] = re.sub(r'\D', '', cnpj)
        r = self._request(url, params, headers, api_name="cgu", api_type="sancao")
        return r if isinstance(r, list) else []

    def cgu_beneficios(self, municipio=None, uf=None, mes=None, ano=None):
        """CGU - Benefícios sociais (Bolsa Família, etc)."""
        key = os.getenv("CGU_API_KEY", "")
        url = "https://api.portaldatransparencia.gov.br/api-de-dados/novo-bolsa-familia"
        headers = {"chave-api-dados": key} if key else {}
        params = {"pagina": 1}
        if municipio: params["codigoIBGE"] = municipio
        if mes: params["mesAno"] = f"{ano}{mes:02d}" if ano else None
        r = self._request(url, params, headers, api_name="cgu", api_type="default")
        return r if isinstance(r, list) else []

    # --- Comprasnet / SIASG ---
    def comprasnet_licitacoes(self, texto=None, data_ini=None, data_fim=None, pagina=1):
        """Comprasnet - Licitações federais."""
        url = "https://www.gov.br/compras/pt-br/compras-sisrp/api/v1/licitacoes"
        params = {"pagina": pagina}
        if texto: params["texto"] = texto
        if data_ini: params["dataInicial"] = data_ini
        if data_fim: params["dataFinal"] = data_fim
        r = self._request(url, params, api_name="comprasnet", api_type="default")
        return r.get("items", []) if isinstance(r, dict) else r or []

    def siasg_contratos(self, orgao=None, ano=None, pagina=1):
        """SIASG - Sistema Integrado de Serviços Gerais."""
        url = "https://www.gov.br/compras/pt-br/compras-sisrp/api/v1/contratos"
        params = {"pagina": pagina}
        if orgao: params["orgao"] = orgao
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="siasg", api_type="licitacao")
        return r.get("items", []) if isinstance(r, dict) else r or []

    # --- TCU ---
    def tcu_acordaos(self, palavra=None, ano=None, pagina=1):
        """TCU - Acórdãos."""
        url = "https://contas.tcu.gov.br/api/consulta/acordos"
        params = {"pagina": pagina, "tamanhoPagina": 50}
        if palavra: params["palavraChave"] = palavra
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="tcu", api_type="default")
        return r.get("items", []) if isinstance(r, dict) else r or []

    def tcu_contas_irregulares(self, ano=None, pagina=1):
        """TCU - Contas irregulares."""
        url = "https://contas.tcu.gov.br/api/consulta/contas-irregulares"
        params = {"pagina": pagina}
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="tcu", api_type="default")
        return r.get("items", []) if isinstance(r, dict) else r or []

    def tcu_processos(self, palavra=None, pagina=1):
        """TCU - Processos."""
        url = "https://contas.tcu.gov.br/api/consulta/processos"
        params = {"pagina": pagina}
        if palavra: params["palavraChave"] = palavra
        r = self._request(url, params, api_name="tcu", api_type="default")
        return r.get("items", []) if isinstance(r, dict) else r or []

    # ================================================================
    # 2. DADOS CADASTRAIS
    # ================================================================

    # --- Receita Federal ---
    def receita_cnpj(self, cnpj: str) -> Optional[Dict]:
        """Consulta CNPJ completa usando BrasilAPI."""
        cnpj_limpo = re.sub(r'\D', '', cnpj)
        if len(cnpj_limpo) != 14:
            return None
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
        r = self._request(url, api_name="brasilapi", api_type="financeiro")
        
        if r and isinstance(r, dict):
            # Formata para manter a mesma estrutura de resposta
            resultado = {
                "nome": r.get("razao_social"),
                "situacao_cadastral": r.get("descricao_situacao_cadastral"),
                "capital_social": r.get("capital_social"),
                "qsa": []
            }
            if r.get("qsa"):
                for socio in r["qsa"]:
                    resultado["qsa"].append({
                        "nome_socio": socio.get("nome_socio"),
                        "qualificacao_socio": socio.get("qualificacao_socio")
                    })
            return resultado
            
        return None

    def receita_simples_nacional(self, cnpj: str) -> Optional[Dict]:
        """Receita - Simples Nacional."""
        cnpj_limpo = re.sub(r'\D', '', cnpj)
        url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}/simples"
        r = self._request(url, api_name="receita", api_type="financeiro")
        return r if isinstance(r, dict) else None

    def enriquecer_empresa(self, cnpj: str) -> Dict[str, Any]:
        """
        Enriquece dados de uma empresa consultando múltiplas fontes:
        - Receita Federal (dados cadastrais)
        - CEIS (sanções)
        - CNEP (condenações)
        - COAF (lavagem de dinheiro)
        - IBAMA (multas/embargos)
        """
        cnpj_limpo = re.sub(r'\D', '', cnpj)
        resultado = {
            "cnpj": cnpj_limpo,
            "dados_cadastrais": None,
            "sancoes_ceis": [],
            "sancoes_cnep": [],
            "sancoes_ceafim": [],
            "sancoes_coaf": [],
            "multas_ibama": [],
            "embargos_ibama": [],
            "inidonea": False,
            "status": "desconhecido"
        }

        # 1. Receita Federal
        dados_cadastrais = self.receita_cnpj(cnpj_limpo)
        if dados_cadastrais:
            resultado["dados_cadastrais"] = dados_cadastrais
            resultado["status"] = dados_cadastrais.get("situacao_cadastral", "desconhecido")

        # 2. CEIS
        ceis = self.cgu_ceis(cnpj=cnpj_limpo)
        if ceis:
            resultado["sancoes_ceis"] = ceis

        # 3. CNEP
        cnep = self.cgu_cnep(cnpj=cnpj_limpo)
        if cnep:
            resultado["sancoes_cnep"] = cnep

        # 4. CEAFIM
        ceafim = self.cgu_ceafim(cnpj=cnpj_limpo)
        if ceafim:
            resultado["sancoes_ceafim"] = ceafim

        # 5. COAF
        coaf = self.coaf_lista_sancoes(cnpj=cnpj_limpo)
        if coaf:
            resultado["sancoes_coaf"] = coaf

        # 6. IBAMA
        multas = self.ibama_multas(cnpj=cnpj_limpo)
        if multas:
            resultado["multas_ibama"] = multas

        embargos = self.ibama_embargos(cnpj=cnpj_limpo)
        if embargos:
            resultado["embargos_ibama"] = embargos

        # Determina se é inidônea
        if (resultado["sancoes_ceis"] or resultado["sancoes_cnep"] or
            resultado["sancoes_ceafim"] or resultado["sancoes_coaf"]):
            resultado["inidonea"] = True

        return resultado

    # --- Correios ---
    def correios_cep(self, cep: str) -> Optional[Dict]:
        """Correios - Consulta CEP."""
        cep_limpo = re.sub(r'\D', '', cep)
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        r = self._request(url, api_name="correios", api_type="default")
        return r if isinstance(r, dict) and not r.get("erro") else None

    # --- IBGE ---
    def ibge_municipios(self, uf: str = None) -> List[Dict]:
        """IBGE - Lista municípios."""
        if uf:
            url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        else:
            url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
        r = self._request(url, api_name="ibge", api_type="default")
        return r if isinstance(r, list) else []

    def ibge_estados(self) -> List[Dict]:
        """IBGE - Lista estados."""
        url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
        r = self._request(url, api_name="ibge", api_type="default")
        return r if isinstance(r, list) else []

    def ibge_populacao(self, municipio: str, ano: int = None) -> Optional[Dict]:
        """IBGE - População estimada."""
        ano = ano or datetime.now().year - 1
        url = f"https://servicodados.ibge.gov.br/api/v1/projecoes/populacao/{municipio}"
        r = self._request(url, api_name="ibge", api_type="default")
        return r if isinstance(r, dict) else None

    # ================================================================
    # 3. LEGISLATIVO
    # ================================================================

    # --- Câmara dos Deputados ---
    def camara_deputados(self, nome=None, partido=None, uf=None, pagina=1):
        """Câmara - Deputados."""
        url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
        params = {"pagina": pagina, "itens": 100}
        if nome: params["nome"] = nome
        if partido: params["siglaPartido"] = partido
        if uf: params["siglaUf"] = uf
        r = self._request(url, params, api_name="camara", api_type="cadastral")
        return r.get("dados", []) if isinstance(r, dict) else []

    def camara_proposicoes(self, palavra=None, ano=None, pagina=1):
        """Câmara - Proposições (projetos de lei)."""
        url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
        params = {"pagina": pagina, "itens": 100}
        if palavra: params["keywords"] = palavra
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="camara", api_type="default")
        return r.get("dados", []) if isinstance(r, dict) else []

    def camara_votacoes(self, proposicao_id=None, pagina=1):
        """Câmara - Votações."""
        url = "https://dadosabertos.camara.leg.br/api/v2/votacoes"
        params = {"pagina": pagina, "itens": 100}
        if proposicao_id: params["idProposicao"] = proposicao_id
        r = self._request(url, params, api_name="camara", api_type="default")
        return r.get("dados", []) if isinstance(r, dict) else []

    def camara_despesas(self, deputado_id=None, ano=None, mes=None, pagina=1):
        """Câmara - Despesas de deputados (cota parlamentar)."""
        url = "https://dadosabertos.camara.leg.br/api/v2/deputados/{}/despesas".format(deputado_id or "")
        params = {"pagina": pagina, "itens": 100}
        if ano: params["ano"] = ano
        if mes: params["mes"] = mes
        r = self._request(url, params, api_name="camara", api_type="financeiro")
        return r.get("dados", []) if isinstance(r, dict) else []

    def camara_frentes(self, pagina=1):
        """Câmara - Frentes parlamentares."""
        url = "https://dadosabertos.camara.leg.br/api/v2/frentes"
        params = {"pagina": pagina, "itens": 100}
        r = self._request(url, params, api_name="camara", api_type="default")
        return r.get("dados", []) if isinstance(r, dict) else []

    def camara_eventos(self, data_ini=None, data_fim=None, pagina=1):
        """Câmara - Eventos (sessões, audiências)."""
        url = "https://dadosabertos.camara.leg.br/api/v2/eventos"
        params = {"pagina": pagina, "itens": 100}
        if data_ini: params["dataInicio"] = data_ini
        if data_fim: params["dataFim"] = data_fim
        r = self._request(url, params, api_name="camara", api_type="default")
        return r.get("dados", []) if isinstance(r, dict) else []

    # --- Senado Federal ---
    def senado_senadores(self, uf=None, partido=None, pagina=1):
        """Senado - Senadores."""
        url = "https://legis.senado.leg.br/dadosabertos/senador/lista/atual"
        params = {"pagina": pagina}
        if uf: params["uf"] = uf
        r = self._request(url, params, api_name="senado", api_type="cadastral")
        return r.get("ListaParlamentarEmExercicio", {}).get("Parlamentares", {}).get("Parlamentar", []) if isinstance(r, dict) else []

    def senado_materias(self, palavra=None, ano=None, pagina=1):
        """Senado - Matérias legislativas."""
        url = "https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista"
        params = {"pagina": pagina}
        if palavra: params["palavraChave"] = palavra
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="senado", api_type="default")
        return r.get("PesquisaBasicaMateria", {}).get("Materias", {}).get("Materia", []) if isinstance(r, dict) else []

    def senado_votacoes(self, materia_id=None, pagina=1):
        """Senado - Votações."""
        url = "https://legis.senado.leg.br/dadosabertos/materia/votacoes"
        params = {"pagina": pagina}
        if materia_id: params["codigoMateria"] = materia_id
        r = self._request(url, params, api_name="senado", api_type="default")
        return r if isinstance(r, dict) else {}

    # ================================================================
    # 4. ELEIÇÕES (TSE)
    # ================================================================

    def tse_candidatos(self, ano=2024, cargo=None, uf=None, pagina=1):
        """TSE - Candidatos."""
        url = f"https://resultados.tse.jus.br/{ano}/candidatos"
        params = {"pagina": pagina}
        if cargo: params["cargo"] = cargo
        if uf: params["uf"] = uf
        r = self._request(url, params, api_name="tse", api_type="cadastral")
        return r if isinstance(r, list) else r.get("candidatos", []) if isinstance(r, dict) else []

    def tse_doacoes(self, ano=2024, candidato_id=None, uf=None):
        """TSE - Doações de campanha (Prestação de contas)."""
        url = f"https://divulgacandcontas.tse.jus.br/dadosabertos/receitas"
        params = {"anoEleitoral": ano}
        if candidato_id: params["codigoCandidato"] = candidato_id
        if uf: params["siglaUF"] = uf
        r = self._request(url, params, api_name="tse", api_type="default")
        return r if isinstance(r, list) else []

    def tse_prestacao_contas(self, ano=2024, uf=None, pagina=1):
        """TSE - Prestação de contas completa."""
        url = f"https://divulgacandcontas.tse.jus.br/dadosabertos/prestacaocontas"
        params = {"anoEleitoral": ano, "pagina": pagina}
        if uf: params["siglaUF"] = uf
        r = self._request(url, params, api_name="tse", api_type="default")
        return r if isinstance(r, list) else []

    # ================================================================
    # 5. FINANCEIRO
    # ================================================================

    # --- Banco Central (BACEN) ---
    def bacen_taxa_cambio(self, moeda="USD", data=None):
        """BACEN - Taxa de câmbio."""
        url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@data)"
        params = {"@moeda": f"'{moeda}'", "@data": f"'{data}'" if data else None}
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    def bacen_taxa_juros(self, data=None):
        """BACEN - Taxa SELIC."""
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 432}  # SELIC
        if data: params["data"] = data
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    def bacen_divida_publica(self, ano=None, mes=None):
        """BACEN - Dívida pública federal."""
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 4389}  # Dívida pública
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    def bacen_inadimplencia(self, pagina=1):
        """BACEN - Inadimplência bancária."""
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 21082}  # Inadimplência
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    # --- SICONFI ---
    def siconfi_receitas(self, municipio=None, ano=None, pagina=1):
        """SICONFI - Receitas municipais."""
        url = "https://apidatalake.tesouro.gov.br/ords/siconfi/api/v1/receita"
        params = {"pagina": pagina}
        if municipio: params["id_municipio"] = municipio
        if ano: params["ano_exercicio"] = ano
        r = self._request(url, params, api_name="siconfi", api_type="financeiro")
        return r.get("items", []) if isinstance(r, dict) else r or []

    def siconfi_despesas(self, municipio=None, ano=None, pagina=1):
        """SICONFI - Despesas municipais."""
        url = "https://apidatalake.tesouro.gov.br/ords/siconfi/api/v1/despesa"
        params = {"pagina": pagina}
        if municipio: params["id_municipio"] = municipio
        if ano: params["ano_exercicio"] = ano
        r = self._request(url, params, api_name="siconfi", api_type="financeiro")
        return r.get("items", []) if isinstance(r, dict) else r or []

    def siconfi_rgf(self, municipio=None, ano=None, pagina=1):
        """SICONFI - Relatório de Gestão Fiscal."""
        url = "https://apidatalake.tesouro.gov.br/ords/siconfi/api/v1/rgf"
        params = {"pagina": pagina}
        if municipio: params["id_municipio"] = municipio
        if ano: params["ano_exercicio"] = ano
        r = self._request(url, params, api_name="siconfi", api_type="default")
        return r.get("items", []) if isinstance(r, dict) else r or []

    # --- BNDES ---
    def bndes_financiamentos(self, ano=None, cliente=None, pagina=1):
        """BNDES - Financiamentos (Carteira)."""
        url = "https://www.bndes.gov.br/wps/wcm/connect/api/json/dadosabertos"
        params = {"pagina": pagina}
        if ano: params["ano"] = ano
        if cliente: params["cliente"] = cliente
        r = self._request(url, params, api_name="bndes", api_type="default")
        return r.get("items", []) if isinstance(r, dict) else r or []

    # ================================================================
    # 6. AGÊNCIAS REGULADORAS
    # ================================================================

    # --- ANATEL ---
    def anatel_concessoes(self, pagina=1):
        """ANATEL - Concessões de telecomunicações."""
        url = "https://sistemas.anatel.gov.br/api/concessoes"
        params = {"pagina": pagina}
        r = self._request(url, params, api_name="anatel", api_type="default")
        return r if isinstance(r, list) else r.get("items", []) if isinstance(r, dict) else []

    # --- ANP (Petróleo) ---
    def anp_postos(self, uf=None, municipio=None, pagina=1):
        """ANP - Postos de combustível."""
        url = "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/postos/api"
        params = {"pagina": pagina}
        if uf: params["uf"] = uf
        if municipio: params["municipio"] = municipio
        r = self._request(url, params, api_name="anp", api_type="default")
        return r if isinstance(r, list) else []

    def anp_precos_combustiveis(self, uf=None, produto=None, semana=None):
        """ANP - Preços de combustíveis."""
        url = "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos/api"
        params = {}
        if uf: params["sigla_uf"] = uf
        if produto: params["produto"] = produto
        if semana: params["semana"] = semana
        r = self._request(url, params, api_name="anp", api_type="default")
        return r if isinstance(r, list) else []

    # --- ANEEL (Energia) ---
    def aneel_concessionarias(self, pagina=1):
        """ANEEL - Concessionárias de energia."""
        url = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
        params = {"resource_id": "d6b04f48-2c52-4c4e-9c1e-8c1c1c1c1c1c", "limit": 100}
        r = self._request(url, params, api_name="aneel", api_type="default")
        return r.get("result", {}).get("records", []) if isinstance(r, dict) else []

    # --- ANTT (Transporte Terrestre) ---
    def antt_concessionarias(self, pagina=1):
        """ANTT - Concessionárias de rodovias."""
        url = "https://www.gov.br/antt/pt-br/assuntos/dados-abertos/api/concessionarias"
        params = {"pagina": pagina}
        r = self._request(url, params, api_name="antt", api_type="default")
        return r if isinstance(r, list) else []

    # --- ANS (Saúde) ---
    def ans_operadoras(self, nome=None, registro=None, pagina=1):
        """ANS - Operadoras de planos de saúde."""
        url = "https://www.ans.gov.br/api/operadoras"
        params = {"pagina": pagina}
        if nome: params["nome"] = nome
        if registro: params["registro"] = registro
        r = self._request(url, params, api_name="ans", api_type="default")
        return r if isinstance(r, list) else []

    # --- ANA (Águas) ---
    def ana_concessoes(self, pagina=1):
        """ANA - Concessões de água/esgoto."""
        url = "https://dadosabertos.ana.gov.br/api/concessoes"
        params = {"pagina": pagina}
        r = self._request(url, params, api_name="ana", api_type="default")
        return r if isinstance(r, list) else []

    # ================================================================
    # 7. JUDICIAL
    # ================================================================

    # --- CNJ (Conselho Nacional de Justiça) ---
    def cnj_processos(self, numero=None, tribunal=None, pagina=1):
        """CNJ - Consulta processual (DataJud)."""
        url = "https://datajud.cnj.jus.br/api/v1/processos"
        params = {"pagina": pagina}
        if numero: params["numero"] = numero
        if tribunal: params["tribunal"] = tribunal
        r = self._request(url, params, api_name="cnj", api_type="default")
        return r if isinstance(r, list) else r.get("items", []) if isinstance(r, dict) else []

    # --- STF ---
    def stf_processos(self, numero=None, pagina=1):
        """STF - Processos no Supremo."""
        url = "https://portal.stf.jus.br/api/processos"
        params = {"pagina": pagina}
        if numero: params["numero"] = numero
        r = self._request(url, params, api_name="stf", api_type="default")
        return r if isinstance(r, list) else []

    # --- JusBrasil ---
    def jusbrasil_busca(self, termo=None, pagina=1):
        """JusBrasil - Busca de processos públicos."""
        url = "https://api.jusbrasil.com.br/search"
        params = {"pagina": pagina, "tipo": "processo"}
        if termo: params["q"] = termo
        r = self._request(url, params, api_name="jusbrasil", api_type="default")
        return r if isinstance(r, dict) else {}

    # ================================================================
    # 8. SOCIAL / SAÚDE / EDUCAÇÃO / MEIO AMBIENTE
    # ================================================================

    # --- DATASUS ---
    def datasus_cnes(self, municipio=None, uf=None, pagina=1):
        """DATASUS - CNES (Cadastro Nacional de Estabelecimentos de Saúde)."""
        url = "http://api.datasus.gov.br/cnes"
        params = {"pagina": pagina}
        if municipio: params["municipio"] = municipio
        if uf: params["uf"] = uf
        r = self._request(url, params, api_name="datasus", api_type="default")
        return r if isinstance(r, list) else []

    def datasus_sih(self, uf=None, ano=None, mes=None):
        """DATASUS - SIH (Sistema de Informações Hospitalares)."""
        url = "http://api.datasus.gov.br/sih"
        params = {}
        if uf: params["uf"] = uf
        if ano: params["ano"] = ano
        if mes: params["mes"] = mes
        r = self._request(url, params, api_name="datasus", api_type="default")
        return r if isinstance(r, list) else []

    # --- INEP ---
    def inep_escolas(self, nome=None, municipio=None, uf=None, pagina=1):
        """INEP - Escolas cadastradas."""
        url = "https://api.inep.gov.br/escolas"
        params = {"pagina": pagina}
        if nome: params["nome"] = nome
        if municipio: params["municipio"] = municipio
        if uf: params["uf"] = uf
        r = self._request(url, params, api_name="inep", api_type="default")
        return r if isinstance(r, list) else []

    def inep_indicadores(self, escola_id=None, pagina=1):
        """INEP - Indicadores educacionais."""
        url = "https://api.inep.gov.br/indicadores"
        params = {"pagina": pagina}
        if escola_id: params["escola"] = escola_id
        r = self._request(url, params, api_name="inep", api_type="default")
        return r if isinstance(r, list) else []

    # --- IBAMA ---
    def ibama_multas(self, cnpj=None, cpf=None, pagina=1):
        """IBAMA - Multas ambientais."""
        url = "https://servicos.ibama.gov.br/consultas/multas"
        params = {"pagina": pagina}
        if cnpj: params["cnpj"] = re.sub(r'\D', '', cnpj)
        if cpf: params["cpf"] = re.sub(r'\D', '', cpf)
        r = self._request(url, params, api_name="ibama", api_type="default")
        return r if isinstance(r, list) else []

    def ibama_embargos(self, cnpj=None, cpf=None, pagina=1):
        """IBAMA - Lista de embargos."""
        url = "https://servicos.ibama.gov.br/consultas/embargos"
        params = {"pagina": pagina}
        if cnpj: params["cnpj"] = re.sub(r'\D', '', cnpj)
        r = self._request(url, params, api_name="ibama", api_type="default")
        return r if isinstance(r, list) else []

    # --- INMET (Meteorologia) ---
    def inmet_estacoes(self, pagina=1):
        """INMET - Estações meteorológicas."""
        url = "https://apitempo.inmet.gov.br/estacoes"
        r = self._request(url, api_name="inmet", api_type="default")
        return r if isinstance(r, list) else []

    # --- EMBRAPA (Agricultura) ---
    def embrapa_producao(self, ano=None, pagina=1):
        """EMBRAPA - Dados de produção agrícola."""
        url = "http://vitibrasil.cnpuv.embrapa.br/api/producao"
        params = {"pagina": pagina}
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="embrapa", api_type="default")
        return r if isinstance(r, list) else []

    # ================================================================
    # 9. DIÁRIOS OFICIAIS
    # ================================================================

    def dou_pesquisa(self, texto=None, data_ini=None, data_fim=None, secao=None):
        """DOU - Diário Oficial da União (Querido Diário)."""
        url = "https://queridodiario.ok.org.br/api/gazettes"
        params = {}
        if texto: params["keywords"] = texto
        if data_ini: params["since"] = data_ini
        if data_fim: params["until"] = data_fim
        if secao: params["section"] = secao
        r = self._request(url, params, api_name="dou", api_type="default")
        return r.get("gazettes", []) if isinstance(r, dict) else r or []

    def doe_pesquisa(self, uf=None, texto=None, data_ini=None, data_fim=None):
        """DOE - Diários Oficiais Estaduais."""
        url = "https://queridodiario.ok.org.br/api/gazettes"
        params = {}
        if uf: params["territory_id"] = uf
        if texto: params["keywords"] = texto
        if data_ini: params["since"] = data_ini
        if data_fim: params["until"] = data_fim
        r = self._request(url, params, api_name="doe", api_type="default")
        return r.get("gazettes", []) if isinstance(r, dict) else r or []

    # ================================================================
    # 9.5. COAF / UIF - PREVENÇÃO À LAVAGEM DE DINHEIRO
    # ================================================================

    # --- COAF (Conselho de Controle de Atividades Financeiras) ---
    # O COAF foi renomeado para UIF (Unidade de Inteligência Financeira)
    # em 2024, mas ainda é conhecido como COAF.

    def coaf_lista_sancoes(self, nome=None, cnpj=None, cpf=None, pagina=1):
        """
        COAF/UIF - Lista de Pessoas e Entidades Sujeitas a Sanções.
        Lista pública de pessoas/empresas sancionadas por lavagem de dinheiro.
        URL: https://www.gov.br/caixa/pt-br/.../coaf
        """
        url = "https://www.gov.br/fazenda/pt-br/assuntos/comite-de-relacoes-financeiras-coaf/dados-abertos"
        params = {"pagina": pagina}
        if nome: params["nome"] = nome
        if cnpj: params["cnpj"] = re.sub(r'\D', '', cnpj)
        if cpf: params["cpf"] = re.sub(r'\D', '', cpf)
        r = self._request(url, params, api_name="coaf", api_type="default")
        return r if isinstance(r, list) else r.get("items", []) if isinstance(r, dict) else []

    def coaf_comunicacoes_operacoes_suspeitas(self, ano=None, pagina=1):
        """
        COAF - Comunicações de Operações Suspeitas (dados agregados/anonimizados).
        Estatísticas públicas de comunicações recebidas pelo COAF.
        """
        url = "https://www.gov.br/fazenda/pt-br/assuntos/comite-de-relacoes-financeiras-coaf/dados-abertos/comunicacoes"
        params = {"pagina": pagina}
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="coaf", api_type="default")
        return r if isinstance(r, list) else r.get("items", []) if isinstance(r, dict) else []

    def coaf_relatorios_estatisticos(self, ano=None):
        """
        COAF - Relatórios estatísticos anuais de atividades.
        Contém dados agregados sobre operações suspeitas por setor.
        """
        url = "https://www.gov.br/fazenda/pt-br/assuntos/comite-de-relacoes-financeiras-coaf/dados-abertos/relatorios"
        params = {}
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="coaf", api_type="default")
        return r if isinstance(r, dict) else {}

    def coaf_ploa_lista(self, pagina=1):
        """
        COAF - PLOA (Pessoas e Entidades Listadas para fins de PLD/CFT).
        Lista de pessoas designadas por resoluções da ONU ou sanções internas.
        """
        url = "https://www.gov.br/fazenda/pt-br/assuntos/comite-de-relacoes-financeiras-coaf/dados-abertos/ploa"
        params = {"pagina": pagina}
        r = self._request(url, params, api_name="coaf", api_type="default")
        return r if isinstance(r, list) else r.get("items", []) if isinstance(r, dict) else []

    def coaf_setores_regulados(self, pagina=1):
        """
        COAF - Setores regulados (instituições obrigadas a reportar).
        Lista de setores sujeitos a PLD: bancos, imobiliárias, joalherias, etc.
        """
        url = "https://www.gov.br/fazenda/pt-br/assuntos/comite-de-relacoes-financeiras-coaf/dados-abertos/setores"
        params = {"pagina": pagina}
        r = self._request(url, params, api_name="coaf", api_type="default")
        return r if isinstance(r, list) else r.get("items", []) if isinstance(r, dict) else []

    # --- COAF via BACEN (Sistema de Comunicação) ---
    def bacen_coaf_comunicacoes(self, ano=None, setor=None, pagina=1):
        """
        BACEN - Comunicações ao COAF via BACEN.
        Dados agregados de comunicações de operações suspeitas enviadas ao COAF.
        """
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 27968}  # Comunicações COAF
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    # --- COIF (Cadastro de Operações de Câmbio) ---
    def bacen_coif_cambio(self, data_ini=None, data_fim=None, pagina=1):
        """
        BACEN - COIF (Cadastro de Operações de Câmbio e Transferências Internacionais).
        Operações de câmbio que podem indicar lavagem de dinheiro.
        """
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 1}  # Operações de câmbio
        if data_ini: params["dataInicial"] = data_ini
        if data_fim: params["dataFinal"] = data_fim
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    # --- CIP (Capacidade de Pagamento) ---
    def bacen_capacidade_pagamento(self, ano=None, mes=None):
        """
        BACEN - Capacidade de pagamento externo.
        Indicador de saúde financeira do país/município.
        """
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 22970}
        if ano: params["ano"] = ano
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    # --- SISBAF (Sistema do Banco Central) ---
    def bacen_sisbaf_inadimplencia(self, cnpj=None, pagina=1):
        """
        BACEN - SISBAF - Inadimplência bancária por instituição.
        Verifica se empresa/instituição está inadimplente no sistema bancário.
        """
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 21082}
        if cnpj: params["cnpj"] = re.sub(r'\D', '', cnpj)
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    # --- SCR (Sistema de Informações de Crédito) ---
    def bacen_scr_operacoes_credito(self, cnpj=None, data=None):
        """
        BACEN - SCR - Operações de crédito registradas.
        Verifica operações de crédito de uma empresa no SCR.
        """
        url = "https://olinda.bcb.gov.br/olinda/servico/SGS/versao/v1/odata/serie/dados"
        params = {"codigoSerie": 20542}
        if cnpj: params["cnpj"] = re.sub(r'\D', '', cnpj)
        if data: params["data"] = data
        r = self._request(url, params, api_name="bacen", api_type="default")
        return r.get("value", []) if isinstance(r, dict) else []

    # ================================================================
    # 10. PAINEL DE PREÇOS
    # ================================================================

    def painel_precos(self, termo=None, pagina=1):
        """Painel de Preços do Governo Federal."""
        url = "https://paineis.preco.governo.digital/api/v1/pesquisa"
        params = {"pagina": pagina}
        if termo: params["termo"] = termo
        r = self._request(url, params, api_name="painel", api_type="default")
        return r.get("items", []) if isinstance(r, dict) else r or []

    def painel_precos_item(self, item_id=None):
        """Painel de Preços - Detalhe de item."""
        url = f"https://paineis.preco.governo.digital/api/v1/item/{item_id or ''}"
        r = self._request(url, api_name="painel", api_type="default")
        return r if isinstance(r, dict) else {}

    # ================================================================
    # MÉTODOS DE CRUZAMENTO
    # ================================================================

    def cruzar_empresa_completo(self, cnpj: str) -> Dict[str, Any]:
        """
        Cruzamento COMPLETO de uma empresa em todas as fontes.
        Retorna um relatório consolidado.
        """
        cnpj_limpo = re.sub(r'\D', '', cnpj)
        resultado = {
            "cnpj": cnpj_limpo,
            "dados_cadastrais": None,
            "sancoes": {"ceis": [], "cnep": [], "ceafim": [], "ibama_multas": [], "ibama_embargos": []},
            "contratos_pncp": [],
            "licitacoes_comprasnet": [],
            "processos_tcu": [],
            "doacoes_tse": [],
            "processos_judiciais": [],
            "alertas": []
        }

        # 1. Receita Federal
        resultado["dados_cadastrais"] = self.receita_cnpj(cnpj_limpo)

        # 2. Sanções
        resultado["sancoes"]["ceis"] = self.cgu_ceis(cnpj=cnpj_limpo)
        resultado["sancoes"]["cnep"] = self.cgu_cnep(cnpj=cnpj_limpo)
        resultado["sancoes"]["ceafim"] = self.cgu_ceafim(cnpj=cnpj_limpo)
        resultado["sancoes"]["ibama_multas"] = self.ibama_multas(cnpj=cnpj_limpo)
        resultado["sancoes"]["ibama_embargos"] = self.ibama_embargos(cnpj=cnpj_limpo)

        # 3. Contratos e licitações
        resultado["contratos_pncp"] = self.pncp_contratos()
        resultado["licitacoes_comprasnet"] = self.comprasnet_licitacoes()

        # 4. TCU
        resultado["processos_tcu"] = self.tcu_processos(palavra=cnpj_limpo)

        # 5. COAF/UIF - Lavagem de dinheiro
        coaf_sancoes = self.coaf_lista_sancoes(cnpj=cnpj_limpo)
        if coaf_sancoes:
            resultado["sancoes"]["coaf"] = coaf_sancoes
            resultado["alertas"].append("🚨 Empresa sancionada pelo COAF/UIF (Lavagem de Dinheiro)")

        # 6. Gera alertas
        if resultado["sancoes"]["ceis"]:
            resultado["alertas"].append("🚨 Empresa no CEIS (Inidônea)")
        if resultado["sancoes"]["cnep"]:
            resultado["alertas"].append("🚨 Empresa no CNEP (Improbidade)")
        if resultado["sancoes"]["ceafim"]:
            resultado["alertas"].append("🚨 Empresa no CEAFIM (Sanção Financeira)")
        if resultado["sancoes"]["ibama_multas"]:
            resultado["alertas"].append(f"⚠️ {len(resultado['sancoes']['ibama_multas'])} multas ambientais")
        if resultado["sancoes"]["ibama_embargos"]:
            resultado["alertas"].append(f"🚨 {len(resultado['sancoes']['ibama_embargos'])} embargos ambientais")

        if resultado["dados_cadastrais"]:
            situacao = resultado["dados_cadastrais"].get("situacao", "").upper()
            if situacao in ("BAIXADA", "INAPTA", "SUSPENSA"):
                resultado["alertas"].append(f"⚠️ Empresa {situacao} na Receita")

        return resultado

    def investigar_municipio_completo(self, nome_municipio: str, uf: str) -> Dict[str, Any]:
        """
        Investigação completa de um município em todas as fontes.
        """
        resultado = {
            "municipio": nome_municipio,
            "uf": uf,
            "codigo_ibge": None,
            "receitas": [],
            "despesas": [],
            "transferencias": [],
            "servidores": [],
            "beneficios": [],
            "licitacoes_pncp": [],
            "populacao": None,
        }

        # 1. Busca código IBGE
        municipios = self.ibge_municipios(uf)
        for m in municipios:
            if m.get("nome", "").lower() == nome_municipio.lower():
                resultado["codigo_ibge"] = str(m.get("id", ""))
                break

        # 2. População
        if resultado["codigo_ibge"]:
            resultado["populacao"] = self.ibge_populacao(resultado["codigo_ibge"])

        # 3. Finanças (SICONFI)
        if resultado["codigo_ibge"]:
            resultado["receitas"] = self.siconfi_receitas(resultado["codigo_ibge"])
            resultado["despesas"] = self.siconfi_despesas(resultado["codigo_ibge"])

        # 4. Transferências (CGU)
        resultado["transferencias"] = self.cgu_transferencias(municipio=nome_municipio, uf=uf)

        # 5. Servidores (CGU)
        resultado["servidores"] = self.cgu_servidores()

        # 6. Licitações (PNCP)
        resultado["licitacoes_pncp"] = self.pncp_licitacoes()

        return resultado

    def listar_todas_apis(self) -> Dict[str, List[str]]:
        """Lista todas as APIs disponíveis organizadas por categoria."""
        return {
            "transparencia": [
                "pncp_licitacoes", "pncp_contratos", "pncp_orgaos",
                "cgu_despesas", "cgu_transferencias", "cgu_servidores",
                "cgu_ceis", "cgu_cnep", "cgu_ceafim", "cgu_beneficios",
                "comprasnet_licitacoes", "siasg_contratos",
                "tcu_acordaos", "tcu_contas_irregulares", "tcu_processos",
            ],
            "cadastrais": [
                "receita_cnpj", "receita_simples_nacional",
                "correios_cep",
                "ibge_municipios", "ibge_estados", "ibge_populacao",
            ],
            "legislativo": [
                "camara_deputados", "camara_proposicoes", "camara_votacoes",
                "camara_despesas", "camara_frentes", "camara_eventos",
                "senado_senadores", "senado_materias", "senado_votacoes",
            ],
            "eleicoes": [
                "tse_candidatos", "tse_doacoes", "tse_prestacao_contas",
            ],
            "financeiro": [
                "bacen_taxa_cambio", "bacen_taxa_juros", "bacen_divida_publica", "bacen_inadimplencia",
                "siconfi_receitas", "siconfi_despesas", "siconfi_rgf",
                "bndes_financiamentos",
            ],
            "reguladoras": [
                "anatel_concessoes", "anp_postos", "anp_precos_combustiveis",
                "aneel_concessionarias", "antt_concessionarias",
                "ans_operadoras", "ana_concessoes",
            ],
            "judicial": [
                "cnj_processos", "stf_processos", "jusbrasil_busca",
            ],
            "social": [
                "datasus_cnes", "datasus_sih",
                "inep_escolas", "inep_indicadores",
                "ibama_multas", "ibama_embargos",
                "inmet_estacoes", "embrapa_producao",
            ],
            "diarios": [
                "dou_pesquisa", "doe_pesquisa",
            ],
            "precos": [
                "painel_precos", "painel_precos_item",
            ],
            "coaf_lavagem": [
                "coaf_lista_sancoes", "coaf_comunicacoes_operacoes_suspeitas",
                "coaf_relatorios_estatisticos", "coaf_ploa_lista",
                "coaf_setores_regulados",
                "bacen_coaf_comunicacoes", "bacen_coif_cambio",
                "bacen_capacidade_pagamento", "bacen_sisbaf_inadimplencia",
                "bacen_scr_operacoes_credito",
            ],
        }
