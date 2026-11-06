"""
Testes unitários para utils/cache_manager.py
"""
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from utils.cache_manager import CacheManager, EmbeddingCache, AIResponseCache, GovAPICache, get_gov_api_cache
from datetime import datetime, timedelta


class TestCacheManager:
    """Testes do gerenciador de cache."""

    def test_criar_cache_manager(self):
        """Testa criação de cache manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            assert str(cache.cache_dir) == tmpdir
            assert cache.ttl == timedelta(hours=24)

    def test_cache_manager_ttl_custom(self):
        """Testa TTL customizado."""
        cache = CacheManager(ttl_hours=12)
        assert cache.ttl == timedelta(hours=12)

    def test_cache_set_get(self):
        """Testa armazenamento e recuperação."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            cache.set("chave_teste", {"valor": 123})
            resultado = cache.get("chave_teste")
            assert resultado == {"valor": 123}

    def test_cache_get_inexistente(self):
        """Testa recuperação de chave inexistente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            resultado = cache.get("chave_inexistente")
            assert resultado is None

    def test_cache_delete(self):
        """Testa exclusão de chave."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            cache.set("chave_teste", "valor")
            cache.delete("chave_teste")
            resultado = cache.get("chave_teste")
            assert resultado is None

    def test_cache_clear(self):
        """Testa limpeza completa."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            cache.set("chave1", "valor1")
            cache.set("chave2", "valor2")
            cache.clear()
            assert cache.get("chave1") is None
            assert cache.get("chave2") is None

    def test_cache_key_generation(self):
        """Testa geração de chave de cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            key1 = cache._get_cache_key("teste")
            key2 = cache._get_cache_key("teste")
            assert key1 == key2
            key3 = cache._get_cache_key("outro")
            assert key1 != key3

    def test_cache_stats(self):
        """Testa estatísticas do cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(cache_dir=tmpdir)
            cache.set("chave1", {"data": "valor1"})
            cache.set("chave2", {"data": "valor2"})
            stats = cache.get_stats()
            assert stats["total_entries"] == 2
            assert stats["total_size_bytes"] > 0


class TestEmbeddingCache:
    """Testes do cache de embeddings."""

    def test_criar_embedding_cache(self):
        """Testa criação de cache de embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(CacheManager(cache_dir=tmpdir))
            assert cache.cache is not None

    def test_embedding_set_get(self):
        """Testa armazenamento e recuperação de embedding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(CacheManager(cache_dir=tmpdir))
            embedding = [0.1, 0.2, 0.3, 0.4]
            cache.set_embedding("texto teste", embedding)
            resultado = cache.get_embedding("texto teste")
            assert resultado == embedding

    def test_embedding_batch(self):
        """Testa operações em lote."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(CacheManager(cache_dir=tmpdir))
            embeddings = {
                "texto1": [0.1, 0.2],
                "texto2": [0.3, 0.4],
            }
            cache.set_embeddings_batch(embeddings)
            resultado = cache.get_embeddings_batch(["texto1", "texto2"])
            assert resultado["texto1"] == [0.1, 0.2]
            assert resultado["texto2"] == [0.3, 0.4]


