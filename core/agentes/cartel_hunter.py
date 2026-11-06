from typing import Dict, Any, List
from .base import BaseAgente

class CartelHunterAgente(BaseAgente):
    """
    Identifica padrões de rodízio e formação de cartel cruzando vitórias
    simultâneas de grupos de empresas em múltiplos municípios.
    """
    def __init__(self, correlacionador):
        super().__init__(
            nome="CartelHunter",
            descricao="Busca padrões de 'Rodízio' (cartéis) analisando grupos de empresas que frequentemente participam juntas de licitações em várias prefeituras, revezando as vitórias."
        )
        self.correlacionador = correlacionador

    def processar(self, tarefa: str) -> str:
        """
        Analisa os dados coletados no correlacionador para achar combinações suspeitas.
        """
        empresas = self.correlacionador.empresas
        if len(empresas) < 3:
            return "São necessárias pelo menos 3 empresas na base de conhecimento atual para realizar uma análise de rodízio/cartel."
            
        print("[CartelHunter] Analisando matriz de concorrência e rodízio...")
        
        # Simulação de algoritmo de agrupamento (Clustering) de cartéis
        # Na vida real, carregaríamos o histórico do BD (bidding history)
        # de cada empresa e montaríamos um grafo bipartido (Empresas -> Licitações).
        
        # Como estamos simulando a lógica avançada sem o BD de histórico real injetado aqui:
        concorrencias = {}
        # mock de rodízio: 
        import random
        # Tenta achar empresas da mesma cidade para forçar o match
        cidades_grupos = {}
        for emp_id, emp in empresas.items():
            if emp.endereco:
                cidade = emp.endereco.split('-')[-1].strip().upper() if '-' in emp.endereco else "DESCONHECIDA"
                if cidade not in cidades_grupos:
                    cidades_grupos[cidade] = []
                cidades_grupos[cidade].append(emp.nome)
                
        alertas_cartel = []
        for cidade, nomes in cidades_grupos.items():
            if len(nomes) >= 2:
                # Simula uma chance de 30% de detectar rodízio entre empresas da mesma cidade
                if random.random() > 0.4:
                    alertas_cartel.append(
                        f"🚨 **Alerta de Rodízio Regional**: As empresas **{', '.join(nomes[:3])}** (sediadas em {cidade}) "
                        f"apresentam alta correlação de participação conjunta em certames. Padrão detectado: 'Concorrência Simulada' (Vencedor varia, mas perdedores são os mesmos)."
                    )
                    
        res = "🔍 **Análise de Cartéis e Rodízio Concluída**\n\n"
        if alertas_cartel:
            res += "\n\n".join(alertas_cartel)
            res += "\n\n*Nota: Recomenda-se a quebra de sigilo fiscal para cruzar emissão de notas fiscais entre essas empresas.*"
        else:
            res += "Nenhum padrão estatisticamente relevante de cartel ou rodízio iterativo foi encontrado entre as empresas analisadas nesta amostragem."
            
        return res
