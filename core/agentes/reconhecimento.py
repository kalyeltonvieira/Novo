from typing import Dict, Any, List
import requests
from bs4 import BeautifulSoup
from .base import BaseAgente

class ReconhecimentoAgente(BaseAgente):
    """
    Agente responsável por visitar uma URL (ex: Portal da Transparência) e 
    identificar qual o sistema/CMS por trás da página (Betha, Aspec, Fiorilli, IPM, etc.).
    """
    def __init__(self):
        super().__init__(
            nome="CMS_Fingerprinter",
            descricao="Reconhece e identifica o tipo de sistema usado por uma prefeitura (Betha, Aspec, Fiorilli, etc.) para guiar as estratégias de extração."
        )
        self.assinaturas_conhecidas = {
            "betha": ["betha.com.br", "Betha Sistemas", "e-Transparencia", "betha-"],
            "aspec": ["Aspec Informatica", "aspec.com.br", "Portal da Transparência - Aspec"],
            "fiorilli": ["Fiorilli", "fiorilli.com.br", "SIAFIC", "Fiorilli S/C Ltda"],
            "ipm": ["IPM Sistemas", "Atende.Net", "ipm.com.br"],
            "govbr": ["GOVBR", "govbr.com.br", "Pronim"],
            "e-cidade": ["e-cidade", "DBSeller", "e-Cidade"],
        }
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    def processar(self, tarefa: str) -> str:
        """
        Recebe a URL ou nome da prefeitura na tarefa. Se achar URL, analisa o HTML.
        """
        import re
        urls = re.findall(r'(https?://[^\s]+)', tarefa)
        
        if not urls:
            return "Nenhuma URL fornecida para análise de CMS."
            
        alvo = urls[0]
        try:
            print(f"[Fingerprinter] Investigando sistema do portal: {alvo}")
            resp = self.session.get(alvo, timeout=15, verify=False)
            html = resp.text.lower()
            
            sistema_detectado = "Personalizado/Desconhecido"
            for cms, signatures in self.assinaturas_conhecidas.items():
                for sig in signatures:
                    if sig.lower() in html:
                        sistema_detectado = cms.upper()
                        break
                if sistema_detectado != "Personalizado/Desconhecido":
                    break
                    
            if sistema_detectado != "Personalizado/Desconhecido":
                return f"Identifiquei que a prefeitura utiliza o sistema: **{sistema_detectado}**. \nO extrator saberá lidar melhor com as peculiaridades desta plataforma."
            else:
                return f"O portal em {alvo} parece utilizar um sistema personalizado ou um CMS não listado nas assinaturas primárias. Recomendo o uso da Extração Genérica por RAG ou XPath dinâmico."
                
        except Exception as e:
            return f"Erro ao tentar acessar a URL para reconhecimento: {e}"
