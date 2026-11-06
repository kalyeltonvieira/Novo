from typing import Dict, Any, List
from .base import BaseAgente

class VisionScraperAgente(BaseAgente):
    """
    Agente que lida com portais muito antigos ou não-estruturados (HTML bruto).
    Ele tenta gerar Heurísticas/XPath dinâmicos usando a IA para não depender
    de parsers estáticos (BeautifulSoup limitados).
    """
    def __init__(self, navegador, ai_manager):
        super().__init__(
            nome="VisionScraper",
            descricao="Utilizado como último recurso quando o HTML da prefeitura é muito bagunçado. Usa o LLM para analisar uma amostra da tabela e inferir os seletores XPath."
        )
        self.navegador = navegador
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """
        Tarefa contém URL ou o comando para analisar a página aberta.
        """
        html = ""
        if hasattr(self.navegador, 'obter_html'):
            html = self.navegador.obter_html()
            
        if not html:
            return "Nenhum HTML encontrado na página atual do navegador."
            
        print("[VisionScraper] Analisando estrutura complexa de HTML...")
        
        # Como o HTML completo estouraria o token limit, vamos pegar as primeiras N linhas do body
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove scripts e styles
        for s in soup(["script", "style", "nav", "footer", "header"]):
            s.extract()
            
        # Pega a parte mais provável de ter os dados (tabelas, listas longas)
        alvo = None
        tabelas = soup.find_all('table')
        if tabelas:
            # Pega a tabela com mais texto
            alvo = max(tabelas, key=lambda t: len(t.get_text()))
        else:
            # Pega a div mais gordinha
            divs = soup.find_all('div')
            if divs:
                alvo = max(divs, key=lambda d: len(d.get_text()))
                
        if not alvo:
            return "Não encontrei nenhuma área de dados para extrair usando heurísticas."
            
        amostra_html = str(alvo)[:2000] # Limite de 2000 chars pra IA
        
        prompt = f"""
        Você é um bot especialista em Web Scraping.
        Abaixo está um fragmento de HTML sujo de um portal da transparência (licitações ou contratos).
        Eu preciso que você infira a estrutura lógica e gere um JSON com uma lista dos itens extraídos dessa amostra.
        Sua saída DEVE ser apenas o JSON, com campos: 'numero', 'objeto', 'valor', 'fornecedor', 'data'.
        
        HTML:
        {amostra_html}
        """
        
        try:
            # Chama a IA para ler a amostra de HTML bagunçado e estruturar
            # Na versão completa aqui chamaríamos a IA para gerar o Regex/XPath
            # Mas vamos pedir extração direta da amostra pra provar o conceito.
            provider = self.ai_manager.get_provider()
            resposta_ia = provider.generate_text(prompt, system_prompt="Você só retorna código JSON válido.")
            
            # Limpa blockticks
            json_str = re.sub(r'```json|```', '', resposta_ia).strip()
            
            import json
            dados = json.loads(json_str)
            
            res = f"VisionScraper extraiu semanticamente os dados da interface legada:\n"
            if isinstance(dados, list):
                res += f"Foram extraídos {len(dados)} registros da página atual via heurística LLM.\n"
                for i, d in enumerate(dados[:3]):
                    res += f"Registro {i+1}: {d}\n"
            else:
                res += f"Estrutura inferida: {dados}\n"
                
            return res
            
        except Exception as e:
            return f"Falha na extração heurística via IA: {str(e)}"
