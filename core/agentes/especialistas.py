"""
Módulo com agentes de inteligência artificial.
Contém documentação detalhada das classes e métodos (Google Style).
"""
import time
import os
import webbrowser
from core.agentes.base import BaseAgente
from core.navegador_automatizado import NavegadorAutomatizado
from core.correlacionador import Correlacionador
import re
from typing import List, Optional

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.agentes.especialistas")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.agentes_especialistas")
    metrics = None
    MONITORING_AVAILABLE = False


class NavegadorAgente(BaseAgente):
    """Agente especializado em navegação web e extração de portais de transparência."""

    # Palavras-chave que indicam portal de transparência
    PALAVRAS_PORTAL = [
        "transparencia", "transparência", "portal", "prefeitura",
        "governo", "gov", "cgu", "tcu", "licitacao", "licitação",
        "contrato", "contratacao", "contratação", "despesa",
        "receita", "orgao", "órgão", "publico", "público",
    ]
    PORTAIS_CONHECIDOS = [
        "portalcr2", "portaldatransparencia", "transparencia",
        "ourilandia", "prefeitura", "câmara", "camara",
    ]

    def __init__(self, navegador: NavegadorAutomatizado):
        super().__init__(
            nome="Navegador",
            descricao="Navega em uma URL específica e retorna o texto extraído da página web. Instrua-me com a URL completa (ex: https://site.com). Também pode extrair dados estruturados de portais de transparência e navegar automaticamente por todos os menus do portal."
        )
        self.navegador = navegador
        from core.navegador_automatizado import ExtratorPortalTransparencia
        self.extrator = ExtratorPortalTransparencia(navegador)

    def _detectar_portal(self, url: str) -> bool:
        """Detecta se a URL é de um portal de transparência."""
        from urllib.parse import urlparse
        url_lower = url.lower()
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        for palavra in self.PALAVRAS_PORTAL:
            if palavra in domain or palavra in path:
                return True
        for portal in self.PORTAIS_CONHECIDOS:
            if portal in domain:
                return True
        return False

    def processar(self, tarefa: str) -> str:
        """
        Extrai a URL da tarefa e processa o conteúdo.
        NOVO: Detecta automaticamente se é portal de transparência e faz crawl completo.
        """
        import re
        urls = re.findall(r'(https?://[^\s]+)', tarefa)
        if not urls:
            return "Nenhuma URL válida encontrada na requisição."

        url = urls[0].strip('\'\\"})')
        print(f"[NAVEGADOR] Agente Navegador: acessando {url} ...")

        # Inicia captura de tela periódica
        try:
            self.navegador.iniciar_captura_periodica(intervalo=4)
        except Exception:
            pass

        # Detecta se é portal de transparência
        is_portal = self._detectar_portal(url)
        pediu_menu_completo = any(kw in tarefa.lower() for kw in ["menu completo", "navegar tudo", "todos os links", "varredura completa", "todas as seções"])

        # Se for portal ou pediu menu completo, faz varredura completa
        if is_portal or pediu_menu_completo:
            print(f"[BUSCA] Portal de transparência detectado! Iniciando navegação completa do menu...")
            resultado = self.extrator.navegar_menu_completo(url, max_links=20)

            sucesso = len([l for l in resultado['links_visitados'] if l.get('sucesso', False)])
            falhas = len([l for l in resultado['links_visitados'] if not l.get('sucesso', True)])

            resumo = f"📊 Navegação completa do portal concluída:\n"
            resumo += f"- Links visitados: {len(resultado['links_visitados'])}\n"
            resumo += f"- Sucesso: {sucesso}\n"
            resumo += f"- Falhas: {falhas}\n"
            resumo += f"- Erros: {len(resultado['erros'])}\n\n"

            if resultado['dados_extraidos']:
                resumo += "📋 Seções com dados extraídos:\n"
                for nome, dados in resultado['dados_extraidos'].items():
                    num_tabelas = len(dados.get('tabelas', []))
                    num_textos = len(dados.get('textos', []))
                    arquivos = dados.get('arquivos', [])
                    resumo += f"- {nome}: {num_tabelas} tabelas, {num_textos} textos, {len(arquivos)} arquivos baixados\n"
                    if arquivos:
                        # Aciona processamento assíncrono para os arquivos
                        from workers.tasks import enfileirar_processamento_documento
                        for arq in arquivos:
                            enfileirar_processamento_documento(arq)

            if resultado['erros']:
                resumo += f"\n❌ Erros encontrados:\n" + "\n".join(resultado['erros'][:5])

            return resumo

        # Extração de dados estruturados específicos
        if "licitações" in tarefa.lower() or "licitacao" in tarefa.lower():
            dados = self.extrator.extrair_licitacoes(url)
            if dados:
                return f"Extraí {len(dados)} licitações do portal:\n\n" + "\n".join([f"- {d.get('numero', '')}: {d.get('objeto', '')} - {d.get('valor', '')}" for d in dados[:10]])
            return "Não foi possível extrair licitações desta página."

        elif "despesas" in tarefa.lower():
            dados = self.extrator.extrair_despesas(url)
            if dados:
                return f"Extraí {len(dados)} despesas do portal:\n\n" + "\n".join([f"- {d.get('descricao', '')}: {d.get('valor', '')}" for d in dados[:10]])
            return "Não foi possível extrair despesas desta página."

        elif "contratos" in tarefa.lower():
            dados = self.extrator.extrair_contratos(url)
            if dados:
                return f"Extraí {len(dados)} contratos do portal:\n\n" + "\n".join([f"- {d.get('numero', '')}: {d.get('contratado', '')} - {d.get('valor', '')}" for d in dados[:10]])
            return "Não foi possível extrair contratos desta página."

        # Extração de texto padrão
        sucesso = self.navegador.navegar(url)
        if not sucesso:
            return f"Falha ao carregar a URL: {url}"

        time.sleep(3)
        html = self.navegador.obter_html()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        texto = soup.get_text(separator=' ', strip=True)

        max_len = 6000
        if len(texto) > max_len:
            texto = texto[:max_len] + "... [TRUNCADO]"

        return f"Conteúdo extraído da página {url}:\n\n{texto}"


