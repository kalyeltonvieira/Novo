"""
Gerenciador de Cache
====================
Sistema de cache para embeddings, resultados de IA e APIs governamentais.
Suporta cache local e distribuído (Redis).
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Optional, Dict, Union
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger("ia_analisadora.cache")

# Tentativa de importar Redis para cache distribuído
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis não disponível. Usando apenas cache local.")


class CacheManager:
    """
    Gerenciador de cache para resultados de IA, embeddings e APIs.
    
    Suporta cache local em disco e cache distribuído com Redis.
    
    Attributes:
        cache_dir (Path): Diretório para cache local
        ttl (timedelta): Tempo de vida padrão do cache
        use_redis (bool): Se True, usa Redis para cache distribuído
        redis_client: Cliente Redis (se disponível)
    """
    
    def __init__(
        self, 
        cache_dir: str = "data/cache", 
        ttl_hours: int = 24,
        use_redis: bool = False,
        redis_url: Optional[str] = None
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.redis_client = None
        
        if self.use_redis:
            redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info(f"Conectado ao Redis em {redis_url}")
            except Exception as e:
                logger.warning(f"Falha ao conectar ao Redis: {e}. Usando cache local.")
                self.use_redis = False
        
        self._cache_index: Dict[str, Dict[str, Any]] = {}
        self._load_index()
    
    def _get_cache_key(self, data: Any) -> str:
        """Gera chave de cache baseada no conteúdo."""
        if isinstance(data, str):
            content = data
        elif isinstance(data, dict):
            content = json.dumps(data, sort_keys=True)
        elif isinstance(data, list):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Retorna caminho do arquivo de cache."""
        return self.cache_dir / f"{cache_key}.cache"
    
    def _load_index(self):
        """Carrega índice de cache do disco."""
        index_path = self.cache_dir / "cache_index.json"
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    self._cache_index = json.load(f)
            except Exception as e:
                logger.warning(f"Erro ao carregar índice de cache: {e}")
                self._cache_index = {}
    
    def _save_index(self):
        """Salva índice de cache no disco."""
        index_path = self.cache_dir / "cache_index.json"
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar índice de cache: {e}")
    
    def _is_expired(self, cache_key: str) -> bool:
        """Verifica se entrada de cache expirou."""
        if cache_key not in self._cache_index:
            return True
        
        cached_time = datetime.fromisoformat(self._cache_index[cache_key]['timestamp'])
        return datetime.now() - cached_time > self.ttl
    
    def get(self, data: Any, use_distributed: bool = True) -> Optional[Any]:
        """
        Recupera item do cache.
        
        Args:
            data: Dados para gerar chave de cache
            use_distributed: Se True, tenta Redis primeiro
        
        Returns:
            Dados em cache ou None se não encontrado/expirado
        """
        cache_key = self._get_cache_key(data)
        
        # Tenta Redis primeiro se disponível
        if self.use_redis and use_distributed:
            try:
                cached_data = self.redis_client.get(f"cache:{cache_key}")
                if cached_data:
                    logger.debug(f"Redis cache hit para chave {cache_key[:8]}...")
                    return pickle.loads(cached_data)
            except Exception as e:
                logger.warning(f"Erro ao ler do Redis: {e}")
        
        # Fallback para cache local
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        if self._is_expired(cache_key):
            self.delete(cache_key)
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
            logger.debug(f"Local cache hit para chave {cache_key[:8]}...")
            return cached_data
        except Exception as e:
            logger.warning(f"Erro ao ler cache local: {e}")
            return None
    
    def set(self, data: Any, value: Any, use_distributed: bool = True):
        """
        Armazena item no cache.
        
        Args:
            data: Dados para gerar chave de cache
            value: Valor a ser armazenado
            use_distributed: Se True, armazena também no Redis
        """
        cache_key = self._get_cache_key(data)
        cache_path = self._get_cache_path(cache_key)
        
        # Armazena no Redis se disponível
        if self.use_redis and use_distributed:
            try:
                serialized = pickle.dumps(value)
                self.redis_client.setex(
                    f"cache:{cache_key}",
                    int(self.ttl.total_seconds()),
                    serialized
                )
                logger.debug(f"Redis cache set para chave {cache_key[:8]}...")
            except Exception as e:
                logger.warning(f"Erro ao salvar no Redis: {e}")
        
        # Armazena localmente
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            
            self._cache_index[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'size': cache_path.stat().st_size,
                'type': type(value).__name__
            }
            self._save_index()
            
            logger.debug(f"Local cache set para chave {cache_key[:8]}...")
        except Exception as e:
            logger.error(f"Erro ao salvar cache local: {e}")
    
    def delete(self, data: Any):
        """Remove item específico do cache."""
        cache_key = data if isinstance(data, str) and len(data) == 64 else self._get_cache_key(data)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            cache_path.unlink()
        
        if cache_key in self._cache_index:
            del self._cache_index[cache_key]
            self._save_index()
    
    def clear(self):
        """Limpa todo o cache."""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        
        self._cache_index.clear()
        self._save_index()
        logger.info("Cache limpo")
    
    def clear_expired(self):
        """Remove apenas entradas expiradas."""
        expired_keys = [
            key for key in self._cache_index.keys()
            if self._is_expired(key)
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        if expired_keys:
            logger.info(f"Removidas {len(expired_keys)} entradas expiradas do cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        total_size = sum(
            entry['size'] for entry in self._cache_index.values()
        )
        
        type_counts = {}
        for entry in self._cache_index.values():
            type_name = entry['type']
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            'total_entries': len(self._cache_index),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'type_distribution': type_counts,
            'cache_dir': str(self.cache_dir),
            'ttl_hours': self.ttl.total_seconds() / 3600
        }


