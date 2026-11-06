from typing import Dict, Any, List
import datetime
from .base import BaseAgente

class AgentePromotor(BaseAgente):
    """
    Agente focado em Redação Jurídica Automatizada.
    Pega os achados de fraude do dossiê e formata em uma Petição Inicial/Denúncia 
    com base na Nova Lei de Licitações (14.133/2021).
    """
    def __init__(self, ai_manager):
        super().__init__(
            nome="PromotorVirtual",
            descricao="Elabora automaticamente peças jurídicas (Denúncias, Ações Populares, Ofícios ao MPF) traduzindo as fraudes descobertas para a linguagem do Direito Administrativo (Lei 14.133/2021)."
        )
        self.ai_manager = ai_manager

    def processar(self, tarefa: str) -> str:
        """
        Recebe a tarefa pedindo para gerar uma petição.
        Idealmente, usaria o Histórico do Chat para ler os achados. Aqui faremos
        uma sumarização direta usando o ai_manager.
        """
        import re
        
        # Filtra a tarefa para entender contra quem é a peça
        alvo = re.sub(r'(?i)(gere|a|peça|petição|denúncia|contra|o|a|prefeito|prefeitura|empresa|para)', '', tarefa).strip()
        if len(alvo) < 3:
            alvo = "MUNICÍPIO / EMPRESA INVESTIGADA"
            
        print(f"[PromotorVirtual] Redigindo Peça Acusatória baseada na Lei 14.133 para: {alvo}")
        
        prompt = f"""
        Você é um Promotor de Justiça especialista em Direito Administrativo Brasileiro.
        Escreva uma minuta de Representação/Denúncia ao Ministério Público Estadual baseada na Nova Lei de Licitações (Lei 14.133/2021).
        O alvo da denúncia é: {alvo}.
        A denúncia deve alegar as seguintes suspeitas (baseadas nos achados de nossos outros agentes):
        - Fracionamento de despesa e direcionamento de licitação.
        - Empresa de fachada (incompatibilidade entre capital social e contrato).
        - Conluio/Rodízio com outras empresas do mesmo grupo (Laranjas).
        
        Formate como um documento legal real:
        EXCELENTÍSSIMO SENHOR DOUTOR PROMOTOR DE JUSTIÇA...
        DOS FATOS...
        DO DIREITO (cite artigos da Lei 14.133)...
        DOS PEDIDOS (suspensão do certame, bloqueio de bens)...
        
        Gere uma peça coesa, técnica e pronta para protocolo (com os espaços em branco para dados específicos).
        """
        
        try:
            provider = self.ai_manager.get_provider()
            resposta_ia = provider.generate_text(prompt, system_prompt="Você é um software de geração de peças jurídicas. Siga estritamente o rito legal brasileiro.")
            
            res = f"⚖️ **Peça Jurídica Gerada com Sucesso**\n\n"
            res += "> *Nota: Esta é uma minuta automática gerada por IA. A assinatura e protocolo exigem um advogado/promotor real.*\n\n"
            res += resposta_ia
            
            return res
            
        except Exception as e:
            return f"Falha ao gerar a petição legal: {e}"