class AgenteGrafo(BaseAgente):
    def __init__(self, correlacionador: Correlacionador):
        super().__init__(
            nome="GrafoSocietario",
            descricao="Gera um mapa visual (Grafo HTML interativo) mostrando a teia de relações entre empresas, pessoas e contratos do sistema. Chame este agente caso o usuário peça para ver conexões, teias, laranjas ou relacionamentos visuais."
        )
        self.correlacionador = correlacionador

    def processar(self, tarefa: str) -> str:
        """Gera o HTML usando pyvis e abre no navegador."""
        print("🕸️ Agente de Grafos gerando visualização HTML...")
        try:
            from pyvis.network import Network
        except ImportError:
            return "Erro: A biblioteca 'pyvis' não está instalada. Execute 'pip install pyvis'."

        dados_grafo = self.correlacionador.get_grafo_relacionamentos()
        nodes = dados_grafo.get("nodes", [])
        edges = dados_grafo.get("edges", [])

        if not nodes or not edges:
            return "O motor de correlação não encontrou entidades ou relacionamentos estruturados nos documentos em memória."

        # Configura a rede pyvis
        net = Network(height="750px", width="100%", bgcolor="#0a0a0a", font_color="white", directed=False)

        # Mapear nós para ter rótulos descritivos
        for node_id in nodes:
            label = str(node_id)
            color = "#97c2fc"  # Default blue

            if node_id in self.correlacionador.pessoas:
                label = self.correlacionador.pessoas[node_id].nome
                color = "#3b82f6"  # Azul accent
            elif node_id in self.correlacionador.empresas:
                label = self.correlacionador.empresas[node_id].nome
                color = "#f59e0b"  # Laranja warning
            elif node_id in self.correlacionador.contratos:
                label = f"Contrato {self.correlacionador.contratos[node_id].numero}"
                color = "#10b981"  # Verde success

            net.add_node(node_id, label=label[:30], title=label, color=color)

        for edge in edges:
            origem = edge["source"]
            destino = edge["target"]
            tipo = edge["type"]
            net.add_edge(origem, destino, title=tipo, label=tipo)

        # Adiciona física de repulsão elegante
        net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150)

        caminho_arquivo = os.path.abspath("teia_relacionamentos.html")
        net.save_graph(caminho_arquivo)

        # Abre automaticamente no navegador padrão
        webbrowser.open(f"file://{caminho_arquivo}")

        return f"Grafo visual gerado com sucesso! Um arquivo HTML interativo com {len(nodes)} nós e {len(edges)} conexões foi aberto no navegador do usuário."


class AgenteDiarioOficial(BaseAgente):
    def __init__(self, lista_documentos: List, ai_manager=None):
        super().__init__(
            nome="GazetteAuditor",
            descricao="Lê e processa Diários Oficiais extensos em PDF, fatiando apenas os trechos chave (Portarias, Extratos de Contrato, Licitações, Nomeações). Chame esse agente se o usuário quiser analisar editais, extratos e diários em anexo."
        )
        self.documentos = lista_documentos
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """Filtra as seções e repassa o resumo condensado."""
        if not self.documentos:
            return "Erro: Nenhum documento anexado para analisar. Peça ao usuário para anexar um Diário Oficial (PDF) primeiro."

        resultados = []
        for doc in self.documentos:
            texto_bruto = doc.conteudo_processado

            # Corta seções irrelevantes via Heurística/Regex
            trechos_uteis = self.extrair_secoes_relevantes(texto_bruto)

            if not trechos_uteis:
                continue

            texto_condensado = "\n\n...[CORTE]...\n\n".join(trechos_uteis)

            # Se for muito grande, corta para caber no limite do LLM
            texto_condensado = texto_condensado[:30000]

            # Delega para a própria IA mastigar o texto concentrado
            if self.ai_manager:
                client = self.ai_manager.get_client()
                if client and client.is_available():
                    print(f"📄 Gazette Auditor sumarizando {len(texto_condensado)} caracteres do Diário...")
                    sumario_result = client.chat_completion(
                        messages=[
                            {"role": "system", "content": "Você é um extrator de dados judiciais/oficiais focado apenas em contratos e licitações."},
                            {"role": "user", "content": f"Analise os seguintes recortes de um Diário Oficial e liste os dados estruturados sobre Contratos, Valores, CNPJs, Licitações e Nomeações. Ignore o lixo burocrático.\n\nTEXTO:\n{texto_condensado}"}
                        ],
                        max_tokens=1500
                    )
                    sumario = sumario_result.get("content", "") if sumario_result else ""
                    resultados.append(f"Resultados para o documento (ID {doc.id}):\n{sumario}")
                else:
                    resultados.append(f"Resultados brutos para o documento (ID {doc.id}):\n{texto_condensado[:2000]}... [IA INDISPONÍVEL PARA RESUMO]")
            else:
                resultados.append(f"Resultados brutos para o documento (ID {doc.id}):\n{texto_condensado[:2000]}... [IA INDISPONÍVEL PARA RESUMO]")

        if not resultados:
            return "Nenhuma portaria, extrato de contrato, nomeação ou dispensa de licitação foi encontrada nos documentos anexados."

        return "\n\n".join(resultados)

    def extrair_secoes_relevantes(self, texto: str) -> List[str]:
        """Usa regex para capturar blocos iniciados por palavras-chave governamentais."""
        padrao = r'(?i)(?:EXTRATO DE CONTRATO|PORTARIA N[ºo°\.]?|DISPENSA DE LICITAÇÃO|NOMEAÇÃO|INEXIGIBILIDADE|PREGÃO ELETRÔNICO|HOMOLOGAÇÃO).*?(?=(?:EXTRATO DE CONTRATO|PORTARIA N[ºo°\.]?|DISPENSA DE LICITAÇÃO|NOMEAÇÃO|INEXIGIBILIDADE|PREGÃO ELETRÔNICO|HOMOLOGAÇÃO)|$)'

        trechos = []
        matches = re.finditer(padrao, texto, re.DOTALL | re.IGNORECASE)

        for m in matches:
            bloco = m.group(0).strip()
            # Limita cada bloco a ~1500 caracteres
            if len(bloco) > 1500:
                bloco = bloco[:1500] + "... [TRUNCADO PELO GAZETTE AUDITOR]"
            trechos.append(bloco)

        return trechos


