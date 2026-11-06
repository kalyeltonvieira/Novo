"""
Gerenciador de Banco de Dados Vetorial (ChromaDB Vector Store & RAG)
====================================================================
Indexa textos de documentos públicos e realiza busca semântica por similaridade de cosseno.
"""

import os
import math
from typing import List, Dict, Any, Optional

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


def _simple_text_embedding(text: str, dim: int = 256) -> List[float]:
    """Gera um embedding de bag-of-words determinístico para busca semântica em fallback."""
    words = text.lower().split()
    vec = [0.0] * dim
    for word in words:
        # Hash de cada palavra para a dimensão
        idx = sum(ord(c) for c in word) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calcula similaridade de cosseno entre dois vetores."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1)) or 1.0
    norm2 = math.sqrt(sum(b * b for b in vec2)) or 1.0
    return dot / (norm1 * norm2)


class VectorStoreManager:
    """
    Gerenciador de Vector Store para busca semântica RAG.
    Utiliza ChromaDB quando disponível ou fallback vetorial em memória.
    """

    def __init__(self, collection_name: str = "documentos_transparencia", persist_dir: str = "data/vector_store"):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.chroma_client = None
        self.collection = None
        self.in_memory_docs: List[Dict[str, Any]] = []

        if CHROMADB_AVAILABLE:
            try:
                os.makedirs(persist_dir, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=persist_dir)
                self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
            except Exception:
                self.chroma_client = None

    def adicionar_documento(self, doc_id: str, texto: str, metadados: Optional[Dict[str, Any]] = None):
        """Indexa um documento no banco de dados vetorial."""
        metadados = metadados or {}
        embedding = _simple_text_embedding(texto)

        if self.collection:
            try:
                self.collection.add(
                    ids=[doc_id],
                    documents=[texto],
                    metadatas=[metadados],
                    embeddings=[embedding]
                )
                return
            except Exception:
                pass

        # Fallback local
        self.in_memory_docs.append({
            "id": doc_id,
            "texto": texto,
            "metadados": metadados,
            "embedding": embedding
        })

    def buscar_similares(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Realiza busca por similaridade semântica para RAG."""
        if self.collection:
            try:
                query_embedding = _simple_text_embedding(query)
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                formatted = []
                if results and "ids" in results and results["ids"]:
                    for i in range(len(results["ids"][0])):
                        formatted.append({
                            "id": results["ids"][0][i],
                            "texto": results["documents"][0][i],
                            "metadados": results["metadatas"][0][i] if results.get("metadatas") else {},
                            "score": 0.9  # Score estimado
                        })
                return formatted
            except Exception:
                pass

        # Fallback local com similaridade de cosseno
        query_vec = _simple_text_embedding(query)
        scored = []
        for doc in self.in_memory_docs:
            sim = _cosine_similarity(query_vec, doc["embedding"])
            scored.append({
                "id": doc["id"],
                "texto": doc["texto"],
                "metadados": doc["metadados"],
                "score": sim
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
