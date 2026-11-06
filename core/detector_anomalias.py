"""
Detector de Anomalias - Motor de Detecção de Irregularidades
==============================================================
Procura padrões suspeitos como:
- Superfaturamento
- Nepotismo
- Cartel
- Fracionamento de compras
- Empresas fantasmas
- Conflito de interesses
- Empresas recém-criadas
- Sócios repetidos
- Pagamentos acima da média
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

from .entidades import (
    Documento, EntidadeExtraida, TipoEntidade, TipoAnomalia,
    Relacionamento, Alerta, Pessoa, Empresa, Contrato
)

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.detector_anomalias")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.detector")
    metrics = None
    MONITORING_AVAILABLE = False

# Importação opcional do gerenciador de IA
try:
    from utils.ai_providers import get_ai_manager
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("Módulo de IA não disponível. Usando apenas detectores baseados em regras.")


class DetectorAnomalias:
    """
    Motor de detecção de irregularidades em dados públicos.
    
    Este módulo implementa 12 detectores de anomalias que identificam padrões
    suspeitos em contratos, licitações e relacionamentos entre entidades.
    
    Detectores implementados:
    - Superfaturamento: Valores muito acima da média
    - Nepotismo: Parentes de agentes públicos contratados
    - Cartel: Empresas com padrão suspeito em licitações
    - Fracionamento: Compras fracionadas para evitar licitação
    - Empresa Fantasma: Empresas com características suspeitas
    - Conflito de Interesses: Agente público sócio de empresa contratada
    - Pagamento sem Licitação: Valores altos sem processo licitatório
    - Prazo Curto: Contratos com prazos suspeitosamente curtos
    - Empresa Recém-Criada: Empresas novas com contratos públicos
    - Sócio Repetido: Mesma pessoa como sócia de múltiplas empresas
    - Valor Acima da Média: Valores individuais acima da média
    - Suspeita de Fraude: Múltiplos indicadores combinados
    
    Attributes:
        config (Dict[str, Any]): Configurações do detector
        alertas (List[Alerta]): Lista de alertas gerados
        limites (Dict[str, float]): Limites configurados para cada detector
        use_ai (bool): Se True, utiliza LLM para detecção avançada
        ai_manager (Any): Gerenciador de provedores de IA
    
    Example:
        >>> detector = DetectorAnomalias(config={"use_ai": True})
        >>> alertas = detector.processar(documentos, relacionamentos, pessoas, empresas)
        >>> print(f"Anomalias detectadas: {len(alertas)}")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.alertas: List[Alerta] = []
        self.limites: Dict[str, float] = {
            "valor_acima_media": 3.0,  # desvios padrão
            "dias_empresa_nova": 180,   # dias desde abertura
            "fracionamento_dias": 30,   # dias entre compras suspeitas
            "fracionamento_valor": 50000,  # valor limite para licitação
            "capital_social_minimo": 10000,  # capital social suspeito
        }
        # Atualiza limites com configuração personalizada
        if config and "limites" in config:
            self.limites.update(config["limites"])
        
        # Configuração de IA
        self.use_ai = self.config.get("use_ai", False)
        self.ai_manager = None
        if AI_AVAILABLE and self.use_ai:
            self.ai_manager = get_ai_manager()

    def processar(
        self,
        documentos: List[Documento],
        relacionamentos: List[Relacionamento],
        pessoas: Dict[str, Pessoa],
        empresas: Dict[str, Empresa],
    ) -> List[Alerta]:
        """
        Processa todos os dados e gera alertas de anomalias.
        
        Executa todos os detectores baseados em regras e, se habilitado,
        utiliza IA para detecção avançada de padrões contextuais.
        
        Args:
            documentos: Lista de documentos processados
            relacionamentos: Lista de relacionamentos entre entidades
            pessoas: Dicionário de pessoas identificadas (id -> Pessoa)
            empresas: Dicionário de empresas identificadas (id -> Empresa)
        
        Returns:
            Lista de alertas ordenados por severidade (critica > alta > media > baixa)
        """
        if MONITORING_AVAILABLE and metrics:
            metrics.increment("detector_processar_executado")
        start_time = datetime.now()
        self.alertas = []

        # Executa cada detector baseado em regras
        self._detectar_superfaturamento(documentos)
        self._detectar_nepotismo(relacionamentos, pessoas)
        self._detectar_cartel(documentos, empresas)
        self._detectar_fracionamento(documentos)
        self._detectar_empresas_fantasmas(empresas)
        self._detectar_conflito_interesses(relacionamentos, pessoas)
        self._detectar_empresas_recem_criadas(relacionamentos, empresas)
        self._detectar_endereco_repetido(empresas)
        self._detectar_socios_repetidos(relacionamentos, empresas)
        self._detectar_valores_acima_media(documentos)
        self._detectar_pagamento_sem_licitacao(documentos, relacionamentos)
        self._detectar_prazo_curto(documentos, relacionamentos)
        self._detectar_suspeita_fraude(documentos, relacionamentos)

        # Se IA está habilitada, executa detecção avançada com LLM
        if self.use_ai and self.ai_manager:
            alertas_ai = self._detectar_anomalias_ai(documentos, relacionamentos, pessoas, empresas)
            if alertas_ai:
                self.alertas.extend(alertas_ai)
                logger.info(f"IA detectou {len(alertas_ai)} anomalias adicionais")

        # Ordena por severidade
        self.alertas.sort(key=lambda a: (
            {"critica": 0, "alta": 1, "media": 2, "baixa": 3}[a.severidade],
            -a.score_confianca
        ))

        duration = (datetime.now() - start_time).total_seconds()
        if MONITORING_AVAILABLE and metrics:
            metrics.record_timing("tempo_deteccao_anomalias", duration)
            metrics.increment("anomalias_detectadas", value=len(self.alertas))
        logger.info(f"Processamento concluído: {len(self.alertas)} alertas em {duration:.2f}s")

        return self.alertas

    def _detectar_superfaturamento(self, documentos: List[Documento]):
        """
        Detecta pagamentos muito acima da média para itens similares.
        """
        # Extrai todos os valores com contexto
        valores_contexto = []
        for doc in documentos:
            for ent in doc.entidades:
                if ent.tipo == TipoEntidade.VALOR:
                    try:
                        valor = float(ent.normalizado)
                        if valor > 1000:  # Ignora valores muito baixos
                            valores_contexto.append({
                                "valor": valor,
                                "contexto": ent.contexto,
                                "documento": doc.fonte,
                                "entidade": ent,
                            })
                    except ValueError:
                        continue

        if len(valores_contexto) < 5:
            return

        # Calcula estatísticas
        valores = [v["valor"] for v in valores_contexto]
        media = statistics.mean(valores)
        mediana = statistics.median(valores)
        try:
            desvio = statistics.stdev(valores)
        except statistics.StatisticsError:
            desvio = media * 0.5

        if desvio == 0:
            return

        # Identifica outliers
        limite_superior = mediana + (self.limites["valor_acima_media"] * desvio)

        for item in valores_contexto:
            if item["valor"] > limite_superior and item["valor"] > media * 2:
                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.SUPERFATURAMENTO,
                    titulo="Possível Superfaturamento Detectado",
                    descricao=(
                        f"Valor de R$ {item['valor']:,.2f} está muito acima da média "
                        f"(média: R$ {media:,.2f}, mediana: R$ {mediana:,.2f}). "
                        f"Contexto: {item['contexto'][:200]}"
                    ),
                    severidade="alta" if item["valor"] > media * 5 else "media",
                    score_confianca=min(0.95, 0.5 + (item["valor"] / media) * 0.1),
                    entidades_envolvidas=[item["entidade"].id],
                    documentos_relacionados=[item["documento"]],
                    valor_envolvido=item["valor"],
                    status="novo",
                ))

    def _detectar_nepotismo(self, relacionamentos: List[Relacionamento], pessoas: Dict[str, Pessoa]):
        """
        Detecta possíveis casos de nepotismo:
        parentes de agentes públicos contratados pelo órgão.
        """
        for rel in relacionamentos:
            if rel.tipo != "parente":
                continue

            # Busca se uma das pessoas tem cargo público
            pessoa_origem = pessoas.get(rel.entidade_origem)
            pessoa_destino = pessoas.get(rel.entidade_destino)

            if not pessoa_origem or not pessoa_destino:
                continue

            # Verifica se alguma tem cargo público e a outra tem contrato
            tem_cargo_publico = any(
                "secretário" in c.lower() or "diretor" in c.lower() or
                "prefeito" in c.lower() or "vereador" in c.lower()
                for c in pessoa_origem.cargos + pessoa_destino.cargos
            )

            if tem_cargo_publico:
                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.NEPOTISMO,
                    titulo="Possível Nepotismo Detectado",
                    descricao=(
                        f"Relação de parentesco entre {pessoa_origem.nome} e "
                        f"{pessoa_destino.nome}, onde um possui cargo público. "
                        f"Detalhes: {rel.detalhes}"
                    ),
                    severidade="alta",
                    score_confianca=0.7,
                    entidades_envolvidas=[rel.entidade_origem, rel.entidade_destino],
                    status="novo",
                ))

    def _detectar_cartel(self, documentos: List[Documento], empresas: Dict[str, Empresa]):
        """
        Detecta padrões de cartel:
        - Mesmas empresas participando sempre juntas
        - Padrões de rodízio em licitações
        """
        # Mapeia licitações e participantes
        licitacoes: Dict[str, List[str]] = {}
        for doc in documentos:
            nome_licitacao = None
            participantes = []

            for ent in doc.entidades:
                if ent.tipo == TipoEntidade.LICITACAO:
                    nome_licitacao = ent.valor
                elif ent.tipo == TipoEntidade.EMPRESA:
                    participantes.append(ent.id)

            if nome_licitacao and len(participantes) >= 2:
                if nome_licitacao not in licitacoes:
                    licitacoes[nome_licitacao] = []
                licitacoes[nome_licitacao].extend(participantes)

        if len(licitacoes) < 2:
            return

        # Verifica co-ocorrência de empresas em múltiplas licitações
        pares_empresas = Counter()
        for licitacao, participantes in licitacoes.items():
            for i in range(len(participantes)):
                for j in range(i + 1, len(participantes)):
                    pares_empresas[(participantes[i], participantes[j])] += 1

        # Se empresas aparecem juntas em muitas licitações
        total_licitacoes = len(licitacoes)
        for (emp1, emp2), count in pares_empresas.items():
            if count >= total_licitacoes * 0.7 and count >= 3:
                nome1 = empresas.get(emp1, Empresa(id="", nome="Desconhecida", nome_normalizado="")).nome
                nome2 = empresas.get(emp2, Empresa(id="", nome="Desconhecida", nome_normalizado="")).nome

                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.CARTEL,
                    titulo="Possível Cartel em Licitações",
                    descricao=(
                        f"As empresas '{nome1}' e '{nome2}' participaram juntas "
                        f"de {count} de {total_licitacoes} licitações. "
                        f"Padrão consistente com prática de cartel."
                    ),
                    severidade="alta",
                    score_confianca=min(0.9, 0.5 + (count / total_licitacoes) * 0.4),
                    entidades_envolvidas=[emp1, emp2],
                    status="novo",
                ))

    def _detectar_fracionamento(self, documentos: List[Documento]):
        """
        Detecta fracionamento de compras para evitar licitação:
        Múltiplas compras de valores próximos ao limite legal,
        para a mesma empresa, em curto período.
        """
        # Agrupa valores por empresa (contexto) e data
        compras: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for doc in documentos:
            empresa_atual = None
            data_atual = None

            for ent in doc.entidades:
                if ent.tipo == TipoEntidade.EMPRESA:
                    empresa_atual = ent.valor
                elif ent.tipo == TipoEntidade.VALOR:
                    try:
                        valor = float(ent.normalizado)
                        if 0 < valor < self.limites["fracionamento_valor"] * 1.5:
                            compras[empresa_atual or "desconhecida"].append({
                                "valor": valor,
                                "data": data_atual,
                                "contexto": ent.contexto,
                                "documento": doc.fonte,
                            })
                    except ValueError:
                        continue

        # Verifica padrão de fracionamento
        for empresa, lista_compras in compras.items():
            if len(lista_compras) < 3:
                continue

            # Ordena por valor
            lista_compras.sort(key=lambda x: x["valor"])

            # Verifica se vários valores estão próximos do limite
            valores_proximos_limite = [
                c for c in lista_compras
                if c["valor"] > self.limites["fracionamento_valor"] * 0.8
                and c["valor"] < self.limites["fracionamento_valor"] * 1.2
            ]

            # Se há mais de 2 compras próximas ao limite de licitação
            if len(valores_proximos_limite) > 2:
                valor_total = sum(c["valor"] for c in valores_proximos_limite)

                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.FRACIONAMENTO,
                    titulo="Possível Fracionamento de Compras",
                    descricao=(
                        f"Empresa '{empresa}' recebeu {len(valores_proximos_limite)} "
                        f"pagamentos próximos ao limite de licitação "
                        f"(R$ {self.limites['fracionamento_valor']:,.2f}). "
                        f"Valor total: R$ {valor_total:,.2f}. "
                        f"Padrão indica possível fracionamento para evitar licitação."
                    ),
                    severidade="alta",
                    score_confianca=0.8,
                    valor_envolvido=valor_total,
                    status="novo",
                ))

    def _detectar_empresas_fantasmas(self, empresas: Dict[str, Empresa]):
        """
        Detecta empresas com características suspeitas:
        - Capital social muito baixo para contratos recebidos
        - Endereço residencial
        - Sem funcionários
        - Recém-criadas com grandes contratos
        """
        for emp_id, empresa in empresas.items():
            alertas_empresa = []

            # Capital social baixo
            if empresa.capital_social and empresa.capital_social < self.limites["capital_social_minimo"]:
                alertas_empresa.append(f"capital social de R$ {empresa.capital_social:,.2f}")

            # Sem funcionários (se informação disponível)
            if empresa.funcionarios is not None and empresa.funcionarios == 0:
                alertas_empresa.append("zero funcionários registrados")

            # Endereço residencial
            if empresa.endereco and any(
                palavra in empresa.endereco.lower()
                for palavra in ["casa", "apartamento", "apto", "residencial"]
            ):
                alertas_empresa.append(f"endereço residencial ({empresa.endereco})")

            # Muitos contratos para empresa com baixo capital
            if empresa.capital_social and len(empresa.contratos) > 3:
                total_contratos = len(empresa.contratos)
                if empresa.capital_social < 5000 and total_contratos > 5:
                    alertas_empresa.append(
                        f"{total_contratos} contratos com capital social de apenas "
                        f"R$ {empresa.capital_social:,.2f}"
                    )

            if len(alertas_empresa) >= 2:
                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.EMPRESA_FANTASMA,
                    titulo="Possível Empresa Fantasma",
                    descricao=(
                        f"Empresa '{empresa.nome}' apresenta características suspeitas: "
                        + "; ".join(alertas_empresa) + "."
                    ),
                    severidade="critica" if len(alertas_empresa) >= 3 else "alta",
                    score_confianca=min(0.95, 0.3 + len(alertas_empresa) * 0.2),
                    entidades_envolvidas=[emp_id],
                    status="novo",
                ))

    def _detectar_conflito_interesses(self, relacionamentos: List[Relacionamento], pessoas: Dict[str, Pessoa]):
        """
        Detecta conflitos de interesse:
        - Agente público que é sócio de empresa contratada
        - Parente de agente público em empresa contratada
        """
        for rel in relacionamentos:
            if rel.tipo != "socio":
                continue

            pessoa = pessoas.get(rel.entidade_origem)
            if not pessoa:
                continue

            # Verifica se a pessoa tem cargo público
            tem_cargo = any(
                cargo for cargo in pessoa.cargos
                if any(p in cargo.lower() for p in [
                    "secretário", "diretor", "prefeito", "governador",
                    "ministro", "vereador", "deputado", "presidente"
                ])
            )

            if tem_cargo:
                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.CONFLITO_INTERESSE,
                    titulo="Possível Conflito de Interesses",
                    descricao=(
                        f"{pessoa.nome} possui cargo público e é sócio(a) de empresa. "
                        f"Cargos: {', '.join(pessoa.cargos)}. "
                        f"Detalhes: {rel.detalhes}"
                    ),
                    severidade="critica",
                    score_confianca=0.85,
                    entidades_envolvidas=[rel.entidade_origem, rel.entidade_destino],
                    status="novo",
                ))

    def _detectar_empresas_recem_criadas(self, relacionamentos: List[Relacionamento], empresas: Dict[str, Empresa]):
        """
        Detecta empresas recém-criadas que recebem grandes contratos.
        """
        relacoes_contrato = [r for r in relacionamentos if r.tipo == "contrato"]
        
        for emp_id, empresa in empresas.items():
            if not empresa.data_abertura:
                continue

            # Busca contratos dessa empresa
            contratos_empresa = [
                r for r in relacoes_contrato 
                if r.entidade_origem == emp_id or r.entidade_destino == emp_id
            ]

            for contrato in contratos_empresa:
                # Usa data_inicio do contrato ou data atual como fallback
                data_ref = contrato.data_inicio or datetime.now()
                idade_dias = (data_ref - empresa.data_abertura).days

                # Só alerta se a empresa foi criada pouco antes do contrato
                if -30 <= idade_dias < self.limites["dias_empresa_nova"]:
                    self.alertas.append(Alerta(
                        id=str(uuid.uuid4()),
                        tipo=TipoAnomalia.EMPRESA_RECEM_CRIADA,
                        titulo="Empresa Recém-Criada com Contrato Público",
                        descricao=(
                            f"Empresa '{empresa.nome}' possuía apenas {max(0, idade_dias)} dias de existência "
                            f"na data do contrato. "
                            f"Data de abertura: {empresa.data_abertura.strftime('%d/%m/%Y')}. "
                            f"Detalhes do contrato: {contrato.detalhes[:150]}"
                        ),
                        severidade="alta" if idade_dias < 30 else "media",
                        score_confianca=min(0.9, 0.5 + ((180 - max(0, idade_dias)) / 180) * 0.4),
                        entidades_envolvidas=[emp_id],
                        status="novo",
                    ))
                    break # Um alerta por empresa é suficiente

    def _detectar_endereco_repetido(self, empresas: Dict[str, Empresa]):
        """
        Detecta empresas diferentes registradas no mesmo endereço.
        """
        enderecos: Dict[str, List[str]] = defaultdict(list)
        
        import re
        for emp_id, empresa in empresas.items():
            if not empresa.endereco or len(empresa.endereco.strip()) < 10:
                continue
            
            # Normalização básica do endereço
            end_norm = empresa.endereco.lower().replace(",", "").replace(".", "").replace("-", " ")
            end_norm = re.sub(r'\s+', ' ', end_norm).strip()
            enderecos[end_norm].append(emp_id)
            
        for endereco, emp_ids in enderecos.items():
            if len(emp_ids) >= 2:
                nomes_empresas = [
                    empresas.get(eid, Empresa(id="", nome="Desconhecida", nome_normalizado="")).nome 
                    for eid in emp_ids
                ]
                
                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.ENDERECO_REPETIDO,
                    titulo="Múltiplas Empresas no Mesmo Endereço",
                    descricao=(
                        f"Encontradas {len(emp_ids)} empresas registradas no mesmo endereço "
                        f"({empresas[emp_ids[0]].endereco}): {', '.join(nomes_empresas)}. "
                        f"Isto pode indicar empresas de fachada ou do mesmo grupo econômico."
                    ),
                    severidade="alta" if len(emp_ids) >= 3 else "media",
                    score_confianca=min(0.9, 0.5 + len(emp_ids) * 0.1),
                    entidades_envolvidas=emp_ids,
                    status="novo",
                ))

    def _detectar_socios_repetidos(self, relacionamentos: List[Relacionamento], empresas: Dict[str, Empresa]):
        """
        Detecta mesmas pessoas como sócias de múltiplas empresas
        que recebem contratos públicos.
        """
        # Mapeia pessoas para empresas
        pessoa_empresas: Dict[str, List[str]] = defaultdict(list)

        for rel in relacionamentos:
            if rel.tipo == "socio":
                pessoa_empresas[rel.entidade_origem].append(rel.entidade_destino)

        # Se uma pessoa é sócia de várias empresas com contratos
        for pessoa_id, empresas_ids in pessoa_empresas.items():
            if len(empresas_ids) >= 3:
                nomes_empresas = [
                    empresas.get(eid, Empresa(id="", nome="Desconhecida", nome_normalizado="")).nome
                    for eid in empresas_ids
                ]

                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.SOCIO_REPETIDO,
                    titulo="Sócio Repetido em Múltiplas Empresas",
                    descricao=(
                        f"Uma mesma pessoa é sócia de {len(empresas_ids)} empresas "
                        f"com contratos públicos: {', '.join(nomes_empresas[:5])}. "
                        f"Padrão suspeito de possível laranja."
                    ),
                    severidade="alta" if len(empresas_ids) >= 5 else "media",
                    score_confianca=min(0.9, 0.3 + len(empresas_ids) * 0.1),
                    entidades_envolvidas=[pessoa_id] + empresas_ids,
                    status="novo",
                ))

    def _detectar_valores_acima_media(self, documentos: List[Documento]):
        """
        Detecta valores individuais muito acima da média do mercado.
        """
        valores_por_contexto: Dict[str, List[float]] = defaultdict(list)

        for doc in documentos:
            for ent in doc.entidades:
                if ent.tipo == TipoEntidade.VALOR:
                    try:
                        valor = float(ent.normalizado)
                        if valor > 100:
                            # Usa primeiras palavras do contexto como categoria
                            categoria = " ".join(ent.contexto.split()[:5])
                            valores_por_contexto[categoria].append(valor)
                    except ValueError:
                        continue

        for categoria, valores in valores_por_contexto.items():
            if len(valores) < 3:
                continue

            media = statistics.mean(valores)
            mediana = statistics.median(valores)
            try:
                desvio = statistics.stdev(valores)
            except statistics.StatisticsError:
                continue

            if desvio == 0:
                continue

            for valor in valores:
                if valor > mediana + (2 * desvio) and valor > media * 1.5:
                    self.alertas.append(Alerta(
                        id=str(uuid.uuid4()),
                        tipo=TipoAnomalia.VALOR_ACIMA_MEDIA,
                        titulo="Valor Acima da Média",
                        descricao=(
                            f"Valor de R$ {valor:,.2f} está acima da média "
                            f"(média: R$ {media:,.2f}) para a categoria "
                            f"'{categoria[:100]}'."
                        ),
                        severidade="media",
                        score_confianca=0.6,
                        valor_envolvido=valor,
                        status="novo",
                    ))

    def _detectar_pagamento_sem_licitacao(self, documentos: List[Documento], relacionamentos: List[Relacionamento]):
        """
        Detecta pagamentos de valores significativos sem evidência de licitação.
        Pagamentos acima de um limite que não estão associados a licitações.
        """
        limite_sem_licitacao = self.limites.get("fracionamento_valor", 50000) * 0.8

        for doc in documentos:
            # Verifica se o documento menciona licitação
            menciona_licitacao = any(
                ent.tipo == TipoEntidade.LICITACAO for ent in doc.entidades
            )

            if menciona_licitacao:
                continue

            # Busca valores altos sem licitação associada
            for ent in doc.entidades:
                if ent.tipo != TipoEntidade.VALOR:
                    continue
                try:
                    valor = float(ent.normalizado)
                except ValueError:
                    continue

                if valor > limite_sem_licitacao:
                    self.alertas.append(Alerta(
                        id=str(uuid.uuid4()),
                        tipo=TipoAnomalia.PAGAMENTO_SEM_LICITACAO,
                        titulo="Pagamento Sem Licitação",
                        descricao=(
                            f"Valor de R$ {valor:,.2f} sem evidência de processo licitatório. "
                            f"Valores acima de R$ {limite_sem_licitacao:,.2f} geralmente "
                            f"exigem licitação. Contexto: {ent.contexto[:200]}"
                        ),
                        severidade="alta" if valor > limite_sem_licitacao * 2 else "media",
                        score_confianca=0.7,
                        entidades_envolvidas=[ent.id],
                        documentos_relacionados=[doc.fonte],
                        valor_envolvido=valor,
                        status="novo",
                    ))

    def _detectar_prazo_curto(self, documentos: List[Documento], relacionamentos: List[Relacionamento]):
        """
        Detecta contratos com prazos suspeitosamente curtos,
        que podem indicar urgência fabricada para dispensar licitação.
        """
        # Busca relações contratuais com datas próximas
        relacoes_contrato = [r for r in relacionamentos if r.tipo == "contrato"]

        for rel in relacoes_contrato:
            if not rel.data_inicio or not rel.data_fim:
                continue

            prazo_dias = (rel.data_fim - rel.data_inicio).days

            if 0 < prazo_dias < 7:  # Menos de uma semana é suspeito
                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.PRAZO_CURTO,
                    titulo="Prazo de Contrato Suspeitosamente Curto",
                    descricao=(
                        f"Contrato com prazo de apenas {prazo_dias} dia(s). "
                        f"Prazos muito curtos podem indicar urgência fabricada "
                        f"para dispensar licitação. Detalhes: {rel.detalhes}"
                    ),
                    severidade="media",
                    score_confianca=0.6,
                    entidades_envolvidas=[rel.entidade_origem, rel.entidade_destino],
                    status="novo",
                ))

    def _detectar_suspeita_fraude(self, documentos: List[Documento], relacionamentos: List[Relacionamento]):
        """
        Detecta combinações de múltiplos indicadores suspeitos.
        Quanto mais alertas para uma mesma entidade, maior a suspeita.
        """
        # Conta alertas por entidade
        alertas_por_entidade: Dict[str, int] = defaultdict(int)
        for alerta in self.alertas:
            for ent_id in alerta.entidades_envolvidas:
                alertas_por_entidade[ent_id] += 1

        # Se uma entidade acumula múltiplos alertas
        for ent_id, total in alertas_por_entidade.items():
            if total >= 3:
                self.alertas.append(Alerta(
                    id=str(uuid.uuid4()),
                    tipo=TipoAnomalia.SUSPEITA_FRAUDE,
                    titulo="Múltiplos Indicadores de Fraude",
                    descricao=(
                        f"Entidade acumula {total} alertas diferentes. "
                        f"Alta probabilidade de irregularidades."
                    ),
                    severidade="critica",
                    score_confianca=0.8,
                    entidades_envolvidas=[ent_id],
                    status="novo",
                ))

    def _detectar_anomalias_ai(
        self,
        documentos: List[Documento],
        relacionamentos: List[Relacionamento],
        pessoas: Dict[str, Pessoa],
        empresas: Dict[str, Empresa],
    ) -> List[Alerta]:
        """
        Detecta anomalias usando LLM (IA) quando disponível.
        Analisa contexto e padrões que detectores baseados em regras podem perder.
        """
        if not self.ai_manager:
            return []
        
        alertas_ai = []
        
        try:
            # Prepara resumo dos dados para análise
            resumo_dados = self._preparar_resumo_para_ai(documentos, relacionamentos, pessoas, empresas)
            
            # Limita tamanho para não exceder limites da API
            resumo_limitado = resumo_dados[:30000]
            
            resultado = self.ai_manager.analyze_text(
                texto=resumo_limitado,
                task="detect_anomalies",
                temperature=0.4,  # Temperatura moderada para análise
                max_tokens=2500,
            )
            
            if not resultado:
                return []
            
            # Parseia resultado da IA
            alertas_ai = self._parsear_alertas_ai(resultado, documentos)
            
            if alertas_ai:
                logger.info(f"IA gerou {len(alertas_ai)} alertas de anomalias")
            
        except Exception as e:
            logger.error(f"Erro ao detectar anomalias com IA: {e}")
        
        return alertas_ai
    
    def _preparar_resumo_para_ai(
        self,
        documentos: List[Documento],
        relacionamentos: List[Relacionamento],
        pessoas: Dict[str, Pessoa],
        empresas: Dict[str, Empresa],
    ) -> str:
        """Prepara resumo estruturado dos dados para análise pela IA."""
        linhas = ["RESUMO DOS DADOS PARA ANÁLISE DE ANOMALIAS:\n"]
        
        # Resumo de documentos
        linhas.append(f"\nDOCUMENTOS ({len(documentos)}):")
        for doc in documentos[:10]:  # Limita a 10 documentos
            linhas.append(f"- {doc.fonte}")
            for ent in doc.entidades[:5]:
                linhas.append(f"  {ent.tipo.value}: {ent.valor}")
        
        # Resumo de empresas
        linhas.append(f"\nEMPRESAS ({len(empresas)}):")
        for eid, emp in list(empresas.items())[:10]:
            linhas.append(f"- {emp.nome} (CNPJ: {emp.cnpj or 'N/A'})")
            linhas.append(f"  Contratos: {len(emp.contratos)}")
            linhas.append(f"  Capital Social: {emp.capital_social or 'N/A'}")
            if emp.alertas:
                linhas.append(f"  Alertas existentes: {len(emp.alertas)}")
        
        # Resumo de pessoas
        linhas.append(f"\nPESSOAS ({len(pessoas)}):")
        for pid, pes in list(pessoas.items())[:10]:
            linhas.append(f"- {pes.nome} (CPF: {pes.cpf or 'N/A'})")
            linhas.append(f"  Cargos: {', '.join(pes.cargos) if pes.cargos else 'N/A'}")
            linhas.append(f"  Empresas relacionadas: {len(pes.empresas_relacionadas)}")
        
        # Resumo de relacionamentos
        linhas.append(f"\nRELACIONAMENTOS ({len(relacionamentos)}):")
        for rel in relacionamentos[:15]:
            linhas.append(f"- {rel.tipo}: {rel.entidade_origem} -> {rel.entidade_destino}")
            if rel.valor:
                linhas.append(f"  Valor: {rel.valor}")
        
        return "\n".join(linhas)
    
    def _parsear_alertas_ai(self, resultado_ia: str, documentos: List[Documento]) -> List[Alerta]:
        """Parseia alertas retornados pela IA."""
        import json
        
        alertas = []
        
        try:
            # Tenta extrair JSON do resultado
            if "```json" in resultado_ia:
                json_str = resultado_ia.split("```json")[1].split("```")[0].strip()
            elif "```" in resultado_ia:
                json_str = resultado_ia.split("```")[1].split("```")[0].strip()
            else:
                # Se não tem JSON, tenta parsear linha por linha
                linhas = resultado_ia.split('\n')
                for linha in linhas:
                    if '-' in linha and any(word in linha.lower() for word in ['anomalia', 'suspeita', 'irregularidade']):
                        alertas.append(Alerta(
                            id=str(uuid.uuid4()),
                            tipo=TipoAnomalia.SUSPEITA_FRAUDE,
                            titulo="Anomalia Detectada por IA",
                            descricao=linha.strip(),
                            severidade="media",
                            score_confianca=0.7,
                            entidades_envolvidas=[],
                            documentos_relacionados=[d.id for d in documentos],
                            status="novo",
                            metadados={"source": "ai_llm"},
                        ))
                return alertas
            
            dados = json.loads(json_str)
            
            if isinstance(dados, list):
                for item in dados:
                    tipo_str = item.get("tipo", "suspeita_fraude")
                    tipo_map = {
                        "superfaturamento": TipoAnomalia.SUPERFATURAMENTO,
                        "nepotismo": TipoAnomalia.NEPOTISMO,
                        "cartel": TipoAnomalia.CARTEL,
                        "fracionamento": TipoAnomalia.FRACIONAMENTO,
                        "empresa_fantasma": TipoAnomalia.EMPRESA_FANTASMA,
                        "conflito_interesse": TipoAnomalia.CONFLITO_INTERESSE,
                        "pagamento_sem_licitacao": TipoAnomalia.PAGAMENTO_SEM_LICITACAO,
                        "suspeita_fraude": TipoAnomalia.SUSPEITA_FRAUDE,
                    }
                    tipo = tipo_map.get(tipo_str.lower(), TipoAnomalia.SUSPEITA_FRAUDE)
                    
                    severidade_str = item.get("severidade", "media").lower()
                    severidade_map = {
                        "critica": "critica",
                        "alta": "alta",
                        "media": "media",
                        "baixa": "baixa",
                    }
                    severidade = severidade_map.get(severidade_str, "media")
                    
                    alertas.append(Alerta(
                        id=str(uuid.uuid4()),
                        tipo=tipo,
                        titulo=item.get("titulo", "Anomalia Detectada por IA"),
                        descricao=item.get("descricao", ""),
                        severidade=severidade,
                        score_confianca=0.75,
                        entidades_envolvidas=item.get("entidades", []),
                        documentos_relacionados=[d.id for d in documentos],
                        status="novo",
                        metadados={"source": "ai_llm"},
                    ))
        
        except json.JSONDecodeError:
            logger.warning("IA não retornou JSON válido para anomalias")
        except Exception as e:
            logger.error(f"Erro ao parsear alertas da IA: {e}")
        
        return alertas

    def resumo_alertas(self) -> Dict[str, Any]:
        """Resumo dos alertas gerados."""
        tipos = defaultdict(int)
        severidades = defaultdict(int)
        valor_total = 0

        for alerta in self.alertas:
            tipos[alerta.tipo.value] += 1
            severidades[alerta.severidade] += 1
            if alerta.valor_envolvido:
                valor_total += alerta.valor_envolvido

        return {
            "total_alertas": len(self.alertas),
            "por_tipo": dict(tipos),
            "por_severidade": dict(severidades),
            "valor_envolvido_total": valor_total,
            "alertas_criticos": severidades.get("critica", 0),
            "alertas_altos": severidades.get("alta", 0),
        }