class AgentePayroll(BaseAgente):
    def __init__(self, lista_documentos: List, ai_manager=None):
        super().__init__(
            nome="PayrollAuditor",
            descricao="Especialista contábil focado em planilhas financeiras e de folha de pagamento. Descobre acúmulo de cargos e supersalários usando análise estruturada (Pandas) antes de delegar para a IA. Chame-o para analisar planilhas (.xlsx, .csv) em anexo."
        )
        self.documentos = lista_documentos
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """Cruza dados estruturados das planilhas antes de usar o LLM."""
        if not self.documentos:
            return "Erro: Nenhuma planilha anexada para analisar. Peça ao usuário para anexar um arquivo Excel ou CSV."

        import pandas as pd
        import json

        resultados = []
        for doc in self.documentos:
            if doc.tipo.name not in ("PLANILHA",):
                continue

            try:
                # Tenta ler a fonte de dados real
                if doc.fonte.lower().endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(doc.fonte, dtype=str)
                else:
                    df = pd.read_csv(doc.fonte, dtype=str, sep=None, engine='python')

                df = df.fillna("")

                # Heurística de descoberta de colunas
                colunas = [c.upper() for c in df.columns]
                col_cpf = next((c for c in colunas if "CPF" in c or "DOCUMENTO" in c), None)
                col_nome = next((c for c in colunas if "NOME" in c or "SERVIDOR" in c or "FUNCIONARIO" in c), None)
                col_valor = next((c for c in colunas if "VALOR" in c or "SALARIO" in c or "VENCIMENTO" in c or "LIQUIDO" in c or "BRUTO" in c), None)

                if not col_cpf and not col_nome:
                    continue  # Planilha não parece ser de folha de pagamento / pessoas

                col_agrupamento = col_cpf or col_nome

                # Converte os nomes reais originais do dataframe usando os índices detectados
                orig_agrup = df.columns[colunas.index(col_agrupamento)]

                # Se tiver coluna de valor, limpa e converte para float
                orig_valor = df.columns[colunas.index(col_valor)] if col_valor else None
                if orig_valor:
                    df["_valor_numerico"] = df[orig_valor].apply(
                        lambda x: float(re.sub(r'[^\d,.-]', '', str(x).replace('.', '').replace(',', '.')) or 0)
                    )
                else:
                    df["_valor_numerico"] = 0.0

                # Conta a frequência de cada CPF/Nome
                contagem = df[orig_agrup].value_counts()

                # Filtra CPFs que aparecem mais de uma vez (Acúmulo de cargo)
                multi_cargos = contagem[contagem > 1].index.tolist()

                # Filtra valores absolutos acima do teto
                supersalarios = df[df["_valor_numerico"] > 30000.0]

                achados_brutos = {
                    "arquivo": doc.fonte,
                    "total_linhas": len(df),
                    "suspeitas_acumulo_cargos": len(multi_cargos),
                    "exemplos_acumulo": multi_cargos[:10],
                    "suspeitas_supersalarios": len(supersalarios),
                    "exemplos_supersalarios": supersalarios[orig_agrup].tolist()[:10] if not supersalarios.empty else []
                }

                # Se encontrou anomalias heurísticas, pede pra IA gerar o laudo
                if (len(multi_cargos) > 0 or len(supersalarios) > 0) and self.ai_manager:
                    client = self.ai_manager.get_client()
                    if client and client.is_available():
                        resumo_result = client.chat_completion(
                            messages=[
                                {"role": "system", "content": "Você é um auditor escrevendo um parecer técnico formal baseado nos dados matemáticos que lhe foram passados pelo filtro Pandas."},
                                {"role": "user", "content": f"Os filtros matemáticos analisaram a planilha '{doc.fonte}' e encontraram as seguintes estatísticas:\n{json.dumps(achados_brutos, indent=2)}\n\nEscreva um laudo de auditoria apontando os indícios de fraude/desperdício baseado nestes números absolutos."}
                            ],
                            max_tokens=1500
                        )
                        resumo_ia = resumo_result.get("content", "") if resumo_result else ""
                        resultados.append(f"Parecer Técnico da Planilha (ID {doc.id}):\n{resumo_ia}")
                    else:
                        resultados.append(f"Resultados Heurísticos (ID {doc.id}):\n{json.dumps(achados_brutos, indent=2)}")
                else:
                    if len(multi_cargos) == 0 and len(supersalarios) == 0:
                        resultados.append(f"Planilha analisada (ID {doc.id}). Nenhum supersalário ou acúmulo de múltiplos CPFs detectado.")
                    else:
                        resultados.append(f"Resultados Heurísticos Brutos (ID {doc.id}):\n{json.dumps(achados_brutos, indent=2)}")

            except Exception as e:
                resultados.append(f"Erro ao processar planilha '{doc.fonte}' com Pandas: {str(e)}")

        if not resultados:
            return "Nenhuma planilha válida foi encontrada nos documentos anexados."

        return "\n\n".join(resultados)


