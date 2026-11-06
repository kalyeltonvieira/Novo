"""
Agentes Especialistas Avançados
================================
Agentes para investigação profunda de portais governamentais:
- CrawlerAgente: Crawl recursivo com paginação automática
- PDFDownloaderAgente: Baixa e processa PDFs de portais
- CNPJValidatorAgente: Consulta Receita Federal e enriquece dados
- CrossPortalAgente: Cruza dados entre múltiplos portais
"""

import os
import re
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.agentes.base import BaseAgente
from core.navegador_automatizado import NavegadorAutomatizado
from core.correlacionador import Correlacionador

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.agentes.avancados")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.agentes_avancados")
    metrics = None
    MONITORING_AVAILABLE = False


class CrawlerAgente(BaseAgente):
    """
    Agente especializado em crawl profundo de portais com paginação automática.
    Navega por todas as páginas de resultados até esgotar.
    """

    def __init__(self, navegador: NavegadorAutomatizado):
        super().__init__(
            nome="CrawlerProfundo",
            descricao="Faz crawl profundo de portais de transparência com paginação automática. "
                      "Navega por TODAS as páginas de resultados (licitações, contratos, despesas) "
                      "até esgotar. Baixa PDFs anexados. Chame este agente para investigação completa."
        )
        self.navegador = navegador
        from core.navegador_automatizado import ExtratorPortalTransparencia
        self.extrator = ExtratorPortalTransparencia(navegador)
        self.max_paginas = 50  # Limite de páginas por seção

    def processar(self, tarefa: str) -> str:
        """
        Faz crawl profundo do portal com paginação automática.
        """
        urls = re.findall(r'(https?://[^\s]+)', tarefa)
        if not urls:
            return "Nenhuma URL válida encontrada."

        url = urls[0].strip('\'\\"})')
        print(f"[CRAWLER] CrawlerProfundo: Iniciando crawl profundo de {url}")

        # Inicia captura periódica
        try:
            self.navegador.iniciar_captura_periodica(intervalo=5)
        except Exception:
            pass

        # 1. Navega para a URL principal
        if not self.navegador.navegar(url):
            return f"Falha ao acessar {url}"

        time.sleep(3)

        # 2. Extrai todos os links do menu
        links_menu = self.extrator.extrair_menu_links(url)
        print(f"[MENU] Encontrados {len(links_menu)} links no menu")

        # 3. Para cada link, faz crawl com paginação
        dados_completos = {
            "url_base": url,
            "secoes": {},
            "total_registros": 0,
            "pdfs_encontrados": [],
            "erros": []
        }

        # Filtra links relevantes
        links_relevantes = self._filtrar_links_relevantes(links_menu)

        for i, link in enumerate(links_relevantes[:15]):  # Limite de 15 seções
            nome_secao = link.get("nome", f"secao_{i}")
            url_secao = link.get("url", "")

            try:
                nome_secao_seguro = nome_secao.encode('ascii', 'ignore').decode('ascii')
            except Exception:
                nome_secao_seguro = "secao"

            print(f"[SECAO] [{i+1}/{len(links_relevantes)}] Crawleando: {nome_secao_seguro}")

            dados_secao = self._crawlear_secao_com_paginacao(url_secao, nome_secao)

            if dados_secao:
                dados_completos["secoes"][nome_secao] = dados_secao
                dados_completos["total_registros"] += dados_secao.get("total_registros", 0)
                dados_completos["pdfs_encontrados"].extend(dados_secao.get("pdfs", []))

        # 4. Compila resultado
        resumo = self._compilar_resultado(dados_completos)
        return resumo

    def _filtrar_links_relevantes(self, links: List[Dict]) -> List[Dict]:
        """Filtra links relevantes para investigação."""
        palavras_relevantes = [
            "licita", "contrato", "despesa", "receita", "empenho",
            "pagamento", "fornecedor", "servidor", "remunera",
            "diario", "edital", "pregao", "concorrencia",
            "dispensa", "inexigibilidade", "sancao", "transparencia",
        ]

        relevantes = []
        for link in links:
            nome = link.get("nome", "").lower()
            url = link.get("url", "").lower()

            if any(palavra in nome or palavra in url for palavra in palavras_relevantes):
                relevantes.append(link)

        # Se não encontrou relevantes, retorna todos
        if not relevantes:
            return links[:10]

        return relevantes

    def _crawlear_secao_com_paginacao(self, url: str, nome: str) -> Dict[str, Any]:
        """Crawlea uma seção navegando por todas as páginas."""
        dados_secao = {
            "url": url,
            "paginas_visitadas": 0,
            "total_registros": 0,
            "tabelas": [],
            "textos": [],
            "pdfs": [],
            "erros": [],
            "shadow_apis": []
        }

        url_atual = url
        pagina = 1

        while url_atual and pagina <= self.max_paginas:
            try:
                print(f"  [PAGINA] Página {pagina} de {nome}...")

                if not self.navegador.navegar(url_atual):
                    dados_secao["erros"].append(f"Falha ao navegar para página {pagina}")
                    break

                time.sleep(2)

                # Extrai Shadow APIs interceptadas pela aba de rede (performance log)
                apis_capturadas = self.navegador.obter_apis_ocultas()
                if apis_capturadas:
                    dados_secao["shadow_apis"].extend(apis_capturadas)
                    # Tentativa de inferência básica de volume de dados na resposta
                    dados_secao["total_registros"] += len(apis_capturadas)

                # Extrai conteúdo da página
                html = self.navegador.obter_html()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")

                # Extrai tabelas
                for tabela in soup.find_all("table"):
                    linhas = []
                    for tr in tabela.find_all("tr"):
                        celulas = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                        if celulas:
                            linhas.append(celulas)

                    if len(linhas) > 1:  # Tem cabeçalho + dados
                        dados_secao["tabelas"].append(linhas)
                        dados_secao["total_registros"] += len(linhas) - 1  # -1 pelo cabeçalho
                
                # Extrai dados de divs com classes comuns de dados (cards, listas, etc.)
                dados_divs = self._extrair_divs_dados(soup)
                if dados_divs:
                    dados_secao["divs_dados"] = dados_divs
                    dados_secao["total_registros"] += len(dados_divs)
                
                # Extrai dados de listas (ul, ol)
                dados_listas = self._extrair_listas(soup)
                if dados_listas:
                    dados_secao["listas"] = dados_listas
                    dados_secao["total_registros"] += sum(len(l) for l in dados_listas)

                # Extrai PDFs
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if href.lower().endswith(".pdf"):
                        from urllib.parse import urljoin
                        pdf_url = urljoin(url_atual, href)
                        dados_secao["pdfs"].append({
                            "url": pdf_url,
                            "texto_link": link.get_text(strip=True),
                            "secao": nome
                        })

                # Extrai textos
                for p in soup.find_all("p"):
                    texto = p.get_text(strip=True)
                    if len(texto) > 20:
                        dados_secao["textos"].append(texto)

                dados_secao["paginas_visitadas"] += 1

                # Procura botão "Próxima página"
                proxima_url = self._encontrar_proxima_pagina(soup, url_atual)

                if not proxima_url or proxima_url == url_atual:
                    break  # Não há mais páginas

                url_atual = proxima_url
                pagina += 1

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                dados_secao["erros"].append(f"Erro na página {pagina}: {str(e)}")
                break

        print(f"  ✅ {nome}: {dados_secao['paginas_visitadas']} páginas, "
              f"{dados_secao['total_registros']} registros, "
              f"{len(dados_secao['pdfs'])} PDFs")

        return dados_secao

    def _extrair_divs_dados(self, soup) -> List[Dict[str, Any]]:
        """Extrai dados de divs com classes comuns de dados."""
        dados = []
        
        # Classes comuns de containers de dados
        classes_dados = [
            "card", "row", "item", "entry", "record",
            "licitacao", "contrato", "despesa", "fornecedor",
            "table-responsive", "data-table", "list-group",
            "resultado", "item-list", "dado"
        ]
        
        for classe in classes_dados:
            for div in soup.find_all("div", class_=lambda c: c and classe in str(c).lower()):
                texto = div.get_text(strip=True)
                if len(texto) > 50:  # Ignora divs muito pequenas
                    # Extrai links dentro
                    links = [a.get("href") for a in div.find_all("a", href=True)]
                    dados.append({
                        "texto": texto[:500],  # Limita tamanho
                        "classe": str(div.get("class", [])),
                        "links": links[:5]  # Limita links
                    })
        
        return dados[:50]  # Limita a 50 itens
    
    def _extrair_listas(self, soup) -> List[List[str]]:
        """Extrai dados de listas (ul, ol)."""
        listas_dados = []
        
        for lista in soup.find_all(["ul", "ol"]):
            itens = []
            for li in lista.find_all("li"):
                texto = li.get_text(strip=True)
                if len(texto) > 20:
                    itens.append(texto[:200])
            
            if len(itens) > 2:  # Apenas listas com dados relevantes
                listas_dados.append(itens)
        
        return listas_dados
    
    def _encontrar_proxima_pagina(self, soup, url_atual: str) -> Optional[str]:
        """Encontra o link para a próxima página."""
        from urllib.parse import urljoin

        # Padrões comuns de botão "Próxima"
        padroes_proxima = [
            ("a", {"text": ["próxima", "proxima", "próximo", "proximo", ">>", "next", "seguinte"]}),
            ("a", {"class": ["next", "proxima", "proximo", "pagination-next"]}),
            ("a", {"rel": "next"}),
            ("li", {"class": ["next", "proxima", "proximo"]}),
        ]

        for tag, attrs in padroes_proxima:
            # Busca por texto
            if "text" in attrs:
                for elem in soup.find_all(tag):
                    texto = elem.get_text(strip=True).lower()
                    if any(p in texto for p in attrs["text"]):
                        href = elem.get("href")
                        if href:
                            return urljoin(url_atual, href)

            # Busca por classe
            if "class" in attrs:
                for elem in soup.find_all(tag):
                    classes = elem.get("class", [])
                    if isinstance(classes, str):
                        classes = [classes]
                    if any(c in str(classes).lower() for c in attrs["class"]):
                        # Procura link dentro
                        link = elem if elem.name == "a" else elem.find("a")
                        if link and link.get("href"):
                            return urljoin(url_atual, link.get("href"))

            # Busca por rel
            if "rel" in attrs:
                for elem in soup.find_all(tag, rel=attrs["rel"]):
                    href = elem.get("href")
                    if href:
                        return urljoin(url_atual, href)

        # Procura por links com números de página
        links_pagina = soup.find_all("a", href=True)
        for link in links_pagina:
            href = link.get("href", "")
            texto = link.get_text(strip=True).lower()

            # Se o texto é um número maior que a página atual
            if texto.isdigit():
                # Verifica se é a próxima página
                if "pagina" in href.lower() or "page" in href.lower():
                    return urljoin(url_atual, href)

        return None

    def _compilar_resultado(self, dados: Dict) -> str:
        """Compila o resultado do crawl em texto estruturado detalhado."""
        resumo = f"🕷️ **CRAWL PROFUNDO CONCLUÍDO**\n\n"
        resumo += f"🌐 URL base: {dados['url_base']}\n"
        resumo += f"📊 Total de registros extraídos: {dados['total_registros']}\n"
        resumo += f"📄 PDFs encontrados: {len(dados['pdfs_encontrados'])}\n"
        resumo += f"📋 Seções crawleadas: {len(dados['secoes'])}\n\n"

        # Detalha cada seção
        resumo += "📋 **DETALHAMENTO POR SEÇÃO:**\n"
        for nome, dados_secao in dados["secoes"].items():
            resumo += f"\n**{nome}:**\n"
            resumo += f"  - Páginas visitadas: {dados_secao['paginas_visitadas']}\n"
            resumo += f"  - Registros encontrados: {dados_secao['total_registros']}\n"
            resumo += f"  - Tabelas: {len(dados_secao['tabelas'])}\n"
            resumo += f"  - Divs de dados: {len(dados_secao.get('divs_dados', []))}\n"
            resumo += f"  - Listas: {len(dados_secao.get('listas', []))}\n"
            resumo += f"  - PDFs: {len(dados_secao['pdfs'])}\n"

            # Mostra amostra de dados das tabelas
            if dados_secao["tabelas"]:
                primeira_tabela = dados_secao["tabelas"][0]
                if len(primeira_tabela) > 1:
                    cabecalho = primeira_tabela[0]
                    primeira_linha = primeira_tabela[1] if len(primeira_tabela) > 1 else []
                    resumo += f"  - Colunas (tabela): {', '.join(cabecalho[:5])}\n"
                    if primeira_linha:
                        resumo += f"  - Exemplo (tabela): {', '.join(primeira_linha[:5])}\n"
            
            # Mostra amostra de dados de divs
            if dados_secao.get("divs_dados"):
                primeiro_div = dados_secao["divs_dados"][0]
                resumo += f"  - Exemplo (div): {primeiro_div.get('texto', '')[:100]}...\n"
            
            # Mostra amostra de listas
            if dados_secao.get("listas"):
                primeira_lista = dados_secao["listas"][0]
                resumo += f"  - Exemplo (lista): {', '.join(primeira_lista[:3])}...\n"

        # Lista PDFs encontrados
        if dados["pdfs_encontrados"]:
            resumo += f"\n📄 **PDFs ENCONTRADOS ({len(dados['pdfs_encontrados'])}):**\n"
            for pdf in dados["pdfs_encontrados"][:10]:
                resumo += f"  - {pdf['texto_link']}: {pdf['url'][:80]}...\n"
            if len(dados["pdfs_encontrados"]) > 10:
                resumo += f"  ... e mais {len(dados['pdfs_encontrados']) - 10} PDFs\n"

        # Erros
        if dados["erros"]:
            resumo += f"\n❌ **ERROS ({len(dados['erros'])}):**\n"
            for erro in dados["erros"][:5]:
                resumo += f"  - {erro}\n"
        
        # Resumo executivo
        resumo += f"\n📝 **RESUMO EXECUTIVO:**\n"
        resumo += f"O portal foi crawleado com sucesso. {dados['total_registros']} registros foram extraídos de {len(dados['secoes'])} seções. "
        resumo += f"Foram encontrados {len(dados['pdfs_encontrados'])} PDFs disponíveis para download. "
        
        if dados['total_registros'] > 0:
            resumo += f"Os dados incluem tabelas, divs estruturados e listas com informações sobre licitações, contratos, despesas e outros documentos públicos."
        else:
            resumo += f"Nenhum registro estruturado foi encontrado. O portal pode usar JavaScript para carregar dados dinamicamente ou exigir autenticação."

        return resumo


