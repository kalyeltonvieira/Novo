from typing import Dict, Any, List
import requests
import urllib.parse
from bs4 import BeautifulSoup
from .base import BaseAgente

class AgenteOSINT(BaseAgente):
    """
    Agente focado em Open Source Intelligence (OSINT).
    Busca nomes de empresas e sócios no Google, DuckDuckGo, JusBrasil 
    ou portais de notícias para encontrar indícios de corrupção ou processos.
    """
    def __init__(self):
        super().__init__(
            nome="OSINT",
            descricao="Vasculha a web aberta (notícias, processos judiciais) atrás de antecedentes criminais, escândalos ou ligações políticas de sócios e empresas."
        )
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        })
        
    def _buscar_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        """Usa a versão HTML lite do DuckDuckGo para fazer scraping seguro."""
        url = "https://html.duckduckgo.com/html/"
        data = {"q": query}
        resultados = []
        try:
            resp = self.session.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.find_all('a', class_='result__snippet'):
                    resumo = a.get_text(strip=True)
                    link = a.get('href', '')
                    resultados.append({'snippet': resumo, 'url': link})
                    if len(resultados) >= 5:
                        break
        except Exception as e:
            print(f"[OSINT] Erro na busca web: {e}")
            
        return resultados

    def processar(self, tarefa: str) -> str:
        """
        Recebe o nome de um alvo (empresa ou sócio) para investigar.
        """
        import re
        
        # Tenta extrair o nome alvo (assumimos que foi passado na string)
        # Vamos remover palavras de comando
        alvo = re.sub(r'(?i)(busque|investigue|osint|sobre|o|a|empresa|socio|sócio|por|favor)', '', tarefa).strip()
        
        if len(alvo) < 3:
            return "Forneça um nome de alvo válido para a pesquisa OSINT."
            
        print(f"[OSINT] Iniciando varredura aberta para o alvo: {alvo}")
        
        termos_suspeitos = ["preso", "investigado", "fraude", "corrupção", "polícia federal", "mpf", "laranja", "desvio"]
        query = f'"{alvo}" AND ("investigado" OR "preso" OR "fraude" OR "corrupção" OR "laranja")'
        
        resultados_busca = self._buscar_duckduckgo(query)
        
        if not resultados_busca:
            return f"Varredura OSINT concluída. Nenhuma notícia criminal ou processo altamente indexado encontrado para: **{alvo}**."
            
        alertas = []
        for r in resultados_busca:
            snippet = r['snippet'].lower()
            encontros = [t for t in termos_suspeitos if t in snippet]
            if encontros:
                alertas.append(f"- Encontrado no trecho: \"...*{r['snippet']}*...\"\n  - **Fonte**: {r['url']}\n  - **Tags**: {', '.join(encontros)}")
                
        if alertas:
            res = f"🚨 **ALERTA OSINT**: Encontrei menções suspeitas na web aberta para **{alvo}**!\n\n"
            res += "\n\n".join(alertas)
            return res
        else:
             return f"Varredura OSINT concluída. Informações encontradas para **{alvo}**, mas sem os gatilhos críticos de corrupção acionados diretamente nos resumos."