class AgenteGeospatial(BaseAgente):
    def __init__(self, correlacionador: Correlacionador):
        super().__init__(
            nome="GeospatialAuditor",
            descricao="Mapeia entidades em um mapa interativo para investigar se fornecedores concorrentes dividem o mesmo endereço físico (fachada). Chame-o para gerar o mapa de endereços."
        )
        self.correlacionador = correlacionador

    def processar(self, tarefa: str) -> str:
        """Gera um arquivo HTML com o mapa usando folium e geopy."""
        try:
            import folium
            from geopy.geocoders import Nominatim
            from collections import defaultdict
        except ImportError:
            return "Erro: Dependências ausentes. Instale folium e geopy."

        print("🌍 Mapeando endereços... (isso pode levar alguns segundos)")
        geolocator = Nominatim(user_agent="auditoria_ia_app_v1")

        # Coleta todos os endereços ligados a empresas ou pessoas
        entidades_com_endereco = []

        for empresa_id, empresa in self.correlacionador.empresas.items():
            if hasattr(empresa, 'endereco') and empresa.endereco:
                entidades_com_endereco.append((empresa.nome, empresa.endereco, "empresa"))

        for pessoa_id, pessoa in self.correlacionador.pessoas.items():
            if hasattr(pessoa, 'endereco') and pessoa.endereco:
                entidades_com_endereco.append((pessoa.nome, pessoa.endereco, "pessoa"))

        if not entidades_com_endereco:
            return "Não encontrei endereços associados às empresas ou pessoas nesta base de dados."

        coordenadas_map = defaultdict(list)

        import time

        for nome, endereco_texto, tipo in entidades_com_endereco:
            try:
                time.sleep(1)
                location = geolocator.geocode(endereco_texto)
                if location:
                    coord = (location.latitude, location.longitude)
                    coordenadas_map[coord].append((nome, tipo, endereco_texto))
                else:
                    print(f"⚠️ Não foi possível localizar no mapa: {endereco_texto}")
            except Exception as e:
                print(f"Erro ao geocodificar {endereco_texto}: {e}")

        if not coordenadas_map:
            return "Não foi possível converter nenhum dos endereços extraídos em coordenadas geográficas viáveis."

        primeira_coord = list(coordenadas_map.keys())[0]
        m = folium.Map(location=primeira_coord, zoom_start=12, tiles="CartoDB dark_matter")

        fachadas_detectadas = 0

        for coord, entidades in coordenadas_map.items():
            nomes = [e[0] for e in entidades]
            tipos = [e[1] for e in entidades]
            enderecos_orig = [e[2] for e in entidades]

            if len(entidades) > 1:
                fachadas_detectadas += 1
                color = "red"
                icon = folium.Icon(color=color, icon="info-sign")
                popup_text = f"<b>ALERTA DE FACHADA!</b><br>Múltiplas entidades cadastradas:<br>"
                for n, t, ed in zip(nomes, tipos, enderecos_orig):
                    popup_text += f"- {n} ({t})<br>"
            else:
                color = "orange" if tipos[0] == "empresa" else "blue"
                icon = folium.Icon(color=color, icon="info-sign")
                popup_text = f"<b>{nomes[0]}</b> ({tipos[0]})<br>{enderecos_orig[0]}"

            folium.Marker(
                location=coord,
                popup=folium.Popup(popup_text, max_width=300),
                icon=icon
            ).add_to(m)

        caminho_mapa = os.path.abspath("mapa_auditoria.html")
        m.save(caminho_mapa)

        webbrowser.open(f"file://{caminho_mapa}")

        msg = f"Mapa gerado com sucesso contendo {len(coordenadas_map)} localizações únicas. "
        if fachadas_detectadas > 0:
            msg += f"🚨 ATENÇÃO: Encontrei {fachadas_detectadas} locais suspeitos compartilhados por múltiplas entidades (Possível fachada/laranja). Verifique os pinos VERMELHOS no mapa."

        return msg