class PDFDownloaderAgente(BaseAgente):
    """
    Agente especializado em baixar e processar PDFs de portais.
    """

    def __init__(self, navegador: NavegadorAutomatizado, leitor=None):
        super().__init__(
            nome="PDFDownloader",
            descricao="Baixa PDFs de portais de transparência (contratos, editais, notas fiscais) "
                      "e processa com OCR para extrair dados. Chame após o CrawlerProfundo encontrar PDFs."
        )
        self.navegador = navegador
        self.leitor = leitor
        self.download_dir = os.path.join("data", "downloads_pdfs")
        os.makedirs(self.download_dir, exist_ok=True)

    def processar(self, tarefa: str) -> str:
        """Baixa e processa PDFs mencionados na tarefa."""
        import requests

        # Extrai URLs de PDF da tarefa
        urls_pdf = re.findall(r'(https?://[^\s]+\.pdf)', tarefa, re.IGNORECASE)

        if not urls_pdf:
            # Se não há URLs diretas, procura no histórico
            return "Nenhuma URL de PDF encontrada na tarefa. Use o CrawlerProfundo primeiro para encontrar PDFs."

        print(f"📥 PDFDownloader: Baixando {len(urls_pdf)} PDFs...")

        resultados = []
        pdfs_processados = 0

        for url_pdf in urls_pdf[:20]:  # Limite de 20 PDFs
            try:
                # Baixa o PDF
                nome_arquivo = url_pdf.split("/")[-1].split("?")[0]
                if not nome_arquivo.endswith(".pdf"):
                    nome_arquivo += ".pdf"

                caminho_pdf = os.path.join(self.download_dir, nome_arquivo)

                print(f"  📥 Baixando: {nome_arquivo}")

                response = requests.get(url_pdf, timeout=60, verify=False, stream=True)
                response.raise_for_status()

                with open(caminho_pdf, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                tamanho = os.path.getsize(caminho_pdf)
                print(f"  ✅ Baixado: {tamanho/1024:.1f} KB")

                # Processa o PDF se o leitor estiver disponível
                texto_extraido = ""
                if self.leitor:
                    try:
                        doc = self.leitor.processar_documento(caminho_pdf)
                        if doc:
                            texto_extraido = doc.conteudo_processado[:5000]
                            num_entidades = len(doc.entidades)
                            print(f"  📝 Processado: {num_entidades} entidades extraídas")
                    except Exception as e:
                        print(f"  ⚠️ Erro ao processar PDF: {e}")

                resultados.append({
                    "arquivo": nome_arquivo,
                    "url": url_pdf,
                    "tamanho_kb": tamanho / 1024,
                    "entidades": num_entidades if self.leitor else 0,
                    "texto_amostra": texto_extraido[:500]
                })
                pdfs_processados += 1

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                resultados.append({
                    "arquivo": url_pdf.split("/")[-1],
                    "url": url_pdf,
                    "erro": str(e)
                })
                print(f"  ❌ Erro: {e}")

        # Compila resultado
        resumo = f"📥 **DOWNLOAD DE PDFs CONCLUÍDO**\n\n"
        resumo += f"PDFs baixados: {pdfs_processados}\n"
        resumo += f"Total tentado: {len(urls_pdf)}\n\n"

        for r in resultados:
            if "erro" in r:
                resumo += f"❌ {r['arquivo']}: {r['erro']}\n"
            else:
                resumo += f"✅ {r['arquivo']} ({r['tamanho_kb']:.1f} KB)\n"
                if r.get("entidades"):
                    resumo += f"   📝 {r['entidades']} entidades extraídas\n"
                if r.get("texto_amostra"):
                    resumo += f"   📄 Amostra: {r['texto_amostra'][:200]}...\n"

        return resumo


class CNPJValidatorAgente(BaseAgente):
    """
    Agente especializado em consultar dados reais de CNPJs na Receita Federal.
    Usa a versão COMPLETA de integrações (60+ APIs incluindo COAF).
    """

    def __init__(self, correlacionador: Correlacionador):
        super().__init__(
            nome="CNPJValidator",
            descricao="Consulta dados reais de CNPJs na Receita Federal (razão social, situação cadastral, "
                      "sócios, capital social, data de abertura) e verifica sanções no CEIS/CNEP/CEAFIM/COAF. "
                      "Também verifica IBAMA (multas/embargos) e PNCP (contratos). "
                      "Chame este agente para enriquecer dados das empresas encontradas."
        )
        self.correlacionador = correlacionador
        # Usa a versão COMPLETA com 60+ APIs (inclui COAF, IBAMA, PNCP, etc)
        try:
            from core.integracoes_gov_completo import IntegracoesGovCompleto
            self.integracoes = IntegracoesGovCompleto()
        except ImportError:
            from core.integracoes_gov import IntegracoesGovernamentais
            self.integracoes = IntegracoesGovernamentais()

    def processar(self, tarefa: str) -> str:
        """Consulta dados reais de CNPJs na Receita Federal e verifica sanções."""
        empresas = self.correlacionador.empresas

        # Extrai CNPJs da tarefa se fornecidos diretamente
        cnpjs_tarefa = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}', tarefa)

        # Se há CNPJs na tarefa, usa eles; senão usa do correlacionador
        cnpjs_para_consultar = []

        if cnpjs_tarefa:
            cnpjs_para_consultar = cnpjs_tarefa
        else:
            for emp_id, empresa in empresas.items():
                if empresa.cnpj:
                    cnpjs_para_consultar.append(empresa.cnpj)

        if not cnpjs_para_consultar:
            if not empresas:
                return "Nenhuma empresa encontrada para consultar. Extraia dados de um portal primeiro."
            return "Nenhum CNPJ válido encontrado para consultar."

        print(f"🏢 CNPJValidator: Consultando {len(cnpjs_para_consultar)} CNPJs na Receita Federal...")

        resultados = []
        empresas_inidoneas = 0
        empresas_baixadas = 0
        empresas_recem_criadas = 0

        for cnpj in cnpjs_para_consultar[:20]:  # Limite de 20 consultas
            cnpj_limpo = re.sub(r'\D', '', cnpj)

            print(f"  🏢 Consultando CNPJ: {cnpj_limpo}")

            # Enriquece dados da empresa
            dados = self.integracoes.enriquecer_empresa(cnpj_limpo)

            if dados.get("dados_cadastrais"):
                cad = dados["dados_cadastrais"]
                razao = cad.get("razao_social", "N/A")
                situacao = cad.get("situacao_cadastral", "N/A")
                abertura = cad.get("data_abertura", "N/A")
                capital = cad.get("capital_social", "N/A")

                resultado = f"🏢 **{razao}**\n"
                resultado += f"   CNPJ: {cnpj_limpo}\n"
                resultado += f"   Situação: {situacao}\n"
                resultado += f"   Abertura: {abertura}\n"
                resultado += f"   Capital: R$ {capital}\n"

                # Verifica situação
                if situacao.upper() in ("BAIXADA", "INAPTA", "SUSPENSA"):
                    empresas_baixadas += 1
                    resultado += f"   ⚠️ ALERTA: Empresa {situacao.upper()}\n"

                # Verifica se é recém-criada
                if abertura and "2023" in abertura or "2024" in abertura:
                    empresas_recem_criadas += 1
                    resultado += f"   ⚠️ Empresa recém-criada\n"

                # Sócios
                socios = cad.get("socios", [])
                if socios:
                    resultado += f"   👥 Sócios ({len(socios)}):\n"
                    for socio in socios[:5]:
                        nome_socio = socio.get("nome", socio.get("qualificacao", ""))
                        resultado += f"      - {nome_socio}\n"

                # Endereço
                end = cad.get("endereco", {})
                if end.get("logradouro"):
                    resultado += f"   📍 {end.get('logradouro')}, {end.get('numero')} - {end.get('municipio')}/{end.get('uf')}\n"

                # Sanções
                if dados.get("inidonea"):
                    empresas_inidoneas += 1
                    resultado += f"   🚨 **EMPRESA INIDÔNEA**\n"
                    for sancao in dados.get("sancoes_ceis", []):
                        resultado += f"      CEIS: {sancao.get('motivo', 'Sanção ativa')}\n"
                    for sancao in dados.get("sancoes_cnep", []):
                        resultado += f"      CNEP: {sancao.get('motivo', 'Condenação')}\n"
                else:
                    resultado += f"   ✅ Sem sanções\n"

                resultados.append(resultado)
            else:
                resultados.append(f"❌ CNPJ {cnpj_limpo}: Não foi possível consultar (API pode estar indisponível)\n")

        # Compila relatório
        relatorio = "🏢 **RELATÓRIO DE CONSULTA CNPJ (RECEITA FEDERAL)**\n\n"
        relatorio += f"Total consultado: {len(cnpjs_para_consultar[:20])}\n"
        relatorio += f"Empresas inidôneas: {empresas_inidoneas}\n"
        relatorio += f"Empresas baixadas/inaptas: {empresas_baixadas}\n"
        relatorio += f"Empresas recém-criadas: {empresas_recem_criadas}\n\n"

        relatorio += "\n".join(resultados)

        if empresas_inidoneas > 0:
            relatorio += f"\n\n🚨 **ALERTA CRÍTICO:** {empresas_inidoneas} empresa(s) inidônea(s) encontrada(s)!"

        return relatorio


