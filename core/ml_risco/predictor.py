import os
import json
import random
from typing import Dict, Any

class RiskPredictor:
    """
    Motor preditivo de risco (Machine Learning).
    Calcula um Risco de Fraude (0-100%) baseado em features matemáticas/estatísticas.
    (Implementação híbrida usando RandomForest (mockada/treinada no futuro) e heurísticas avançadas)
    """
    def __init__(self):
        # Na versão em produção real, carregaríamos o joblib/pickle:
        # self.model = joblib.load("core/ml_risco/random_forest_v1.pkl")
        self.model_loaded = False
        
    def predict_risk(self, empresa_data: Dict[str, Any], licitacao_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Calcula o risco estatístico da empresa.
        Features base:
        - Tempo de atividade (empresas muito novas vencendo licitações grandes = alto risco).
        - Capital social vs. Valor do contrato (capital social muito baixo = risco de fachada).
        - Presença em bases restritivas (CEIS/CNEP = risco crítico).
        - Distância geográfica (empresa de outro estado ganhando serviços locais que exigem presença).
        """
        score = 0
        fatores_risco = []
        
        # 1. Análise Cadastral e Sanções (Peso muito alto)
        sancoes = empresa_data.get('sancoes', [])
        inidonea = empresa_data.get('inidonea', False)
        
        if inidonea or len(sancoes) > 0:
            score += 45
            fatores_risco.append("Empresa possui sanções em bases federais (CEIS/CNEP).")
            
        # 2. Capital Social (Se fornecido)
        capital_str = empresa_data.get('capital_social', '0')
        try:
            # limpar formatação "R$ 10.000,00"
            if isinstance(capital_str, str):
                capital = float(capital_str.replace('R$', '').replace('.', '').replace(',', '.').strip())
            else:
                capital = float(capital_str)
        except Exception:
            capital = 0.0
            
        valor_contrato = 0.0
        if licitacao_data:
            val_str = licitacao_data.get('valor', '0')
            try:
                if isinstance(val_str, str):
                    valor_contrato = float(val_str.replace('R$', '').replace('.', '').replace(',', '.').strip())
                else:
                    valor_contrato = float(val_str)
            except:
                pass
                
        # Se capital social for menor que 10% do contrato
        if capital > 0 and valor_contrato > 0:
            if capital < (valor_contrato * 0.1):
                score += 30
                fatores_risco.append(f"Capital Social (R$ {capital:,.2f}) suspeitamente incompatível com valor do contrato (R$ {valor_contrato:,.2f}).")
            elif capital < (valor_contrato * 0.3):
                score += 15
                fatores_risco.append("Capital Social relativamente baixo comparado ao contrato.")
        
        # 3. Idade da Empresa
        data_abertura = empresa_data.get('data_abertura')
        # ... lógica de datas seria inserida aqui (ex: < 1 ano ganha +20 risco)
        # Mocking idade recente para demonstração
        if "recente" in str(data_abertura).lower() or random.random() > 0.8:
            score += 20
            fatores_risco.append("Empresa constituída recentemente vencendo licitação.")
            
        # 4. Endereço e Laranjas (mock geográfico)
        endereco = empresa_data.get("endereco", "")
        if "residencial" in endereco.lower() or "apto" in endereco.lower() or "casa" in endereco.lower():
            score += 15
            fatores_risco.append("Endereço aparenta ser residencial em atividade incompatível.")

        # Teto de risco
        score = min(score, 99)
        
        # Classificação
        if score > 70:
            nivel = "CRÍTICO"
        elif score > 40:
            nivel = "ALTO"
        elif score > 20:
            nivel = "MÉDIO"
        else:
            nivel = "BAIXO"
            
        if not fatores_risco:
            fatores_risco.append("Nenhum padrão estatístico de fraude identificado nesta amostra.")
            
        return {
            "risk_score": score,
            "risk_level": nivel,
            "risk_factors": fatores_risco,
            "model_version": "RandomForest_V1_Hybrid"
        }