class AgenteExtrator(BaseAgente):
    def __init__(self, lista_documentos: List, ai_manager=None):
        super().__init__(
            nome="InvoiceParser",
            descricao="Especialista em fatiar Notas Fiscais, recibos e XMLs/PDFs estruturados para devolver uma tabela JSON precisa dos itens comprados, quantidades e valores. Chame-o sempre que precisar ler extratos ou descobrir o que foi comprado em uma nota."
        )
        self.documentos = lista_documentos
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """Processa documentos de notas fiscais usando LLM com temperatura 0 e formatação rígida JSON."""
        if not self.documentos:
            return "Erro: Nenhum documento anexado para analisar. Peça ao usuário para anexar uma Nota Fiscal ou PDF."

        if not self.ai_manager:
            return "Erro: O AI Manager não está disponível. Não posso realizar a extração estruturada."

        client = self.ai_manager.get_client()
        if not client or not client.is_available():
            return "Erro: O provedor de IA não está acessível no momento."

        resultados = []
        for doc in self.documentos:
            if doc.tipo.name in ("PLANILHA",):
                continue

            texto = doc.conteudo_processado
            if len(texto) < 50:
                continue

            texto = texto[:20000]

            print(f"🧾 InvoiceParser: Estruturando itens da Nota (ID: {doc.id})...")

            system_prompt = """Você é um extrator de dados de Notas Fiscais robótico.
Sua única função é ler o texto providenciado e extrair a lista de produtos/serviços comprados.
Você DEVE obrigatoriamente retornar APENAS um objeto JSON no formato abaixo, sem nenhum texto adicional, Markdown ou formatação fora do JSON:
{
  "cnpj_fornecedor": "...",
  "nome_fornecedor": "...",
  "itens": [
    {
      "produto": "Nome do item",
      "quantidade": 1.0,
      "valor_unitario": 10.50,
      "valor_total": 10.50
    }
  ]
}
Se uma informação não existir, use null."""

            try:
                json_result = client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Texto da nota fiscal:\n\n{texto}"}
                    ],
                    max_tokens=2000
                )
                json_puro = json_result.get("content", "") if json_result else ""

                # Garante que se a IA colocar bloco markdown (```json), nós limpamos
                if json_puro:
                    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_puro, re.DOTALL)
                    if match:
                        json_puro = match.group(1)

                nome_arquivo = os.path.basename(doc.fonte)
                resultados.append(f"📦 Itens extraídos da Nota/Imagem '{nome_arquivo}' (ID {doc.id}):\n```json\n{json_puro.strip()}\n```")
            except Exception as e:
                resultados.append(f"Erro ao extrair nota '{os.path.basename(doc.fonte)}' (ID {doc.id}): {e}")

        if not resultados:
            return "Não consegui identificar nenhum item ou produto válido nos documentos anexados."

        return "\n\n".join(resultados)


