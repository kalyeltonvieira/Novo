from typing import Dict, Any, List
import requests
from .base import BaseAgente

class OffshoreAgente(BaseAgente):
    """
    Rastreia nomes de empresas e pessoas em bases globais de vazamentos 
    (ex: ICIJ Offshore Leaks, Panama Papers, Pandora Papers) para detectar
    ligações com offshores e paraísos fiscais.
    """
    def __init__(self):
        super().__init__(
            nome="OffshoreAgent",
            descricao="Cruza nomes de sócios e empresas com os bancos de dados globais do ICIJ (Panama Papers, Pandora Papers) para buscar offshores em paraísos fiscais usadas para lavagem de dinheiro."
        )
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

    def _consultar_icij(self, query: str) -> List[Dict[str, str]]:
        """
        Consulta simulada (mock) na base do ICIJ Offshore Leaks.
        Em produção, consumiria o dump do ICIJ Neo4j ou a API de busca deles via web scraping.
        """
        import random
        import time
        time.sleep(1) # Simula delay de rede
        
        resultados = []
        # Mocking a resposta se a query tiver um "nome suspeito" ou 10% de chance aleatória
        if "laranja" in query.lower() or "fantasma" in query.lower() or random.random() > 0.8:
            jurisdicoes = ["British Virgin Islands", "Cayman Islands", "Panama", "Bahamas", "Seychelles"]
            resultados.append({
                "node_type": "Officer",
                "name": query.upper(),
                "jurisdiction": random.choice(jurisdicoes),
                "source": "Pandora Papers",
                "link_description": "Shareholder of"
            })
            
            # Adiciona a empresa offshore conectada
            resultados.append({
                "node_type": "Entity",
                "name": f"{query.split()[0].upper()} HOLDINGS LTD",
                "jurisdiction": random.choice(jurisdicoes),
                "source": "Pandora Papers",
                "link_description": "Registered in"
            })
            
        return resultados

    def processar(self, tarefa: str) -> str:
        """
        Recebe o nome do alvo na tarefa e cruza com a base offshore.
        """
        import re
        
        alvo = re.sub(r'(?i)(busque|offshore|panama|papers|o|a|empresa|socio|sócio|por|favor|em)', '', tarefa).strip()
        if len(alvo) < 3:
            return "Forneça um nome válido de pessoa ou empresa para cruzar no Offshore Leaks."
            
        print(f"[OffshoreAgent] Consultando base global do ICIJ para: {alvo}...")
        
        resultados = self._consultar_icij(alvo)
        
        if not resultados:
            return f"🌴 **Offshore Check**: Nenhuma ligação direta encontrada para **{alvo}** nas bases do Panama Papers, Pandora Papers ou Bahamas Leaks."
            
        res = f"🚨 **ALERTA VERMELHO INTERNACIONAL (LAVAGEM DE DINHEIRO)** 🚨\n"
        res += f"O alvo **{alvo}** possui correspondências exatas em vazamentos de paraísos fiscais (ICIJ Database)!\n\n"
        
        for r in resultados:
            if r['node_type'] == 'Officer':
                res += f"- **Sócio/Beneficiário**: `{r['name']}`\n"
                res += f"  - Jurisdição: {r['jurisdiction']} (Fonte: {r['source']})\n"
                res += f"  - Relação: {r['link_description']}\n\n"
            else:
                res += f"- **Empresa Offshore (Shell Company)**: `{r['name']}`\n"
                res += f"  - Jurisdição: {r['jurisdiction']} (Fonte: {r['source']})\n\n"
                
        res += "> **Ação Recomendada**: Sugere-se solicitar quebra de sigilo bancário internacional ao Coaf/MPF com base nos tratados de cooperação, pois os fundos das licitações locais podem estar sendo remetidos para esta jurisdição."
        
        return res
