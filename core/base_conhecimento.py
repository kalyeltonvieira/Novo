"""
Base de Conhecimento - Graph Database
======================================
Armazena entidades e relacionamentos em um grafo (NetworkX).
Permite consultas complexas como:
- Quem são os sócios desta empresa?
- Quais contratos esta pessoa tem?
- Qual a rede de relacionamentos?
- Caminho entre duas entidades
"""

import json
import uuid
import os
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict

from .entidades import (
    Documento, EntidadeExtraida, TipoEntidade,
    Relacionamento, Alerta, Pessoa, Empresa, Contrato, Relatorio
)

# Importação do sistema de monitoring centralizado
try:
    from utils.monitoring import get_logger, get_metrics
    logger = get_logger("core.base_conhecimento")
    metrics = get_metrics()
    MONITORING_AVAILABLE = True
except ImportError:
    import logging
    logger = logging.getLogger("ia_analisadora.base")
    metrics = None
    MONITORING_AVAILABLE = False


class BaseConhecimento:
    """
    Base de Conhecimento em Grafo usando NetworkX.
    
    Este módulo armazena entidades e relacionamentos em um grafo,
    permitindo consultas complexas como vizinhança, caminhos entre
    entidades e estatísticas da rede de relacionamentos.
    
    Funcionalidades:
    - Armazenamento de entidades (nós) e relacionamentos (arestas)
    - Consulta de vizinhança de uma entidade
    - Busca de caminhos entre entidades
    - Estatísticas do grafo (graus, centralidade, etc.)
    - Persistência em disco (JSON)
    
    Attributes:
        caminho_db (str): Caminho para armazenamento do banco de dados
        graph (networkx.Graph): Grafo NetworkX com entidades e relacionamentos
    
    Example:
        >>> base = BaseConhecimento("data/conhecimento")
        >>> base.adicionar_entidades(entidades)
        >>> base.adicionar_relacionamentos(relacionamentos)
        >>> base.salvar()
        >>> vizinhos = base.consultar_vizinhanca("entidade_id")
    """

    def __init__(self, caminho_db: Optional[str] = None) -> None:
        self.caminho_db = caminho_db or os.path.join("data", "conhecimento")
        self.graph = None
        self._inicializar_grafo()

    def _inicializar_grafo(self) -> None:
        """
        Inicializa o grafo NetworkX.
        
        Tenta importar e criar um grafo NetworkX. Se não estiver disponível,
        registra um warning e define graph como None.
        """
        try:
            import networkx as nx
            self.graph = nx.Graph()
        except ImportError:
            logger.warning("networkx não instalado. Use: pip install networkx")
            self.graph = None

    def adicionar_entidades(self, entidades: List[EntidadeExtraida]) -> None:
        """
        Adiciona entidades como nós ao grafo.
        
        Args:
            entidades: Lista de entidades a serem adicionadas
        
        Cada entidade é adicionada como um nó com atributos:
        - tipo: Tipo da entidade (pessoa, empresa, etc.)
        - valor: Valor original da entidade
        - normalizado: Valor normalizado
        - confianca: Confiança da extração
        - contexto: Contexto ao redor (primeiros 200 caracteres)
        """
        if self.graph is None:
            return

        for ent in entidades:
            self.graph.add_node(
                ent.id,
                tipo=ent.tipo.value,
                valor=ent.valor,
                normalizado=ent.normalizado,
                confianca=ent.confianca,
                contexto=ent.contexto[:200],
            )

    def adicionar_relacionamentos(self, relacionamentos: List[Relacionamento]) -> None:
        """
        Adiciona relacionamentos como arestas ao grafo.
        
        Args:
            relacionamentos: Lista de relacionamentos a serem adicionados
        
        Cada relacionamento é adicionado como uma aresta com atributos:
        - tipo: Tipo do relacionamento (socio, contrato, etc.)
        - forca: Força do relacionamento (0-1)
        - valor: Valor envolvido (se aplicável)
        - detalhes: Detalhes do relacionamento (primeiros 200 caracteres)
        """
        if self.graph is None:
            return

        for rel in relacionamentos:
            self.graph.add_edge(
                rel.entidade_origem,
                rel.entidade_destino,
                tipo=rel.tipo,
                forca=rel.forca,
                valor=rel.valor,
                detalhes=rel.detalhes[:200],
            )

    def adicionar_pessoas(self, pessoas: Dict[str, Pessoa]):
        """Adiciona/atualiza pessoas no grafo."""
        if self.graph is None:
            return

        for pid, pessoa in pessoas.items():
            if self.graph.has_node(pid):
                self.graph.nodes[pid].update({
                    "nome": pessoa.nome,
                    "nome_normalizado": pessoa.nome_normalizado,
                    "cpf": pessoa.cpf,
                    "cargos": pessoa.cargos,
                    "tipo_entidade": "pessoa",
                })
            else:
                self.graph.add_node(
                    pid,
                    tipo="pessoa",
                    tipo_entidade="pessoa",
                    nome=pessoa.nome,
                    nome_normalizado=pessoa.nome_normalizado,
                    cpf=pessoa.cpf,
                    cargos=pessoa.cargos,
                )

    def adicionar_empresas(self, empresas: Dict[str, Empresa]):
        """Adiciona/atualiza empresas no grafo."""
        if self.graph is None:
            return

        for eid, empresa in empresas.items():
            if self.graph.has_node(eid):
                self.graph.nodes[eid].update({
                    "nome": empresa.nome,
                    "nome_normalizado": empresa.nome_normalizado,
                    "cnpj": empresa.cnpj,
                    "capital_social": empresa.capital_social,
                    "score_suspeita": empresa.score_suspeita,
                    "tipo_entidade": "empresa",
                })
            else:
                self.graph.add_node(
                    eid,
                    tipo="empresa",
                    tipo_entidade="empresa",
                    nome=empresa.nome,
                    nome_normalizado=empresa.nome_normalizado,
                    cnpj=empresa.cnpj,
                    capital_social=empresa.capital_social,
                    score_suspeita=empresa.score_suspeita,
                )

    def adicionar_alertas(self, alertas: List[Alerta]):
        """Adiciona alertas como nós no grafo."""
        if self.graph is None:
            return

        for alerta in alertas:
            self.graph.add_node(
                alerta.id,
                tipo="alerta",
                tipo_anomalia=alerta.tipo.value,
                titulo=alerta.titulo,
                descricao=alerta.descricao[:200],
                severidade=alerta.severidade,
                score_confianca=alerta.score_confianca,
                status=alerta.status,
                data_deteccao=alerta.data_deteccao.isoformat(),
            )

            # Conecta alerta às entidades envolvidas
            for ent_id in alerta.entidades_envolvidas:
                if self.graph.has_node(ent_id):
                    self.graph.add_edge(
                        alerta.id,
                        ent_id,
                        tipo="alerta_entidade",
                        forca=alerta.score_confianca,
                    )

    def consultar_vizinhanca(self, entidade_id: str, profundidade: int = 2) -> Dict[str, Any]:
        """
        Retorna a vizinhança de uma entidade no grafo.
        Similar a "Quem conhece quem?"
        """
        if self.graph is None or not self.graph.has_node(entidade_id):
            return {"entidade": None, "conexoes": []}

        from networkx import ego_graph
        subgrafo = ego_graph(self.graph, entidade_id, radius=profundidade)

        conexoes = []
        for node in subgrafo.nodes():
            if node == entidade_id:
                continue
            dados = dict(subgrafo.nodes[node])
            aresta = self.graph.get_edge_data(entidade_id, node, default={})
            conexoes.append({
                "id": node,
                "dados": dados,
                "aresta": dict(aresta) if aresta else {},
            })

        return {
            "entidade": dict(self.graph.nodes[entidade_id]),
            "conexoes": conexoes,
            "total_conexoes": len(conexoes),
        }

    def consultar_caminho(self, entidade1: str, entidade2: str) -> List[Dict[str, Any]]:
        """
        Encontra o caminho mais curto entre duas entidades.
        """
        if self.graph is None:
            return []

        import networkx as nx
        try:
            caminho = nx.shortest_path(self.graph, entidade1, entidade2)
            resultado = []
            for i in range(len(caminho) - 1):
                node_a = caminho[i]
                node_b = caminho[i + 1]
                aresta = self.graph.get_edge_data(node_a, node_b, default={})
                resultado.append({
                    "entidade_origem": node_a,
                    "entidade_destino": node_b,
                    "relacao": aresta.get("tipo", "desconhecido"),
                    "forca": aresta.get("forca", 0),
                })
            return resultado
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        except Exception:
            return []

    def consultar_entidades_por_tipo(self, tipo: str) -> List[Dict[str, Any]]:
        """Retorna todas entidades de um tipo específico."""
        if self.graph is None:
            return []

        resultado = []
        for node, dados in self.graph.nodes(data=True):
            if dados.get("tipo") == tipo or dados.get("tipo_entidade") == tipo:
                resultado.append({"id": node, **dados})
        return resultado

    def consultar_relacionamentos_por_tipo(self, tipo: str) -> List[Dict[str, Any]]:
        """Retorna todos relacionamentos de um tipo específico."""
        if self.graph is None:
            return []

        resultado = []
        for u, v, dados in self.graph.edges(data=True):
            if dados.get("tipo") == tipo:
                resultado.append({
                    "origem": u,
                    "destino": v,
                    **dados,
                })
        return resultado

    def consultar_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas da base de conhecimento."""
        if self.graph is None:
            return {"total_entidades": 0, "total_relacionamentos": 0}

        tipos_entidades = defaultdict(int)
        tipos_relacoes = defaultdict(int)

        for _, dados in self.graph.nodes(data=True):
            tipo = dados.get("tipo") or dados.get("tipo_entidade", "desconhecido")
            tipos_entidades[tipo] += 1

        for _, _, dados in self.graph.edges(data=True):
            tipo = dados.get("tipo", "desconhecido")
            tipos_relacoes[tipo] += 1

        return {
            "total_entidades": self.graph.number_of_nodes(),
            "total_relacionamentos": self.graph.number_of_edges(),
            "entidades_por_tipo": dict(tipos_entidades),
            "relacoes_por_tipo": dict(tipos_relacoes),
        }

    def exportar_para_vis(self) -> Dict[str, List]:
        """
        Exporta o grafo para visualização (formato vis.js ou similar).
        Retorna {nodes: [], edges: []}
        """
        if self.graph is None:
            return {"nodes": [], "edges": []}

        nodes = []
        for node, dados in self.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "label": dados.get("nome", dados.get("valor", node[:8])),
                "group": dados.get("tipo", dados.get("tipo_entidade", "outro")),
                "title": json.dumps(dados, default=str),
                "size": min(30, 10 + len(list(self.graph.neighbors(node))) * 3),
            })

        edges = []
        for u, v, dados in self.graph.edges(data=True):
            edges.append({
                "from": u,
                "to": v,
                "label": dados.get("tipo", ""),
                "width": min(5, max(1, dados.get("forca", 0.5) * 5)),
                "title": dados.get("detalhes", dados.get("tipo", "")),
            })

        return {"nodes": nodes, "edges": edges}

    def salvar(self, caminho: Optional[str] = None):
        """Salva o grafo em disco."""
        if self.graph is None:
            return

        caminho = caminho or self.caminho_db
        os.makedirs(os.path.dirname(caminho), exist_ok=True)

        # Salva como JSON do NetworkX
        from networkx.readwrite import json_graph
        dados = json_graph.node_link_data(self.graph)
        with open(f"{caminho}.json", "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)

    def carregar(self, caminho: Optional[str] = None):
        """Carrega o grafo do disco."""
        import networkx as nx
        from networkx.readwrite import json_graph

        caminho = caminho or self.caminho_db
        if not os.path.exists(f"{caminho}.json"):
            return

        with open(f"{caminho}.json", "r", encoding="utf-8") as f:
            dados = json.load(f)

        self.graph = json_graph.node_link_graph(dados)

    def salvar_documentos(self, documentos: List[Documento]) -> str:
        """
        Persiste documentos processados em disco (JSON).
        Retorna o caminho do arquivo salvo.
        """
        caminho = f"{self.caminho_db}_documentos.json"
        os.makedirs(os.path.dirname(caminho), exist_ok=True)

        dados = []
        for doc in documentos:
            dados.append({
                "id": doc.id,
                "fonte": doc.fonte,
                "tipo": doc.tipo.value,
                "conteudo_original": doc.conteudo_original[:10000],  # Limita tamanho
                "conteudo_processado": doc.conteudo_processado[:10000],
                "metadados": doc.metadados,
                "data_processamento": doc.data_processamento.isoformat(),
                "data_documento": doc.data_documento.isoformat() if doc.data_documento else None,
                "orgao_origem": doc.orgao_origem,
                "url_origem": doc.url_origem,
                "hash_documento": doc.hash_documento,
                "resumo": doc.resumo,
                "confianca_ocr": doc.confianca_ocr,
                "entidades": [
                    {
                        "id": ent.id,
                        "tipo": ent.tipo.value,
                        "valor": ent.valor,
                        "normalizado": ent.normalizado,
                        "contexto": ent.contexto[:200],
                        "confianca": ent.confianca,
                        "posicao_inicio": ent.posicao_inicio,
                        "posicao_fim": ent.posicao_fim,
                        "documento_id": ent.documento_id,
                    }
                    for ent in doc.entidades
                ],
            })

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)

        return caminho

    def carregar_documentos(self) -> List[Documento]:
        """
        Carrega documentos persistidos anteriormente.
        """
        from .entidades import TipoDocumento, EntidadeExtraida, TipoEntidade
        caminho = f"{self.caminho_db}_documentos.json"
        if not os.path.exists(caminho):
            return []

        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        documentos = []
        for d in dados:
            entidades = []
            for ent_data in d.get("entidades", []):
                try:
                    tipo_ent = TipoEntidade(ent_data["tipo"])
                except ValueError:
                    tipo_ent = TipoEntidade.OBJETO
                entidades.append(EntidadeExtraida(
                    id=ent_data["id"],
                    tipo=tipo_ent,
                    valor=ent_data["valor"],
                    normalizado=ent_data["normalizado"],
                    contexto=ent_data.get("contexto", ""),
                    confianca=ent_data.get("confianca", 1.0),
                    posicao_inicio=ent_data.get("posicao_inicio", 0),
                    posicao_fim=ent_data.get("posicao_fim", 0),
                    documento_id=ent_data.get("documento_id"),
                ))

            try:
                tipo_doc = TipoDocumento(d["tipo"])
            except ValueError:
                tipo_doc = TipoDocumento.TEXTO

            data_proc = datetime.fromisoformat(d["data_processamento"]) if d.get("data_processamento") else datetime.now()
            data_doc = datetime.fromisoformat(d["data_documento"]) if d.get("data_documento") else None

            documentos.append(Documento(
                id=d["id"],
                fonte=d["fonte"],
                tipo=tipo_doc,
                conteudo_original=d.get("conteudo_original", ""),
                conteudo_processado=d.get("conteudo_processado", ""),
                metadados=d.get("metadados", {}),
                data_processamento=data_proc,
                data_documento=data_doc,
                orgao_origem=d.get("orgao_origem"),
                url_origem=d.get("url_origem"),
                hash_documento=d.get("hash_documento"),
                entidades=entidades,
                resumo=d.get("resumo"),
                confianca_ocr=d.get("confianca_ocr", 0.0),
            ))

        return documentos

    def buscar_semantica(self, texto: str, limite: int = 20) -> List[Dict[str, Any]]:
        """
        Busca entidades por similaridade de texto (básica).
        """
        if self.graph is None:
            return []

        texto = texto.lower()
        resultados = []

        for node, dados in self.graph.nodes(data=True):
            score = 0
            campos_busca = [
                dados.get("nome", ""),
                dados.get("valor", ""),
                dados.get("normalizado", ""),
                dados.get("contexto", ""),
            ]

            for campo in campos_busca:
                if texto in campo.lower():
                    score += 1
                # Palavras individuais
                palavras_texto = set(texto.split())
                palavras_campo = set(campo.lower().split())
                score += len(palavras_texto & palavras_campo) * 0.5

            if score > 0:
                resultados.append({
                    "id": node,
                    "dados": dados,
                    "score": score,
                })

        resultados.sort(key=lambda x: -x["score"])
        return resultados[:limite]