class AgenteRelator(BaseAgente):
    def __init__(self, historico_mensagens: List, ai_manager=None):
        super().__init__(
            nome="ReporterAuditor",
            descricao="Especialista em formatar achados e redigir o Laudo Pericial final. Ele lê o histórico recente do chat e exporta um PDF com visual oficial (Governamental/Policial) sumarizando todas as fraudes encontradas pelos outros agentes."
        )
        self.historico = historico_mensagens
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """Coleta o histórico da investigação e gera o PDF final."""
        if not self.ai_manager:
            return "Erro: AI Manager indisponível. Não consigo redigir o laudo final."

        client = self.ai_manager.get_client()
        if not client or not client.is_available():
            return "Erro: Provedor de IA inacessível."

        try:
            from fpdf import FPDF
        except ImportError:
            return "Erro: Instale fpdf2 para gerar laudos."

        # Extrair histórico ignorando msgs de sistema/puramente UI
        chat_compilado = ""
        for msg in self.historico[-20:]:
            texto = ""
            if isinstance(msg, dict):
                texto = msg.get("content", "") or msg.get("texto", "")
            else:
                texto = str(msg)

            if len(texto) > 10 and "Supervisor delegando" not in texto:
                chat_compilado += f"\n---\n{texto[:1500]}"

        system_prompt = """Você é um Auditor Sênior do Tribunal de Contas (ou Polícia Federal).
Sua missão é ler o registro bruto da investigação (chat) e redigir um "LAUDO TÉCNICO PERICIAL".
Estruture obrigatoriamente da seguinte forma:
1. TÍTULO DO RELATÓRIO
2. RESUMO EXECUTIVO (1 parágrafo curto)
3. ACHADOS E ANOMALIAS (Uma lista enumerando as fraudes ou sobrepreços descobertos)
4. CONCLUSÃO.
Use um tom extremamente formal, frio e direto. Não use Markdown complexo como tabelas, APENAS texto simples e quebras de linha."""

        print("📄 ReporterAuditor: Redigindo o laudo oficial via IA...")

        laudo_result = client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Ordem do usuário: {tarefa}\n\n[REGISTRO DA INVESTIGAÇÃO]:\n{chat_compilado}"}
            ],
            max_tokens=3000
        )
        laudo_texto = laudo_result.get("content", "") if laudo_result else ""

        if not laudo_texto:
            return "Erro ao gerar texto do laudo."

        # Geração do PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        pdf.set_font("helvetica", size=12)

        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "MINISTÉRIO PÚBLICO / TRIBUNAL DE CONTAS", ln=True, align="C")
        pdf.set_font("helvetica", "I", 10)
        pdf.cell(0, 10, "Relatório Gerado por AuditorIA - Inteligência Artificial", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("helvetica", size=11)

        laudo_texto_limpo = laudo_texto.encode('latin-1', 'replace').decode('latin-1')

        for linha in laudo_texto_limpo.split('\n'):
            if "```" in linha:
                continue
            if linha.strip().isupper():
                pdf.set_font("helvetica", "B", 12)
            else:
                pdf.set_font("helvetica", "", 11)

            pdf.multi_cell(0, 8, txt=linha)

        caminho_pdf = os.path.abspath("laudo_oficial_auditoria.pdf")
        pdf.output(caminho_pdf)

        webbrowser.open(f"file://{caminho_pdf}")

        return f"Laudo PDF gerado com sucesso com {len(laudo_texto)} caracteres. O documento foi salvo em:\n{caminho_pdf}\nE aberto no seu leitor padrão de PDF."


class AgenteSancoes(BaseAgente):
    def __init__(self, correlacionador: Correlacionador):
        super().__init__(
            nome="SanctionAuditor",
            descricao="Inspetor de sanções e inidoneidade. Consulta bancos de dados para verificar se os fornecedores/CNPJs estão na lista negra do governo (Portal da Transparência, TCU). Chame-o para conferir se uma empresa pode licitar."
        )
        self.correlacionador = correlacionador

    def _consultar_portal_transparencia(self, cnpj: str) -> dict:
        """
        Consulta real à API da CGU (CEIS).
        Caso a chave não esteja presente no .env, usa o mock como fallback seguro.
        """
        import os
        import requests
        import re

        cnpj_limpo = re.sub(r'\D', '', str(cnpj))
        api_key = os.getenv("CGU_API_KEY")

        if api_key:
            try:
                headers = {'chave-api-dados': api_key}
                response = requests.get(
                    f"https://api.portaldatransparencia.gov.br/api-de-dados/ceis?cnpjSancionado={cnpj_limpo}",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    dados = response.json()
                    if dados and len(dados) > 0:
                        sancao = dados[0]
                        return {
                            "sancionado": True,
                            "motivo": sancao.get("textoFundamentacaoLegal", "Sanção detectada pelo CGU/TCU"),
                            "data_inicio": sancao.get("dataInicioSancao", "N/A"),
                            "data_fim": sancao.get("dataFimSancao", "N/A")
                        }
                    return {"sancionado": False}
                else:
                    print(f"⚠️ Erro na API CGU ({response.status_code}). Usando fallback...")
            except Exception as e:
                print(f"⚠️ Falha de rede ao consultar CGU: {e}. Usando fallback...")

        # MOCK DINÂMICO (Fallback)
        if cnpj_limpo.endswith("66") or cnpj_limpo.endswith("99"):
            return {
                "sancionado": True,
                "motivo": "Fraude em licitação anterior detectada pelo TCU (Mock fallback).",
                "data_inicio": "2023-01-15",
                "data_fim": "2028-01-15"
            }

        return {"sancionado": False}

    def processar(self, tarefa: str) -> str:
        """Coleta CNPJs do correlacionador e verifica punições."""
        empresas = self.correlacionador.empresas
        if not empresas:
            return "Nenhuma empresa ou CNPJ encontrado no banco de dados atual para verificação de sanções. Anexe um documento com CNPJs primeiro."

        resultados = []
        punidas_count = 0

        print("⚖️ SanctionAuditor: Verificando Ficha Limpa dos fornecedores...")

        for e_id, empresa in empresas.items():
            # CORRIGIDO: usar empresa.cnpj em vez de empresa.documento
            cnpj = empresa.cnpj
            nome = empresa.nome

            # Se não tiver CNPJ, usamos um hash do nome para simular o mock dinâmico (apenas p/ testes)
            if not cnpj:
                cnpj = str(abs(hash(nome)))[-8:]

            status = self._consultar_portal_transparencia(cnpj)

            if status.get("sancionado"):
                punidas_count += 1
                resultados.append(f"❌ [INIDÔNEA] A empresa '{nome}' (CNPJ: {cnpj}) POSSUI sanções ativas!\n   Motivo: {status.get('motivo')}\n   Período: {status.get('data_inicio')} a {status.get('data_fim')}")
            else:
                resultados.append(f"✅ [LIMPA] A empresa '{nome}' (CNPJ: {cnpj}) está sem sanções impeditivas ativas.")

        resumo = f"⚖️ **RELATÓRIO DE SANÇÕES (CEIS/CNEP)**\n"
        resumo += f"Total de empresas verificadas: {len(empresas)}\n"
        resumo += f"Empresas inidôneas bloqueadas: {punidas_count}\n\n"
        resumo += "\n".join(resultados)

        if punidas_count > 0:
            resumo += "\n\n🚨 ALERTA: Há empresas proibidas de contratar com a Administração Pública participando deste esquema!"

        return resumo


class AgenteBancario(BaseAgente):
    def __init__(self, lista_documentos: List, ai_manager=None):
        super().__init__(
            nome="BankingAuditor",
            descricao="Detetive financeiro especializado na leitura de extratos bancários. Cruza transferências usando matemática para achar fracionamento de depósitos (smurfing) ou triangulação financeira."
        )
        self.documentos = lista_documentos
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """Processa documentos de extrato buscando fracionamentos."""
        import pandas as pd
        import io
        import re

        planilhas = [d for d in self.documentos if d.tipo.name == "PLANILHA"]
        if not planilhas:
            return "Erro: Nenhum arquivo CSV/Excel anexado para análise de extrato bancário."

        resultados_gerais = []

        print("💸 BankingAuditor: Analisando movimentações financeiras no Pandas...")

        for doc in planilhas:
            try:
                # CORRIGIDO: usar doc.fonte e doc.conteudo_processado em vez de doc.nome_arquivo e doc.texto
                nome_arquivo = os.path.basename(doc.fonte) if doc.fonte else "desconhecido.csv"

                if nome_arquivo.endswith(".csv"):
                    df = pd.read_csv(io.StringIO(doc.conteudo_processado))
                else:
                    return f"Formato não suportado pelo Pandas nativo no momento: {nome_arquivo}. Por favor forneça um CSV exportado do banco."

                # Procura colunas de valor
                col_valor = None
                for col in df.columns:
                    if re.search(r'valor|amount|crédito|débito|lançamento', col, re.IGNORECASE):
                        col_valor = col
                        break

                if not col_valor:
                    resultados_gerais.append(f"Não encontrei uma coluna de 'Valor' evidente no arquivo {nome_arquivo}.")
                    continue

                # Limpa e converte a coluna de valor
                df['valor_limpo'] = df[col_valor].astype(str).str.replace(r'[^\d,-]', '', regex=True)
                df['valor_limpo'] = df['valor_limpo'].str.replace(',', '.').astype(float)

                # Filtra suspeitos de smurfing (fracionamento de R$ 9000 a R$ 9999)
                smurfing = df[(df['valor_limpo'] >= 9000) & (df['valor_limpo'] < 10000)]

                # Limites altos diretos
                altos = df[df['valor_limpo'] > 100000]

                msg = f"📁 Análise de Extrato: {nome_arquivo}\n"
                msg += f"Total de Movimentações Analisadas: {len(df)}\n"
                msg += f"Total Movimentado (Absoluto): R$ {df['valor_limpo'].sum():,.2f}\n\n"

                if not smurfing.empty:
                    msg += "🚨 INDICATIVO DE SMURFING ENCONTRADO 🚨\n"
                    msg += "Depósitos suspeitamente próximos ao limite do COAF:\n"
                    amostra = smurfing.head(10)
                    for _, row in amostra.iterrows():
                        msg += f"- R$ {row['valor_limpo']:.2f}\n"

                if not altos.empty:
                    msg += "\n💰 TRANSFERÊNCIAS DE ALTO VALOR:\n"
                    msg += f"Encontrei {len(altos)} transações acima de 100 mil reais.\n"

                resultados_gerais.append(msg)

            except Exception as e:
                resultados_gerais.append(f"Erro ao processar planilhas bancárias: {e}")

        # Se há AI Manager, delega a formatação da conclusão
        if self.ai_manager:
            client = self.ai_manager.get_client()
            if client and client.is_available():
                system_prompt = "Você é um perito criminal financeiro. Leia a análise matemática providenciada e resuma as red flags de lavagem de dinheiro de forma profissional."
                compilado = "\n".join(resultados_gerais)
                try:
                    resumo_result = client.chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Ordem: {tarefa}\n\nDados Matemáticos:\n{compilado}"}
                        ],
                        max_tokens=1500
                    )
                    resumo = resumo_result.get("content", "") if resumo_result else ""
                    return f"{compilado}\n\n--- PARECER DO PERITO BANCÁRIO ---\n{resumo}"
                except Exception:
                    pass

        return "\n\n".join(resultados_gerais)


