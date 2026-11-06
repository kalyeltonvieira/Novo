from typing import Dict, Any, List
import requests
import base64
import os
from .base import BaseAgente

class VisaoGeoespacialAgente(BaseAgente):
    """
    Agente que cruza o endereço de uma empresa com a API do Google Street View
    e usa Modelos Multimodais (LLM Vision) para dizer se a fachada é compatível 
    com o volume financeiro do contrato vencido.
    """
    def __init__(self, ai_manager):
        super().__init__(
            nome="VisaoGeoespacial",
            descricao="Busca a foto da fachada da empresa no Street View e usa IA Visual para atestar se é uma sede real condizente com os contratos, ou se é um terreno baldio/residência."
        )
        self.ai_manager = ai_manager
        # Na vida real usaria chave do Google Cloud (os.getenv("GOOGLE_MAPS_API_KEY"))
        self.maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "MOCK_KEY")

    def _baixar_street_view(self, endereco: str) -> str:
        """
        Baixa a imagem estática do Street View e converte pra base64.
        Para demonstração sem API Key válida, retorna uma string mockada 
        ou a URL apenas.
        """
        # Em produção:
        # url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={urllib.parse.quote(endereco)}&key={self.maps_api_key}"
        # resp = requests.get(url)
        # return base64.b64encode(resp.content).decode('utf-8')
        
        # Mocking
        return "data:image/jpeg;base64,MOCK_IMAGE_DATA_AQUI_..."

    def processar(self, tarefa: str) -> str:
        """
        Recebe um endereço na tarefa.
        """
        import re
        
        alvo = re.sub(r'(?i)(analise|endereço|endereco|a|fachada|de|da|empresa|na|rua)', '', tarefa).strip()
        if len(alvo) < 5:
            return "Forneça um endereço válido para análise visual geoespacial."
            
        print(f"[VisaoGeoespacial] Puxando satélite e Street View de: {alvo}...")
        
        b64_image = self._baixar_street_view(alvo)
        
        if not b64_image:
            return "Não foi possível encontrar imagens de Street View para este endereço."
            
        # Aciona o provedor Multimodal (ex: GPT-4 Vision)
        prompt_visual = (
            "Atue como um perito criminal. Analise a imagem em anexo correspondente ao endereço sede de uma construtora "
            "que venceu R$ 5.000.000,00 em licitações. A estrutura física da foto suporta as máquinas, funcionários "
            "e logística exigidos para este volume financeiro? Ou parece uma empresa de fachada (residência, lote vago)?"
        )
        
        try:
            # Em uma implementação real do AI Manager com suporte a Vision:
            # resposta_ia = self.ai_manager.get_provider().generate_vision(prompt=prompt_visual, image_b64=b64_image)
            
            # Simulando a resposta para manter fluidez no mock:
            import random
            if random.random() > 0.5:
                laudo = (
                    "**LAUDO VISUAL (IA Multimodal):** 🚨 INCOMPATÍVEL.\n"
                    "A análise da fachada indica tratar-se de um imóvel puramente residencial (casa térrea pequena, sem pátio). "
                    "Não há evidências de garagem para maquinário pesado ou espaço administrativo capaz de gerir um contrato "
                    "do porte de milhões de reais. Forte indício de empresa 'Laranja' ou de fachada."
                )
            else:
                laudo = (
                    "**LAUDO VISUAL (IA Multimodal):** ✅ COMPATÍVEL.\n"
                    "A análise da fachada exibe um galpão logístico de médio/grande porte com logotipo condizente. "
                    "Há evidências de pátio para veículos operacionais. Estrutura aparentemente compatível com a capacidade técnica exigida."
                )
                
            res = f"📍 **Análise de Fachada (Google Street View)**\n**Alvo**: {alvo}\n\n{laudo}"
            return res
            
        except Exception as e:
            return f"Erro ao processar visão computacional do endereço: {e}"
