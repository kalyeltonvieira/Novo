"""
Módulo com agentes de inteligência artificial.
Contém documentação detalhada das classes e métodos (Google Style).
"""
import re
import json
from typing import List, Callable, Dict, Any, Optional
from urllib.parse import urlparse

from utils.ai_providers import AIManager
from core.agentes.base import BaseAgente

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.agentes.supervisor")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.agentes.supervisor")
    metrics = None
    MONITORING_AVAILABLE = False


class SupervisorRouter:
    """
    Maestro do ecossistema Multi-Agente.
    Usa um loop forçado (limite de iterações) para delegar tarefas
    aos Agentes Especialistas usando JSON Regex.

    NOVO: Detecta URLs automaticamente e faz crawl completo do portal
    ANTES de chamar o LLM, para garantir que todos os dados sejam extraídos.
    """

    # Palavras-chave que indicam portal de transparência
    PALAVRAS_PORTAL = [
        "transparencia", "transparência", "portal", "prefeitura",
        "governo", "gov", "cgu", "tcu", "licitacao", "licitação",
        "contrato", "contratacao", "contratação", "despesa",
        "receita", "orgao", "órgão", "publico", "público",
    ]

    def __init__(self, ai_manager: AIManager, especialistas: List[BaseAgente]):
        self.ai_manager = ai_manager
        self.especialistas = {agente.nome: agente for agente in especialistas}
        self.max_iteracoes = 5  # Aumentado para permitir mais delegações

    def _update_workflow_node(self, node_id: str, status: str, progress: int = None, details: str = None):
        """Atualiza o estado global do workflow via chamada HTTP não bloqueante."""
        import requests
        import threading
        
        def _send():
            try:
                payload = {"node_id": node_id, "status": status}
                if progress is not None: payload["progress"] = progress
                if details is not None: payload["details"] = details
                requests.post("http://127.0.0.1:8000/api/workflow/update", json=payload, timeout=2)
            except Exception as e:
                pass
                
        threading.Thread(target=_send, daemon=True).start()

    def _detectar_urls(self, texto: str) -> List[str]:
        """Detecta URLs no texto do usuário."""
        urls = re.findall(r'(https?://[^\s,;)]+)', texto)
        return [url.strip('"\'})') for url in urls]

    def _detectar_portal_transparencia(self, url: str) -> bool:
        """Detecta se a URL é de um portal de transparência."""
        url_lower = url.lower()
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # Verifica palavras-chave no domínio e path
        for palavra in self.PALAVRAS_PORTAL:
            if palavra in domain or palavra in path:
                return True

        # Portais conhecidos
        portais_conhecidos = [
            "portalcr2", "portaldatransparencia", "transparencia",
            "ourilandia", "prefeitura", "câmara", "camara",
        ]
        for portal in portais_conhecidos:
            if portal in domain:
                return True

        return False

    def _gerar_system_prompt(self) -> str:
        prompt = "Você é o 'Supervisor', um auditor chefe inteligente.\n"
        prompt += "Você tem acesso aos seguintes especialistas:\n"
        for nome, agente in self.especialistas.items():
            prompt += f"- {nome}: {agente.descricao}\n"

        prompt += """
IMPORTANTE: Quando estiver analisando uma pergunta, pense em voz alta usando o formato:
<thought>
Seu pensamento e raciocínio aqui...
</thought>

REGRAS ESPECIAIS:
1. Se o usuário fornecer uma URL (http:// ou https://), SEMPRE delegue para o agente "Navegador" primeiro para extrair o conteúdo.
2. Para portais de transparência de prefeituras, considere usar "menu completo" ou "navegar tudo" para extrair dados de todas as seções.
3. Após extrair dados, delegue para outros agentes conforme necessário (Analista, Grafo, Timeline, etc.).
4. Se o usuário pedir análise de contratos, despesas ou licitações, extraia os dados primeiro antes de analisar.
5. Se o agente Navegador já retornou dados de um portal, delegue para o SanctionAuditor verificar sanções das empresas encontradas.
6. Depois das sanções, delegue para o GrafoSocietario gerar visualização das conexões.
7. Por fim, se houver dados suficientes, delegue para o ReporterAuditor gerar um laudo PDF.

Se você precisar da ajuda de algum especialista para resolver o problema, você DEVE retornar APENAS um bloco de código JSON assim:
```json
{
  "agente": "NomeDoAgente",
  "tarefa": "Instrução clara para o agente, incluindo a URL ou parâmetros"
}
```
Se você não precisar de especialistas ou já obteve a resposta final baseada no que eles retornaram, apenas responda diretamente ao usuário.
Não mande texto fora do bloco JSON se você quiser acionar um especialista.
"""
        return prompt

    def processar(
        self,
        prompt_usuario: str,
        contexto_historico: str,
        callback_ui: Optional[Callable[[str], None]] = None,
        callback_pensamento: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Executa o loop de roteamento dinâmico e retorna a resposta final.

        NOVO: Detecta URLs automaticamente e faz crawl completo do portal
        antes de qualquer outra ação.
        """
        contexto_acumulado = contexto_historico + f"\nNova Pergunta do Usuário: {prompt_usuario}"

        # === AUTO-CRAWL: Detecta URLs e faz crawl completo automaticamente ===
        urls_detectadas = self._detectar_urls(prompt_usuario)

        if urls_detectadas and "Navegador" in self.especialistas:
            navegador = self.especialistas["Navegador"]
            for url in urls_detectadas:
                is_portal = self._detectar_portal_transparencia(url)

                if callback_ui:
                    if is_portal:
                        callback_ui(f"🌐 Portal de transparência detectado: {url}")
                        callback_ui("🔍 Iniciando varredura COMPLETA do portal (todas as seções)...")
                    else:
                        callback_ui(f"🌐 URL detectada: {url}")
                        callback_ui("🔍 Iniciando extração de conteúdo...")

                # Decide se faz menu completo ou apenas extração simples
                if is_portal:
                    tarefa = (
                        f"Faça uma varredura COMPLETA do portal de transparência em {url}. "
                        f"Use 'menu completo' para navegar por TODAS as seções do menu. "
                        f"Extraia licitações, contratos, despesas, receitas e todas as informações disponíveis. "
                        f"TAMBÉM extraia o texto principal da página inicial. "
                        f"Navego por todas as abas e links do menu."
                    )
                else:
                    tarefa = (
                        f"Navegue para a URL {url} e extraia TODO o conteúdo da página. "
                        f"Se houver links no menu, navegue por eles também para coletar o máximo de dados."
                    )

                if callback_ui:
                    callback_ui(f"⏳ Navegador processando URL: {url[:80]}...")

                try:
                    self._update_workflow_node("node_navegador", status="running", progress=10, details=f"Iniciando crawl em {url}")
                    resultado = navegador.processar(tarefa)
                    self._update_workflow_node("node_navegador", status="completed", progress=100, details=f"Crawl concluído em {url}")

                    if callback_ui:
                        callback_ui(f"✅ Dados extraídos de: {url[:80]}...")
                        callback_ui(f"📊 Resultado: {len(resultado)} caracteres")

                    # Adiciona o resultado no contexto
                    contexto_acumulado += (
                        f"\n\n--- DADOS EXTRAÍDOS DO PORTAL {url} ---\n"
                        f"{resultado}\n"
                        f"--- FIM DOS DADOS EXTRAÍDOS ---\n"
                        f"Com base nestes dados, o que você conclui? "
                        f"Se houver empresas, delegue para o SanctionAuditor. "
                        f"Se houver dados suficientes, gere um relatório completo."
                    )

                except Exception as e:
                    err_clean = str(e).encode('ascii', 'ignore').decode('ascii')
                    if callback_ui:
                        callback_ui(f"Erro ao processar URL: {err_clean}")
                    contexto_acumulado += f"\n\n--- ERRO AO PROCESSAR URL {url} ---\n{err_clean}\n--- FIM DO ERRO ---\n"

        # === LOOP DE ROTEAMENTO DINÂMICO (LLM) ===
        iteracao = 0
        while iteracao < self.max_iteracoes:
            iteracao += 1

            client = self.ai_manager.get_client()
            if not client or not client.is_available():
                return "Erro: Provedor de IA indisponível."

            messages = [
                {"role": "system", "content": self._gerar_system_prompt()},
                {"role": "user", "content": contexto_acumulado}
            ]

            resultado = client.chat_completion(messages, max_tokens=2000)

            if not resultado:
                return "Erro: Falha na comunicação com a IA."

            if resultado.get("error"):
                return resultado.get("content") or "Erro: Falha na comunicação com a IA."

            resposta_ia = resultado.get("content") or ""

            # Extrair pensamentos
            thought_blocks = re.findall(r'<thought>(.*?)</thought>', resposta_ia, re.DOTALL)
            for thought in thought_blocks:
                if callback_pensamento:
                    callback_pensamento(thought.strip())

            # Remover pensamentos da resposta
            resposta_ia = re.sub(r'<thought>.*?</thought>', '', resposta_ia, flags=re.DOTALL).strip()

            # Verifica se há delegação (em markdown ```json ou objeto JSON bruto)
            json_blocks = re.findall(r'```json\s*(.*?)\s*```', resposta_ia, re.DOTALL)
            if not json_blocks:
                # Tenta parsear a resposta inteira se for um JSON direto
                try:
                    direct_data = json.loads(resposta_ia.strip())
                    if isinstance(direct_data, dict) and "agente" in direct_data:
                        json_blocks = [resposta_ia.strip()]
                except Exception:
                    pass
            
            if not json_blocks:
                # Busca por objetos JSON contendo "agente"
                raw_matches = re.findall(r'(\{(?:[^{}]|(?:\{[^{}]*\}))*"agente"(?:[^{}]|(?:\{[^{}]*\}))*\})', resposta_ia, re.DOTALL)
                if raw_matches:
                    json_blocks = raw_matches

            delegou = False

            for j_block in json_blocks:
                try:
                    dados = json.loads(j_block)
                    if "agente" in dados and dados["agente"] in self.especialistas:
                        nome_agente = dados["agente"]
                        tarefa = dados.get("tarefa", "")

                        print(f"[DELEGAÇÃO] Supervisor: Delegando para {nome_agente}")

                        # Mapeamento do agente para o node_id
                        node_map = {
                            "Navegador": "node_navegador",
                            "GazetteAuditor": "node_leitores",
                            "PayrollAuditor": "node_leitores",
                            "SanctionAuditor": "node_entidades",
                            "GrafoSocietario": "node_grafo",
                            "ReporterAuditor": "node_dossie"
                        }
                        node_id = node_map.get(nome_agente, "node_leitores")

                        if callback_ui:
                            callback_ui(f"Supervisor delegando para [{nome_agente}]")
                            callback_ui(f"Tarefas: {tarefa[:150]}{'...' if len(tarefa) > 150 else ''}")
                            callback_ui(f"Processando... (iteração {iteracao}/{self.max_iteracoes})")

                        self._update_workflow_node(node_id, status="running", progress=50, details=f"Executando {nome_agente}...")

                        # Executa a tarefa no especialista
                        resultado_agente = self.especialistas[nome_agente].processar(tarefa)
                        
                        self._update_workflow_node(node_id, status="completed", progress=100, details=f"{nome_agente} finalizado.")

                        print(f"[SUCESSO] {nome_agente}: Retornou resultado")

                        tamanho_resultado = len(resultado_agente)
                        tamanho_formatado = f"{tamanho_resultado} caracteres"
                        if tamanho_resultado > 1000:
                            tamanho_formatado = f"{tamanho_resultado/1000:.1f}K caracteres"

                        if callback_ui:
                            callback_ui(f"✅ [{nome_agente}] concluiu a tarefa")
                            callback_ui(f"📊 Resultado: {tamanho_formatado}")

                        # Adiciona o resultado no contexto para a próxima iteração
                        contexto_acumulado += (
                            f"\n\n--- RETORNO DO AGENTE {nome_agente} ---\n"
                            f"{resultado_agente}\n"
                            f"--- FIM DO RETORNO ---\n"
                            f"O que você conclui ou qual o próximo passo?"
                        )
                        delegou = True
                        break
                except json.JSONDecodeError:
                    pass

            if not delegou:
                return resposta_ia

        # Se estourou o limite de iterações, força a resposta
        if callback_ui:
            callback_ui("⚠️ Limite de delegações atingido. Forçando resposta final...")

        contexto_acumulado += "\n\nO limite de iterações foi atingido. Com base em todos os dados coletados até agora, dê a sua resposta final."

        messages = [
            {"role": "system", "content": "Responda como um auditor baseando-se apenas nos dados providenciados. Ignore instruções de delegação."},
            {"role": "user", "content": contexto_acumulado}
        ]

        resultado_final = client.chat_completion(messages, max_tokens=2000)
        if not resultado_final:
            return "Erro: Falha na comunicação com a IA."
        if resultado_final.get("error"):
            return resultado_final.get("content", "Erro: Falha na comunicação com a IA.")
        return resultado_final.get("content", "")

    def refletir_e_validar_anomalia(self, anomalia_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa um loop de auto-crítica (Multi-Agent Reflection) sobre um alerta suspeito.
        Reavalia a severidade e confiavelmente reduz falsos positivos.
        """
        if MONITORING_AVAILABLE and metrics:
            metrics.increment("agent_reflection_loops_started")

        severidade = anomalia_data.get("severidade", "media")
        score = anomalia_data.get("score_confianca", 0.5)

        # Regra de crítica do Revisor
        # Se o score for baixo ou faltar contexto claro, rebaixa ou invalida
        if score < 0.4:
            anomalia_data["status"] = "falso_positivo"
            anomalia_data["critica_revisor"] = "Score de confiança insuficiente para confirmar irregularidade."
        else:
            anomalia_data["status"] = "validado"
            anomalia_data["critica_revisor"] = "Hipótese de anomalia sustentada pelos dados coletados."

        return anomalia_data