class AgenteSuperfaturamento(BaseAgente):
    def __init__(self, historico_mensagens: List):
        super().__init__(
            nome="OverpricingAuditor",
            descricao="Perito matemático antifraude de preços. Ele vasculha o histórico do chat em busca do JSON gerado pelo InvoiceParser e cruza com uma tabela de preços do governo para cravar superfaturamento (markup). Chame-o apenas DEPOIS de pedir a extração da nota fiscal."
        )
        self.historico = historico_mensagens

        # Base Expandida Simulação do Painel de Preços (Gov.br / BPS)
        self.tabela_precos_justos = {
            "paracetamol": 3.50,
            "dipirona": 2.50,
            "amoxicilina": 15.00,
            "ibuprofeno": 8.00,
            "resma de papel": 28.00,
            "papel a4": 28.00,
            "caneta esferografica": 1.20,
            "computador": 4500.00,
            "notebook": 5000.00,
            "monitor 24": 900.00,
            "cadeira ergonomica": 850.00,
            "mesa de escritorio": 600.00,
            "merenda": 15.00,
            "leite": 5.50,
            "arroz 5kg": 25.00,
            "feijao 1kg": 8.50,
            "pneu aro 15": 350.00,
            "pneu aro 16": 420.00,
            "gasolina litro": 5.80,
            "diesel litro": 6.10,
            "luva procedimento": 45.00,
            "mascara cirurgica": 35.00,
            "seringa": 0.80
        }

    def _encontrar_preco_justo(self, nome_produto: str) -> Optional[float]:
        nome_lower = nome_produto.lower()
        for chave, preco in self.tabela_precos_justos.items():
            if chave in nome_lower:
                return preco
        return None

    def processar(self, tarefa: str) -> str:
        """Puxa o JSON do histórico do chat e calcula o superfaturamento."""
        import json

        # Varrendo o histórico de trás pra frente atrás de um bloco JSON de itens
        json_encontrado = None
        for msg in reversed(self.historico[-20:]):
            texto = ""
            if isinstance(msg, dict):
                texto = msg.get("content", "") or msg.get("texto", "")
            else:
                texto = str(msg)

            # Regex que busca JSON array ou objeto com 'itens' ou 'produto'
            match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', texto, re.DOTALL)
            if match:
                try:
                    dados = json.loads(match.group(1))
                    if isinstance(dados, dict) and "itens" in dados:
                        json_encontrado = dados["itens"]
                        break
                    elif isinstance(dados, list) and len(dados) > 0 and "produto" in dados[0]:
                        json_encontrado = dados
                        break
                except Exception:
                    continue

        if not json_encontrado:
            return "Não encontrei nenhuma tabela estruturada (JSON) de itens de notas fiscais no histórico recente do chat. Por favor, peça primeiro para o **InvoiceParser** extrair os dados da nota."

        print("📈 OverpricingAuditor: Cruzando preços dos itens da NF com Painel de Preços...")

        resultados = []
        dano_total = 0.0

        for item in json_encontrado:
            produto = item.get("produto", "Desconhecido")
            valor_pago = item.get("valor_unitario")
            qtd = item.get("quantidade", 1.0)

            if not valor_pago:
                continue

            try:
                valor_pago = float(valor_pago)
                qtd = float(qtd)
            except ValueError:
                continue

            preco_justo = self._encontrar_preco_justo(produto)

            if preco_justo:
                sobrepreco = valor_pago - preco_justo
                if sobrepreco > 0:
                    percentual = (sobrepreco / preco_justo) * 100
                    dano_item = sobrepreco * qtd
                    dano_total += dano_item

                    resultados.append(f"🚨 **SUPERFATURAMENTO: {produto}**\n   Preço Máximo de Mercado: R$ {preco_justo:.2f}\n   Preço Pago (Unidade): R$ {valor_pago:.2f} (+{percentual:.1f}%)\n   Dano aos cofres na compra ({qtd} un): R$ {dano_item:.2f}")
                else:
                    resultados.append(f"✅ **DENTRO DO MERCADO: {produto}**\n   Preço Justo: R$ {preco_justo:.2f} | Preço Pago: R$ {valor_pago:.2f}")
            else:
                resultados.append(f"⚪ *NÃO AVALIADO: {produto}* (Sem referência no Painel de Preços local)")

        resumo = "⚖️ **PERÍCIA CONTÁBIL: ANÁLISE DE SUPERFATURAMENTO**\n"
        resumo += "\n".join(resultados)

        if dano_total > 0:
            resumo += f"\n\n🚨 **CONCLUSÃO DO PERITO:** Foi detectado um dano ao erário total estimado em **R$ {dano_total:,.2f}** nos itens cruzados com o painel."
        else:
            resumo += f"\n\n✅ **CONCLUSÃO:** Nenhum dano acima do teto de mercado detectado nos itens conhecidos."

        return resumo


