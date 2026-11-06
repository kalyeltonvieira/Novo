"""
Correlacionador - Motor de Relacionamentos
===========================================
Liga entidades extraídas dos documentos, criando uma rede de relacionamentos.
Responde perguntas como:
- Quem contratou quem?
- Quem é sócio de quem?
- Quem recebeu dinheiro?
- Quem assinou / aprovou?
- Quem aparece em múltiplos contratos?
"""

import uuid
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from collections import defaultdict

from .entidades import (
    Documento, EntidadeExtraida, TipoEntidade,
    Relacionamento, Pessoa, Empresa, Contrato
)

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.correlacionador")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.correlacionador")
    metrics = None
    MONITORING_AVAILABLE = False


class Correlacionador:
    """
    Motor de relacionamentos entre entidades extraídas de documentos.
    
    Este módulo cria uma rede de relacionamentos conectando pessoas,
    empresas, contratos e outras entidades identificadas nos documentos.
    
    Métodos de correlação:
    - Correspondência por CNPJ/CPF: Liga entidades com mesmo documento fiscal
    - Co-ocorrência em documentos: Entidades que aparecem juntas
    - Similaridade de nomes: Nomes parecidos podem ser a mesma entidade
    - Padrões relacionais: Contratos, licitações, pagamentos
    - Relações societárias: Empresas com mesmos sócios
    
    Attributes:
        config (Dict[str, Any]): Configurações do correlacionador
        relacionamentos (List[Relacionamento]): Lista de relacionamentos encontrados
        pessoas (Dict[str, Pessoa]): Dicionário de pessoas identificadas
        empresas (Dict[str, Empresa]): Dicionário de empresas identificadas
        contratos (Dict[str, Contrato]): Dicionário de contratos extraídos
    
    Example:
        >>> correlacionador = Correlacionador()
        >>> relacionamentos = correlacionador.processar_documentos(documentos)
        >>> print(f"Relacionamentos: {len(relacionamentos)}")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.relacionamentos: List[Relacionamento] = []
        self.pessoas: Dict[str, Pessoa] = {}
        self.empresas: Dict[str, Empresa] = {}
        self.contratos: Dict[str, Contrato] = {}
        self._entidades_avulsas: List[EntidadeExtraida] = []

    def adicionar_entidade(self, tipo: str, valor: str, metadados: Dict[str, Any]) -> None:
        """
        Adiciona uma entidade avulsa (ex: do OCR em background) e enriquece automaticamente.
        """
        from .entidades import TipoEntidade, EntidadeExtraida
        
        tipo_enum = TipoEntidade.OUTRO
        if tipo.lower() == "empresa" or tipo.lower() == "cnpj":
            tipo_enum = TipoEntidade.EMPRESA if tipo.lower() == "empresa" else TipoEntidade.CNPJ
            
            # Auto-enriquecimento via Receita Federal / APIs
            cnpj_limpo = re.sub(r'[^0-9]', '', metadados.get('cnpj', valor))
            if cnpj_limpo:
                print(f"[CORRELACIONADOR] Auto-enriquecendo CNPJ {cnpj_limpo}...")
                try:
                    from core.integracoes_gov_completo import IntegracoesGovCompleto
                    gov = IntegracoesGovCompleto()
                    # Simula a chamada da Receita Federal
                    dados_receita = gov.receita_cnpj(cnpj_limpo)
                    if dados_receita:
                        metadados['razao_social'] = dados_receita.get('nome')
                        metadados['qsa'] = dados_receita.get('qsa', [])
                        metadados['capital'] = dados_receita.get('capital_social')
                        
                        # Injeta os sócios detectados no QSA diretamente na fila de pessoas
                        for socio in metadados['qsa']:
                            nome_socio = socio.get('nome_socio')
                            if nome_socio:
                                self.adicionar_entidade("pessoa", nome_socio, {"cargo": socio.get('qualificacao_socio')})
                except Exception as e:
                    print(f"[CORRELACIONADOR] Falha no enriquecimento automático: {e}")

        ent = EntidadeExtraida(
            tipo=tipo_enum,
            valor=valor,
            normalizado=valor.upper(),
            documento_id="background_task",
            contexto="Extraído via fila assíncrona",
            confianca=0.9,
            metadados=metadados
        )
        self._entidades_avulsas.append(ent)
        
        # Reprocessa tudo com a nova entidade
        self.processar_documentos([])

    def processar_documentos(self, documentos: List[Documento]) -> List[Relacionamento]:
        """
        Processa uma lista de documentos e extrai relacionamentos.
        
        Executa 6 etapas de correlação:
        1. Correlação por CNPJ/CPF
        2. Co-ocorrência em documentos
        3. Extração de relações contratuais
        4. Correlação por similaridade nominal
        5. Extração de relações societárias
        6. Montagem de entidades estruturadas
        
        Args:
            documentos: Lista de documentos processados com entidades extraídas
        
        Returns:
            Lista de relacionamentos encontrados entre as entidades
        """
        if MONITORING_AVAILABLE and metrics:
            metrics.increment("correlacionador_processar_executado")
        start_time = datetime.now()
        todas_entidades = list(self._entidades_avulsas)
        for doc in documentos:
            todas_entidades.extend(doc.entidades)

        # 1. Relacionamentos por CNPJ/CPF
        relacionamentos_cnpj = self._correlacionar_por_cnpj(todas_entidades)
        self.relacionamentos.extend(relacionamentos_cnpj)

        # 2. Co-ocorrência em documentos
        relacionamentos_coocorrencia = self._correlacionar_por_documento(documentos)
        self.relacionamentos.extend(relacionamentos_coocorrencia)

        # 3. Padrões contratuais
        relacionamentos_contrato = self._extrair_relacoes_contratuais(todas_entidades)
        self.relacionamentos.extend(relacionamentos_contrato)

        # 4. Similaridade nominal
        relacionamentos_similares = self._correlacionar_por_similaridade(todas_entidades)
        self.relacionamentos.extend(relacionamentos_similares)

        # 5. Relações societárias (empresas com mesmos sócios)
        relacoes_societarias = self._extrair_relacoes_societarias(todas_entidades)
        self.relacionamentos.extend(relacoes_societarias)

        # 6. Montar entidades estruturadas
        self._montar_pessoas_e_empresas(todas_entidades)
        self._montar_contratos(todas_entidades)

        duration = (datetime.now() - start_time).total_seconds()
        if MONITORING_AVAILABLE and metrics:
            metrics.record_timing("tempo_correlacao_entidades", duration)
            metrics.increment("relacionamentos_encontrados", value=len(self.relacionamentos))
        logger.info(f"Correlação concluída: {len(self.relacionamentos)} relacionamentos em {duration:.2f}s")

        return self.relacionamentos

    def _correlacionar_por_cnpj(self, entidades: List[EntidadeExtraida]) -> List[Relacionamento]:
        """
        Correlaciona entidades que compartilham o mesmo CNPJ ou CPF.
        
        Agrupa entidades por documento fiscal (CNPJ/CPF) e cria
        relacionamentos entre elas, inferindo o tipo de relação
        baseado no contexto ao redor das menções.
        
        Args:
            entidades: Lista de entidades extraídas dos documentos
        
        Returns:
            Lista de relacionamentos baseados em CNPJ/CPF compartilhado
        """
        relacionamentos = []

        # Agrupa entidades por CNPJ/CPF
        grupos: Dict[str, List[EntidadeExtraida]] = {}
        for ent in entidades:
            if ent.tipo in (TipoEntidade.CNPJ, TipoEntidade.CPF):
                if ent.normalizado not in grupos:
                    grupos[ent.normalizado] = []
                grupos[ent.normalizado].append(ent)

        # Cria relacionamentos
        for documento_id, grupo in grupos.items():
            for i in range(len(grupo)):
                for j in range(i + 1, len(grupo)):
                    # Busca contexto ao redor para determinar tipo de relação
                    tipo_relacao = self._determinar_tipo_relacao(
                        grupo[i].contexto + " " + grupo[j].contexto
                    )

                    rel = Relacionamento(
                        id=str(uuid.uuid4()),
                        tipo=tipo_relacao,
                        entidade_origem=grupo[i].id,
                        entidade_destino=grupo[j].id,
                        tipo_origem=grupo[i].tipo.value,
                        tipo_destino=grupo[j].tipo.value,
                        forca=0.9,
                        detalhes=f"Mesmo {grupo[i].tipo.value}: {documento_id}",
                        documento_id=grupo[i].documento_id or grupo[j].documento_id,
                    )
                    relacionamentos.append(rel)

        return relacionamentos

    def _correlacionar_por_documento(self, documentos: List[Documento]) -> List[Relacionamento]:
        """Correlaciona entidades que aparecem no mesmo documento."""
        relacionamentos = []

        for doc in documentos:
            entidades = doc.entidades
            # Agrupa entidades por tipo para criar relações
            pessoas = [e for e in entidades if e.tipo == TipoEntidade.PESSOA]
            empresas = [e for e in entidades if e.tipo == TipoEntidade.EMPRESA]
            valores = [e for e in entidades if e.tipo == TipoEntidade.VALOR]

            # Relaciona pessoas com empresas no mesmo documento
            for pessoa in pessoas:
                for empresa in empresas:
                    # Verifica proximidade no texto
                    if abs(pessoa.posicao_inicio - empresa.posicao_inicio) < 500:
                        tipo = self._determinar_tipo_relacao(
                            pessoa.contexto + " " + empresa.contexto
                        )
                        rel = Relacionamento(
                            id=str(uuid.uuid4()),
                            tipo=tipo,
                            entidade_origem=pessoa.id,
                            entidade_destino=empresa.id,
                            tipo_origem="pessoa",
                            tipo_destino="empresa",
                            forca=0.7,
                            detalhes=f"Co-ocorrência em: {doc.fonte}",
                            documento_id=pessoa.documento_id,
                        )
                        relacionamentos.append(rel)

            # Relaciona empresas com valores
            for empresa in empresas:
                for valor in valores:
                    if abs(empresa.posicao_inicio - valor.posicao_inicio) < 300:
                        try:
                            valor_float = float(valor.normalizado)
                        except ValueError:
                            valor_float = 0.0

                        rel = Relacionamento(
                            id=str(uuid.uuid4()),
                            tipo="pagamento",
                            entidade_origem=empresa.id,
                            entidade_destino=valor.id,
                            tipo_origem="empresa",
                            tipo_destino="valor",
                            forca=0.6,
                            valor=valor_float,
                            detalhes=f"Valor: {valor.valor} em {doc.fonte}",
                            documento_id=empresa.documento_id,
                        )
                        relacionamentos.append(rel)

        return relacionamentos

    def _extrair_relacoes_contratuais(self, entidades: List[EntidadeExtraida]) -> List[Relacionamento]:
        """Extrai relações do tipo contrato entre órgãos públicos e empresas."""
        relacionamentos = []
        orgaos = [e for e in entidades if e.tipo == TipoEntidade.ORGAO_PUBLICO]
        empresas = [e for e in entidades if e.tipo == TipoEntidade.EMPRESA]
        pessoas = [e for e in entidades if e.tipo == TipoEntidade.PESSOA]

        # Palavras-chave de contratação
        palavras_contrato = {
            "contrato", "contratou", "contratada", "contratante",
            "licitação", "licitou", "vencedor", "adjudicado",
            "empenho", "pagamento", "nota fiscal", "fatura"
        }

        # Verifica contexto para relações contratuais
        for orgao in orgaos:
            for empresa in empresas:
                contexto = (orgao.contexto + " " + empresa.contexto).lower()
                if any(p in contexto for p in palavras_contrato):
                    rel = Relacionamento(
                        id=str(uuid.uuid4()),
                        tipo="contrato",
                        entidade_origem=orgao.id,
                        entidade_destino=empresa.id,
                        tipo_origem="orgao_publico",
                        tipo_destino="empresa",
                        forca=0.8,
                        detalhes=f"Relação contratual detectada",
                        documento_id=orgao.documento_id or empresa.documento_id,
                    )
                    relacionamentos.append(rel)

            # Pessoas que trabalham no órgão
            for pessoa in pessoas:
                contexto = (orgao.contexto + " " + pessoa.contexto).lower()
                cargos = {
                    "secretário", "diretor", "presidente", "coordenador",
                    "gerente", "supervisor", "chefe", "ministro",
                    "prefeito", "governador", "vereador", "deputado"
                }
                if any(c in contexto for c in cargos):
                    rel = Relacionamento(
                        id=str(uuid.uuid4()),
                        tipo="cargo",
                        entidade_origem=pessoa.id,
                        entidade_destino=orgao.id,
                        tipo_origem="pessoa",
                        tipo_destino="orgao_publico",
                        forca=0.75,
                        detalhes=f"Vínculo funcional detectado",
                        documento_id=pessoa.documento_id,
                    )
                    relacionamentos.append(rel)

        return relacionamentos

    def _montar_contratos(self, entidades: List[EntidadeExtraida]):
        """Popula objetos Contrato a partir de entidades extraídas."""
        # Agrupa entidades por documento para encontrar relações contratuais
        docs_grupos = defaultdict(list)
        for ent in entidades:
            docs_grupos[ent.documento_id].append(ent)

        for doc_id, grupo in docs_grupos.items():
            contrato_atual = {}
            for ent in grupo:
                if ent.tipo == TipoEntidade.CONTRATO:
                    contrato_atual["id"] = ent.id
                    num_match = re.search(r"(\d+/\d{4}|\d+)", ent.valor)
                    if num_match:
                        contrato_atual["numero"] = num_match.group(1)
                elif ent.tipo == TipoEntidade.VALOR:
                    try:
                        contrato_atual["valor"] = abs(float(ent.normalizado))
                    except ValueError:
                        pass
                elif ent.tipo == TipoEntidade.ORGAO_PUBLICO:
                    contrato_atual["orgao_contratante"] = ent.valor
                elif ent.tipo == TipoEntidade.EMPRESA and "contratada" not in contrato_atual:
                    contrato_atual["contratada"] = ent.valor
                    if ent.id:
                        contrato_atual["cnpj_contratada"] = ent.id

            if contrato_atual.get("id"):
                contrato = Contrato(
                    id=contrato_atual.get("id", str(uuid.uuid4())),
                    numero=contrato_atual.get("numero"),
                    orgao_contratante=contrato_atual.get("orgao_contratante", ""),
                    contratada=contrato_atual.get("contratada", ""),
                    cnpj_contratada=contrato_atual.get("cnpj_contratada"),
                    valor=contrato_atual.get("valor", 0.0),
                    objeto=contrato_atual.get("objeto", ""),
                )
                if contrato.id not in self.contratos:
                    self.contratos[contrato.id] = contrato

    def _correlacionar_por_similaridade(self, entidades: List[EntidadeExtraida]) -> List[Relacionamento]:
        """Correlaciona entidades com nomes similares usando embeddings (quando disponível) ou Jaccard."""
        relacionamentos = []

        # Tenta carregar modelo de embeddings para similaridade semântica
        use_embeddings = False
        embedding_model = None
        try:
            from sentence_transformers import SentenceTransformer
            embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            use_embeddings = True
        except ImportError:
            pass

        # Agrupa por tipo
        por_tipo = defaultdict(list)
        for ent in entidades:
            por_tipo[ent.tipo.value].append(ent)

        for tipo, lista in por_tipo.items():
            if len(lista) < 2:
                continue

            for i in range(len(lista)):
                for j in range(i + 1, len(lista)):
                    if use_embeddings and embedding_model:
                        # Similaridade por cosseno via embeddings
                        emb1 = embedding_model.encode(lista[i].normalizado[:200])
                        emb2 = embedding_model.encode(lista[j].normalizado[:200])
                        import numpy as np
                        similaridade = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
                    else:
                        # Fallback: similaridade Jaccard
                        similaridade = self._calcular_similaridade(
                            lista[i].normalizado,
                            lista[j].normalizado
                        )

                    if similaridade > 0.85 and similaridade < 1.0:
                        rel = Relacionamento(
                            id=str(uuid.uuid4()),
                            tipo="similaridade",
                            entidade_origem=lista[i].id,
                            entidade_destino=lista[j].id,
                            tipo_origem=tipo,
                            tipo_destino=tipo,
                            forca=similaridade,
                            detalhes=f"Similaridade: {similaridade:.2%}",
                        )
                        relacionamentos.append(rel)

        return relacionamentos

    def _extrair_relacoes_societarias(self, entidades: List[EntidadeExtraida]) -> List[Relacionamento]:
        """Identifica relações societárias entre pessoas e empresas."""
        relacionamentos = []
        pessoas = [e for e in entidades if e.tipo == TipoEntidade.PESSOA]
        empresas = [e for e in entidades if e.tipo == TipoEntidade.EMPRESA]

        palavras_socio = {
            "sócio", "socia", "proprietário", "proprietaria",
            "diretor", "presidente", "CEO", "fundador",
            "acionista", "quotista", "administrador"
        }

        for pessoa in pessoas:
            for empresa in empresas:
                contexto = (pessoa.contexto + " " + empresa.contexto).lower()
                if any(p in contexto for p in palavras_socio):
                    rel = Relacionamento(
                        id=str(uuid.uuid4()),
                        tipo="socio",
                        entidade_origem=pessoa.id,
                        entidade_destino=empresa.id,
                        tipo_origem="pessoa",
                        tipo_destino="empresa",
                        forca=0.85,
                        detalhes=f"Relação societária detectada",
                        documento_id=pessoa.documento_id or empresa.documento_id,
                    )
                    relacionamentos.append(rel)

        return relacionamentos

    def _montar_pessoas_e_empresas(self, entidades: List[EntidadeExtraida]):
        """Constrói objetos Pessoa e Empresa a partir das entidades extraídas."""
        # Conjuntos de cargos conhecidos para extrair do contexto
        cargos_conhecidos = {
            "secretário", "secretaria", "diretor", "diretora", "presidente",
            "coordenador", "coordenadora", "gerente", "supervisor", "chefe",
            "ministro", "prefeito", "prefeita", "governador", "governadora",
            "vereador", "vereadora", "deputado", "deputada", "senador",
            "senadora", "procurador", "procuradora", "advogado", "advogada",
        }

        for ent in entidades:
            if ent.tipo == TipoEntidade.PESSOA:
                if ent.id not in self.pessoas:
                    self.pessoas[ent.id] = Pessoa(
                        id=ent.id,
                        nome=ent.valor,
                        nome_normalizado=ent.normalizado,
                    )
                pessoa = self.pessoas[ent.id]
                # Extrai cargos do contexto
                contexto_lower = ent.contexto.lower()
                for cargo in cargos_conhecidos:
                    if cargo in contexto_lower and cargo not in pessoa.cargos:
                        pessoa.cargos.append(cargo)

            elif ent.tipo == TipoEntidade.EMPRESA:
                if ent.id not in self.empresas:
                    self.empresas[ent.id] = Empresa(
                        id=ent.id,
                        nome=ent.valor,
                        nome_normalizado=ent.normalizado,
                    )
                empresa = self.empresas[ent.id]

        # Enriquece empresas com CNPJ e endereço a partir de entidades próximas
        for ent in entidades:
            if ent.tipo == TipoEntidade.EMPRESA:
                empresa = self.empresas.get(ent.id)
                if not empresa:
                    continue
                # Busca CNPJ/CPF/endereço no contexto da empresa
                for outra in entidades:
                    if outra.documento_id != ent.documento_id:
                        continue
                    if abs(outra.posicao_inicio - ent.posicao_inicio) > 300:
                        continue
                    if outra.tipo == TipoEntidade.CNPJ and not empresa.cnpj:
                        empresa.cnpj = outra.normalizado
                    elif outra.tipo == TipoEntidade.ENDERECO and not empresa.endereco:
                        empresa.endereco = outra.valor

        # Enriquece pessoas com CPF a partir de entidades próximas
        for ent in entidades:
            if ent.tipo == TipoEntidade.PESSOA:
                pessoa = self.pessoas.get(ent.id)
                if not pessoa or pessoa.cpf:
                    continue
                for outra in entidades:
                    if outra.documento_id != ent.documento_id:
                        continue
                    if abs(outra.posicao_inicio - ent.posicao_inicio) > 200:
                        continue
                    if outra.tipo == TipoEntidade.CPF and not pessoa.cpf:
                        pessoa.cpf = outra.normalizado

    def _determinar_tipo_relacao(self, contexto: str) -> str:
        """Determina o tipo de relação baseado no contexto."""
        contexto = contexto.lower()

        mapa = {
            "contrato": ["contrato", "contratou", "contratada", "contratante"],
            "socio": ["sócio", "socia", "proprietário", "societário"],
            "parente": ["filho", "filha", "irmão", "irmã", "primo", "tio", "pai", "mãe"],
            "licitacao": ["licitação", "licitou", "participou", "concorrência"],
            "pagamento": ["pagamento", "recebeu", "pago", "transferência"],
            "cargo": ["nomeado", "exonerado", "designado", "cargo"],
            "endereco": ["mesmo endereço", "sede", "matriz", "filial"],
        }

        for tipo, palavras in mapa.items():
            if any(p in contexto for p in palavras):
                return tipo

        return "co_ocorrencia"

    def _calcular_similaridade(self, texto1: str, texto2: str) -> float:
        """Calcula similaridade entre dois textos normalizados."""
        if not texto1 or not texto2:
            return 0.0

        # Distância de Levenshtein simplificada
        set1 = set(texto1.split())
        set2 = set(texto2.split())

        if not set1 or not set2:
            return 0.0

        intersecao = set1 & set2
        uniao = set1 | set2

        if not uniao:
            return 0.0

        return len(intersecao) / len(uniao)

    def get_grafo_relacionamentos(self) -> Dict[str, Any]:
        """Retorna o grafo de relacionamentos para visualização."""
        nodes = set()
        edges = []

        for rel in self.relacionamentos:
            nodes.add(rel.entidade_origem)
            nodes.add(rel.entidade_destino)
            edges.append({
                "source": rel.entidade_origem,
                "target": rel.entidade_destino,
                "type": rel.tipo,
                "weight": rel.forca,
                "value": rel.valor,
            })

        return {
            "nodes": list(nodes),
            "edges": edges,
        }

    def resumo_correlacoes(self) -> Dict[str, Any]:
        """Resumo das correlações encontradas."""
        tipos = defaultdict(int)
        for rel in self.relacionamentos:
            tipos[rel.tipo] += 1

        return {
            "total_relacionamentos": len(self.relacionamentos),
            "total_pessoas": len(self.pessoas),
            "total_empresas": len(self.empresas),
            "por_tipo": dict(tipos),
        }

    def calcular_centralidade_laranjas(self) -> List[Dict[str, Any]]:
        """
        Calcula a centralidade de intermediação (Betweenness Centrality) dos nós do grafo
        para identificar "Laranjas" (Pessoas ou empresas que conectam muitos clusters isolados).
        (Simulação de NetworkX).
        """
        grafo = self.get_grafo_relacionamentos()
        nodes = grafo.get("nodes", [])
        edges = grafo.get("edges", [])
        
        if not edges:
            return []
            
        # Simula o cálculo de betweenness centrality contando quantas arestas passam por um nó
        score_nodes = defaultdict(int)
        for e in edges:
            score_nodes[e['source']] += 1
            score_nodes[e['target']] += 1
            
        # Pessoas físicas conectadas a mais de 3 empresas/contratos distintos
        # têm altíssima chance de ser um "hub" laranja.
        possiveis_laranjas = []
        for n, score in score_nodes.items():
            if score >= 3:
                # Verifica se é pessoa física (heurística básica por ausência de LTDA)
                if isinstance(n, str) and not any(ext in n.upper() for ext in ["LTDA", "S.A", "INC", "PREFEITURA"]):
                    possiveis_laranjas.append({
                        "nome": n,
                        "centralidade_score": score * 10,  # Fator mock de Betweenness
                        "motivo": f"Conecta {score} entidades diferentes no grafo (Possível Hub/Testa de Ferro)."
                    })
                    
        # Ordena pelos de maior centralidade
        possiveis_laranjas.sort(key=lambda x: x["centralidade_score"], reverse=True)
        return possiveis_laranjas