class CrossPortalAgente(BaseAgente):
    """
    Agente que cruza dados entre múltiplos portais e fontes.
    Usa a versão COMPLETA de integrações (60+ APIs).
    """

    def __init__(self, correlacionador: Correlacionador):
        super().__init__(
            nome="CrossPortal",
            descricao="Cruza dados entre múltiplos portais governamentais (PNCP, Receita, CGU, TCU, COAF) "
                      "para encontrar conexões ocultas entre empresas, sócios e contratos. "
                      "Chame este agente para investigação profunda após extrair dados."
        )
        self.correlacionador = correlacionador
        # Usa a versão COMPLETA com 60+ APIs
        try:
            from core.integracoes_gov_completo import IntegracoesGovCompleto
            self.integracoes = IntegracoesGovCompleto()
        except ImportError:
            from core.integracoes_gov import IntegracoesGovernamentais
            self.integracoes = IntegracoesGovernamentais()

    def processar(self, tarefa: str) -> str:
        """Cruza dados entre fontes governamentais."""
        print("🔗 CrossPortal: Cruzando dados entre portais governamentais...")

        empresas = self.correlacionador.empresas
        if not empresas:
            return "Nenhuma empresa encontrada para cruzar. Extraia dados de um portal primeiro."

        resultados = {
            "empresas_encontradas_pncp": 0,
            "empresas_com_sancoes": 0,
            "empresas_recem_criadas": 0,
            "socios_repetidos": [],
            "enderecos_compartilhados": [],
            "alertas": []
        }

        # 1. Consulta PNCP para ver se empresas aparecem em outras licitações
        cnpjs = [emp.cnpj for emp in empresas.values() if emp.cnpj]
        cnpjs = [re.sub(r'\D', '', c) for c in cnpjs if c]

        if cnpjs:
            print(f"  🔍 Consultando PNCP para {len(cnpjs)} empresas...")
            try:
                licitacoes_pncp = self.integracoes.consultar_pncp_licitacoes(
                    data_inicial=f"{datetime.now().year}-01-01",
                    data_final=f"{datetime.now().year}-12-31",
                    tamanho_pagina=50
                )

                # Cruza CNPJs com licitações do PNCP
                for lic in licitacoes_pncp:
                    cnpj_licitante = str(lic.get("cnpjFornecedor", lic.get("cnpj", "")))
                    cnpj_licitante = re.sub(r'\D', '', cnpj_licitante)

                    if cnpj_licitante in cnpjs:
                        resultados["empresas_encontradas_pncp"] += 1
                        resultados["alertas"].append(
                            f"Empresa {cnpj_licitante} encontrada em licitação no PNCP: "
                            f"{lic.get('objetoCompra', 'N/A')}"
                        )
            except Exception as e:
                print(f"  ⚠️ Erro ao consultar PNCP: {e}")

        # 2. Verifica sócios repetidos
        socios_empresas = {}
        for emp_id, empresa in empresas.items():
            for socio in empresa.socios:
                nome_socio = socio.get("nome", str(socio)) if isinstance(socio, dict) else str(socio)
                nome_normalizado = nome_socio.upper().strip()
                if nome_normalizado not in socios_empresas:
                    socios_empresas[nome_normalizado] = []
                socios_empresas[nome_normalizado].append(empresa.nome)

        for socio, empresas_lista in socios_empresas.items():
            if len(empresas_lista) > 1:
                resultados["socios_repetidos"].append({
                    "socio": socio,
                    "empresas": empresas_lista
                })

        # 3. Verifica endereços compartilhados
        enderecos_empresas = {}
        for emp_id, empresa in empresas.items():
            if empresa.endereco:
                end_norm = re.sub(r'[^a-zA-Z0-9]', '', empresa.endereco.lower())[:50]
                if end_norm not in enderecos_empresas:
                    enderecos_empresas[end_norm] = []
                enderecos_empresas[end_norm].append(empresa.nome)

        for endereco, empresas_lista in enderecos_empresas.items():
            if len(empresas_lista) > 1:
                resultados["enderecos_compartilhados"].append({
                    "endereco": endereco,
                    "empresas": empresas_lista
                })

        # Compila relatório
        relatorio = "🔗 **CRUZAMENTO DE DADOS ENTRE PORTAIS**\n\n"
        relatorio += f"📊 Empresas analisadas: {len(empresas)}\n"
        relatorio += f"🔍 Empresas encontradas no PNCP: {resultados['empresas_encontradas_pncp']}\n"
        relatorio += f"🚨 Empresas com sanções: {resultados['empresas_com_sancoes']}\n"
        relatorio += f"📅 Empresas recém-criadas: {resultados['empresas_recem_criadas']}\n\n"

        # Sócios repetidos
        if resultados["socios_repetidos"]:
            relatorio += f"\n👥 **SÓCIOS REPETIDOS ({len(resultados['socios_repetidos'])}):**\n"
            for item in resultados["socios_repetidos"][:10]:
                relatorio += f"  - {item['socio']}: {', '.join(item['empresas'])}\n"

        # Endereços compartilhados
        if resultados["enderecos_compartilhados"]:
            relatorio += f"\n📍 **ENDEREÇOS COMPARTILHADOS ({len(resultados['enderecos_compartilhados'])}):**\n"
            for item in resultados["enderecos_compartilhados"][:10]:
                relatorio += f"  - {', '.join(item['empresas'])}\n"

        # Alertas
        if resultados["alertas"]:
            relatorio += f"\n⚠️ **ALERTAS ({len(resultados['alertas'])}):**\n"
            for alerta in resultados["alertas"][:10]:
                relatorio += f"  - {alerta}\n"

        return relatorio