class TestAIResponseCache:
    """Testes do cache de respostas de IA."""

    def test_criar_ai_cache(self):
        """Testa criação de cache de IA."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AIResponseCache(CacheManager(cache_dir=tmpdir))
            assert cache.cache is not None

    def test_ai_response_set_get(self):
        """Testa armazenamento e recuperação de resposta."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AIResponseCache(CacheManager(cache_dir=tmpdir))
            response = {"text": "Resposta de teste", "tokens": 10}
            cache.set_response("prompt teste", "openai", "gpt-4", response)
            resultado = cache.get_response("prompt teste", "openai", "gpt-4")
            assert resultado == response

    def test_ai_response_com_temperature(self):
        """Testa cache com temperatura diferente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = AIResponseCache(CacheManager(cache_dir=tmpdir))
            response = {"text": "Resposta"}
            cache.set_response("prompt", "openai", "gpt-4", response, temperature=0.5)
            resultado = cache.get_response("prompt", "openai", "gpt-4", temperature=0.5)
            assert resultado is not None


class TestGovAPICache:
    """Testes do cache de APIs governamentais."""

    def test_criar_gov_api_cache(self):
        """Testa criação de cache de APIs governamentais."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GovAPICache(CacheManager(cache_dir=tmpdir))
            assert cache.cache is not None
            assert cache.stats == {"hits": 0, "misses": 0, "by_api_type": {}}

    def test_gov_api_set_get(self):
        """Testa armazenamento e recuperação de resposta de API."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GovAPICache(CacheManager(cache_dir=tmpdir))
            response = {"data": "dados de teste"}
            cache.set_api_response("pncp", "/licitacoes", response, {"pagina": 1}, api_type="licitacao")
            resultado = cache.get_api_response("pncp", "/licitacoes", {"pagina": 1}, api_type="licitacao")
            assert resultado["response"] == response

    def test_gov_api_cache_miss(self):
        """Testa cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GovAPICache(CacheManager(cache_dir=tmpdir))
            resultado = cache.get_api_response("pncp", "/licitacoes", {"pagina": 1})
            assert resultado is None
            assert cache.stats["misses"] == 1

    def test_gov_api_cache_hit(self):
        """Testa cache hit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GovAPICache(CacheManager(cache_dir=tmpdir))
            response = {"data": "dados"}
            cache.set_api_response("pncp", "/licitacoes", response)
            resultado = cache.get_api_response("pncp", "/licitacoes")
            assert resultado is not None
            assert cache.stats["hits"] == 1

    def test_gov_api_ttl_types(self):
        """Testa diferentes tipos de TTL."""
        assert GovAPICache.API_TTLS["cadastral"] == timedelta(hours=24)
        assert GovAPICache.API_TTLS["licitacao"] == timedelta(hours=1)
        assert GovAPICache.API_TTLS["realtime"] == timedelta(minutes=5)

    def test_gov_api_invalidate(self):
        """Testa invalidação de API específica."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GovAPICache(CacheManager(cache_dir=tmpdir))
            cache.set_api_response("pncp", "/licitacoes", {"data": "1"})
            cache.set_api_response("cgu", "/despesas", {"data": "2"})
            cache.invalidate_api("pncp")
            assert cache.get_api_response("pncp", "/licitacoes") is None
            assert cache.get_api_response("cgu", "/despesas") is not None

    def test_gov_api_stats(self):
        """Testa estatísticas do cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GovAPICache(CacheManager(cache_dir=tmpdir))
            response = {"data": "dados"}
            cache.set_api_response("pncp", "/licitacoes", response)
            cache.get_api_response("pncp", "/licitacoes")  # Hit
            cache.get_api_response("pncp", "/contratos")  # Miss
            stats = cache.get_stats()
            assert stats["total_hits"] == 1
            assert stats["total_misses"] == 1
            assert stats["hit_rate_percent"] == 50.0

    def test_gov_api_clear(self):
        """Testa limpeza do cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GovAPICache(CacheManager(cache_dir=tmpdir))
            cache.set_api_response("pncp", "/licitacoes", {"data": "dados"})
            cache.clear()
            assert cache.stats == {"hits": 0, "misses": 0, "by_api_type": {}}


class TestGlobalGovAPICache:
    """Testes da função global de cache."""

    def test_get_gov_api_cache(self):
        """Testa obtenção de cache global."""
        cache = get_gov_api_cache()
        assert cache is not None
        assert isinstance(cache, GovAPICache)

    def test_gov_api_cache_singleton(self):
        """Testa que cache global é singleton."""
        cache1 = get_gov_api_cache()
        cache2 = get_gov_api_cache()
        assert cache1 is cache2