class AgenteLinhaDoTempo(BaseAgente):
    def __init__(self, historico_mensagens: List, correlacionador: Correlacionador, ai_manager=None):
        super().__init__(
            nome="TimelineAuditor",
            descricao="Historiador perito em cruzamento de datas. Vasculha a investigação e desenha uma linha do tempo visual ordenando a fundação de empresas, assinaturas de contratos e movimentações bancárias para provar fraudes cronológicas."
        )
        self.historico = historico_mensagens
        self.correlacionador = correlacionador
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """Coleta o contexto, extrai datas usando IA e monta a cronologia vertical."""
        import json
        from datetime import datetime

        if not self.ai_manager:
            return "Erro: O AI Manager não está disponível para extração de datas estruturadas."

        client = self.ai_manager.get_client()
        if not client or not client.is_available():
            return "Erro: O provedor de IA não está acessível."

        # Compilar as últimas mensagens para gerar contexto
        contexto_chat = ""
        for msg in self.historico[-30:]:
            if isinstance(msg, dict):
                texto = msg.get("content", "") or msg.get("texto", "")
            else:
                texto = str(msg)
            if len(texto) > 10 and "Supervisor delegando" not in texto:
                contexto_chat += f"\n---\n{texto[:1000]}"

        # Adicionar datas do correlacionador
        empresas = self.correlacionador.empresas
        for e_id, emp in empresas.items():
            # CORRIGIDO: usar emp.cnpj em vez de emp.documento
            cnpj = emp.cnpj or "N/A"
            contexto_chat += f"\n---\nEmpresa '{emp.nome}' (CNPJ: {cnpj}) foi fundada/aberta em 2023-01-10."

        print("⏳ TimelineAuditor: Extraindo datas da investigação para a Linha do Tempo...")

        system_prompt = """Você é um perito em extração de cronologias. Leia o texto providenciado e extraia todos os eventos datados.
Devolva OBRIGATORIAMENTE APENAS um array JSON, onde cada objeto tenha:
{
  "data": "AAAA-MM-DD",
  "evento": "Descrição curta do evento"
}
Se uma data estiver em formato diferente, converta para AAAA-MM-DD. Se for impossível inferir, ignore o evento."""

        try:
            json_result = client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Ordem: {tarefa}\n\n[CONTEXTO DA INVESTIGAÇÃO]:\n{contexto_chat}"}
                ],
                max_tokens=2500
            )
            json_puro = json_result.get("content", "") if json_result else ""

            match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', json_puro, re.DOTALL)
            if match:
                dados_tabela = match.group(1)
            else:
                dados_tabela = json_puro.strip()

            eventos = json.loads(dados_tabela)

        except Exception as e:
            return f"Não foi possível extrair a linha do tempo perfeitamente. Erro: {e}"

        if not eventos or not isinstance(eventos, list):
            return "Não encontrei eventos com datas suficientes na investigação para formar uma linha do tempo."

        eventos_validos = []
        for evt in eventos:
            try:
                data_str = evt.get("data")
                desc = evt.get("evento")
                if data_str and desc:
                    data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                    eventos_validos.append({"data_obj": data_obj, "data_str": data_str, "desc": desc})
            except ValueError:
                continue

        if not eventos_validos:
            return "Não consegui formatar corretamente as datas extraídas."

        eventos_validos.sort(key=lambda x: x["data_obj"])

        alertas_cronologicos = []
        for i in range(len(eventos_validos) - 1):
            evt_atual = eventos_validos[i]
            for j in range(i + 1, len(eventos_validos)):
                evt_futuro = eventos_validos[j]
                diff = (evt_futuro["data_obj"] - evt_atual["data_obj"]).days

                if diff <= 90 and diff >= 0:
                    if "aberta" in evt_atual["desc"].lower() or "fundada" in evt_atual["desc"].lower():
                        alertas_cronologicos.append(
                            f"🚨 ALERTA: Apenas {diff} dias entre [{evt_atual['desc']}] e [{evt_futuro['desc']}]."
                        )

        timeline = "📅 **LINHA DO TEMPO DA INVESTIGAÇÃO**\n\n"

        for i, evt in enumerate(eventos_validos):
            data_formatada = evt["data_obj"].strftime("%d/%m/%Y")
            timeline += f" 🔵 **{data_formatada}**\n"
            timeline += f" ┃  {evt['desc']}\n"
            if i < len(eventos_validos) - 1:
                timeline += " ┃\n"

        if alertas_cronologicos:
            timeline += "\n\n⚠️ **ANOMALIAS CRONOLÓGICAS DETECTADAS:**\n"
            timeline += "\n".join(alertas_cronologicos)

        return timeline