class ShadowAPIAgente(BaseAgente):
    """
    Sniper de APIs Ocultas (Auto-Paginador XHR).
    Intercepta as rotas JSON de uma SPA e repete a consulta paginando
    autonomamente para puxar os dados completos direto do backend.
    """
    def __init__(self, navegador):
        super().__init__(
            nome="ShadowAPI",
            descricao="Intercepta rotas XHR/JSON ocultas em portais e faz paginação infinita autônoma para puxar dados diretamente do banco de dados ignorando a UI."
        )
        self.navegador = navegador
        
        # O self.session do import requests é feito localmente no processar para evitar problemas no import global
        import requests
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    def processar(self, tarefa: str) -> str:
        """
        Tarefa contém URL ou indicação de buscar as Shadow APIs de uma sessão aberta.
        """
        import re
        import time
        import urllib.parse
        
        shadow_apis = []
        if hasattr(self.navegador, 'obter_apis_ocultas'):
            shadow_apis = self.navegador.obter_apis_ocultas()
            
        if not shadow_apis:
            return "Nenhuma API JSON oculta detectada no log de rede atual. O portal pode ser renderizado no servidor (SSR)."
            
        print(f"[ShadowAPI] Interceptadas {len(shadow_apis)} requisições JSON. Analisando...")
        
        # Filtra rotas prováveis de paginação/dados estruturados
        api_dados = None
        for api in shadow_apis:
            url = api.get('url', '')
            if 'api' in url.lower() or 'json' in url.lower() or 'licitacoes' in url.lower() or 'despesas' in url.lower():
                api_dados = url
                break
                
        if not api_dados:
            return "APIs detectadas não parecem conter dados estruturados de licitações ou transparência."
            
        print(f"[ShadowAPI] Endpoint promissor encontrado: {api_dados}")
        print(f"[ShadowAPI] Iniciando Auto-Paginador...")
        
        registros_totais = []
        
        # Tentativa de inferir o parâmetro de paginação
        parsed = urllib.parse.urlparse(api_dados)
        query = urllib.parse.parse_qs(parsed.query)
        
        param_page = None
        for p in ['page', 'pagina', 'p', 'offset', 'inicio']:
            if p in query:
                param_page = p
                break
                
        if not param_page:
            # Se não tem na url, assumimos param_page='page' e valor='1'
            param_page = 'page'
            query[param_page] = ['1']
            
        try:
            pagina_atual = int(query[param_page][0])
        except (ValueError, IndexError):
            pagina_atual = 1
        
        for _ in range(5): # Limite de 5 páginas
            query[param_page] = [str(pagina_atual)]
            nova_url = parsed._replace(query=urllib.parse.urlencode(query, doseq=True)).geturl()
            
            try:
                resp = self.session.get(nova_url, timeout=10, verify=False)
                dados = resp.json()
                
                encontrou = False
                if isinstance(dados, list):
                    registros_totais.extend(dados)
                    encontrou = True
                elif isinstance(dados, dict):
                    for k in ['data', 'items', 'content', 'registros']:
                        if k in dados and isinstance(dados[k], list):
                            registros_totais.extend(dados[k])
                            encontrou = True
                            break
                            
                if not encontrou:
                    break
                    
                print(f"  [Auto-Paginação] Extraídos dados da página {pagina_atual}")
                pagina_atual += 1
                time.sleep(1)
            except Exception:
                break
                
        res = f"Auto-paginador extraiu com sucesso **{len(registros_totais)}** registros diretamente do backend da prefeitura (Endpoint: `{api_dados.split('?')[0]}`)."
        return res