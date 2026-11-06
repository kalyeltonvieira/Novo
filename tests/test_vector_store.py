"""
Testes Unitários do Banco Vetorial (VectorStoreManager & RAG)
==============================================================
"""

import pytest
import tempfile
from core.vector_store import VectorStoreManager


def test_adicionar_e_buscar_vector_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        vm = VectorStoreManager(collection_name="test_collection", persist_dir=tmpdir)
        
        vm.adicionar_documento(
            doc_id="doc_1",
            texto="Contrato de prestação de serviços de limpeza urbana no valor de R$ 500.000",
            metadados={"tipo": "contrato", "orgao": "Prefeitura"}
        )
        vm.adicionar_documento(
            doc_id="doc_2",
            texto="Aquisição de material escolar e livros de literatura infantil",
            metadados={"tipo": "compra", "orgao": "Educação"}
        )

        resultados = vm.buscar_similares("limpeza urbana e contratos", top_k=1)
        assert len(resultados) == 1
        assert resultados[0]["id"] == "doc_1"
        assert "limpeza urbana" in resultados[0]["texto"]