class EmbeddingCache:
    """Cache específico para embeddings."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager or CacheManager("data/cache/embeddings")
    
    def get_embedding(self, text: str) -> Optional[list]:
        """Recupera embedding do cache."""
        return self.cache.get(text)
    
    def set_embedding(self, text: str, embedding: list):
        """Armazena embedding no cache."""
        self.cache.set(text, embedding)
    
    def get_embeddings_batch(self, texts: list) -> Dict[str, Optional[list]]:
        """Recupera múltiplos embeddings do cache."""
        results = {}
        for text in texts:
            results[text] = self.get_embedding(text)
        return results
    
    def set_embeddings_batch(self, embeddings: Dict[str, list]):
        """Armazena múltiplos embeddings no cache."""
        for text, embedding in embeddings.items():
            self.set_embedding(text, embedding)


class AIResponseCache:
    """Cache específico para respostas de IA."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager or CacheManager("data/cache/ai_responses")
    
    def get_response(
        self,
        prompt: str,
        provider: str,
        model: str,
        temperature: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """Recupera resposta de IA do cache."""
        cache_key = {
            'prompt': prompt,
            'provider': provider,
            'model': model,
            'temperature': temperature
        }
        return self.cache.get(cache_key)
    
    def set_response(
        self,
        prompt: str,
        provider: str,
        model: str,
        response: Dict[str, Any],
        temperature: float = 0.7
    ):
        """Armazena resposta de IA no cache."""
        cache_key = {
            'prompt': prompt,
            'provider': provider,
            'model': model,
            'temperature': temperature
        }
        self.cache.set(cache_key, response)


# Instâncias globais
_embedding_cache: Optional[EmbeddingCache] = None
_ai_cache: Optional[AIResponseCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Retorna instância global do cache de embeddings."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def get_ai_cache() -> AIResponseCache:
    """Retorna instância global do cache de IA."""
    global _ai_cache
    if _ai_cache is None:
        _ai_cache = AIResponseCache()
    return _ai_cache


def reset_caches():
    """Reseta instâncias globais de cache."""
    global _embedding_cache, _ai_cache, _gov_api_cache
    _embedding_cache = None
    _ai_cache = None
    _gov_api_cache = None


class GovAPICache:
    """
    Cache específico para APIs governamentais.
    
    Configura TTLs diferentes por tipo de API:
    - Dados estáticos (ex: cadastros): 24h
    - Dados dinâmicos (ex: licitações): 1h
    - Dados em tempo real (ex: preços): 5min
    
    Attributes:
        cache: Instância do CacheManager
        api_ttls: Configuração de TTL por tipo de API
    """
    
    # Configuração de TTL por tipo de API
    API_TTLS = {
        'cadastral': timedelta(hours=24),      # CNPJ, dados cadastrais
        'licitacao': timedelta(hours=1),       # Licitações, contratos
        'financeiro': timedelta(minutes=30),   # Preços, câmbio
        'realtime': timedelta(minutes=5),      # Dados em tempo real
        'diario': timedelta(hours=6),          # Diários oficiais
        'default': timedelta(hours=2),
    }
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager or CacheManager(
            cache_dir="data/cache/gov_apis",
            ttl_hours=2,
            use_redis=os.getenv("USE_REDIS", "false").lower() == "true"
        )
        self.stats = {
            'hits': 0,
            'misses': 0,
            'by_api_type': {}
        }
    
    def get_api_response(
        self,
        api_name: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        api_type: str = 'default'
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera resposta de API governamental do cache.
        
        Args:
            api_name: Nome da API (ex: 'cgu', 'receita', 'pncp')
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            api_type: Tipo de API para definir TTL
        
        Returns:
            Resposta em cache ou None
        """
        cache_key = self._generate_api_key(api_name, endpoint, params)
        
        # Verifica se cache expirou baseado no tipo de API
        if self._is_api_cache_expired(cache_key, api_type):
            self.cache.delete(cache_key)
            self.stats['misses'] += 1
            return None
        
        cached_data = self.cache.get(cache_key)
        if cached_data:
            self.stats['hits'] += 1
            self._increment_api_stat(api_name, 'hits')
            logger.debug(f"GovAPI cache hit: {api_name}/{endpoint}")
            return cached_data
        
        self.stats['misses'] += 1
        self._increment_api_stat(api_name, 'misses')
        return None
    
    def set_api_response(
        self,
        api_name: str,
        endpoint: str,
        response: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        api_type: str = 'default'
    ) -> None:
        """
        Armazena resposta de API governamental no cache.
        
        Args:
            api_name: Nome da API
            endpoint: Endpoint da API
            response: Resposta da API
            params: Parâmetros da requisição
            api_type: Tipo de API para definir TTL
        """
        cache_key = self._generate_api_key(api_name, endpoint, params)
        
        # Adiciona metadados de cache
        cache_data = {
            'response': response,
            'cached_at': datetime.now().isoformat(),
            'api_name': api_name,
            'endpoint': endpoint,
            'api_type': api_type,
            'ttl_seconds': self.API_TTLS.get(api_type, self.API_TTLS['default']).total_seconds()
        }
        
        self.cache.set(cache_key, cache_data)
        logger.debug(f"GovAPI cache set: {api_name}/{endpoint} (TTL: {cache_data['ttl_seconds']}s)")
    
    def _generate_api_key(
        self,
        api_name: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Gera chave de cache para API.
        
        Args:
            api_name: Nome da API
            endpoint: Endpoint da API
            params: Parâmetros da requisição
        
        Returns:
            Chave de cache hash
        """
        key_data = {
            'api': api_name,
            'endpoint': endpoint,
            'params': params or {}
        }
        return self.cache._get_cache_key(key_data)
    
    def _is_api_cache_expired(self, cache_key: str, api_type: str) -> bool:
        actual_key = self.cache._get_cache_key(cache_key)
        if actual_key not in self.cache._cache_index:
            return True
        
        ttl = self.API_TTLS.get(api_type, self.API_TTLS['default'])
        cached_time = datetime.fromisoformat(self.cache._cache_index[actual_key]['timestamp'])
        return datetime.now() - cached_time > ttl
    
    def _increment_api_stat(self, api_name: str, stat_type: str) -> None:
        """Incrementa estatísticas por API."""
        if api_name not in self.stats['by_api_type']:
            self.stats['by_api_type'][api_name] = {'hits': 0, 'misses': 0}
        self.stats['by_api_type'][api_name][stat_type] += 1
    
    def invalidate_api(self, api_name: str) -> None:
        """
        Invalida todo o cache de uma API específica.
        
        Args:
            api_name: Nome da API a invalidar
        """
        keys_to_delete = []
        for cache_key in list(self.cache._cache_index.keys()):
            cache_path = self.cache._get_cache_path(cache_key)
            if cache_path.exists():
                try:
                    with open(cache_path, 'rb') as f:
                        cached_data = pickle.load(f)
                    if isinstance(cached_data, dict) and cached_data.get('api_name') == api_name:
                        keys_to_delete.append(cache_key)
                except Exception:
                    pass
        
        for key in keys_to_delete:
            self.cache.delete(key)
        
        logger.info(f"Invalidados {len(keys_to_delete)} caches da API {api_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache de APIs.
        
        Returns:
            Dicionário com estatísticas
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'total_hits': self.stats['hits'],
            'total_misses': self.stats['misses'],
            'hit_rate_percent': round(hit_rate, 2),
            'by_api': self.stats['by_api_type'],
            'cache_stats': self.cache.get_stats()
        }
    
    def clear(self) -> None:
        """Limpa todo o cache de APIs."""
        self.cache.clear()
        self.stats = {'hits': 0, 'misses': 0, 'by_api_type': {}}
        logger.info("Cache de APIs governamentais limpo")


# Instância global do cache de APIs governamentais
_gov_api_cache: Optional[GovAPICache] = None


def get_gov_api_cache() -> GovAPICache:
    """Retorna instância global do cache de APIs governamentais."""
    global _gov_api_cache
    if _gov_api_cache is None:
        _gov_api_cache = GovAPICache()
    return _gov_api_cache
