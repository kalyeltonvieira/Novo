"""
Integração com Provedores de IA (LLM APIs)
===========================================
Simplificado para usar apenas OpenAI nativo com API da NVIDIA (deepseek-v4-flash).
"""

import os
from typing import Optional, Dict, Any, List
from enum import Enum
import logging
import time

logger = logging.getLogger("ia_analisadora.ai")


class AIProvider(Enum):
    """Provedores de IA suportados."""
    NVIDIA = "nvidia"  # NVIDIA API com DeepSeek
    HUGGINGFACE = "huggingface"  # HuggingFace Inference API
    LOCAL = "local"  # spaCy local (sem API)


class AIModel:
    """Representa um modelo de IA específico."""
    
    def __init__(self, provider: AIProvider, model_name: str, display_name: str):
        self.provider = provider
        self.model_name = model_name
        self.display_name = display_name
    
    def __str__(self):
        return f"{self.provider.value}:{self.model_name}"


# Catálogo de modelos disponíveis
MODELS_CATALOG = {
    AIProvider.NVIDIA: [
        AIModel(AIProvider.NVIDIA, "deepseek-ai/deepseek-v4-flash", "DeepSeek V4 Flash"),
        AIModel(AIProvider.NVIDIA, "deepseek-ai/deepseek-r1", "DeepSeek R1"),
    ],
    AIProvider.HUGGINGFACE: [
        # Modelos servidos via router OpenAI-compatible do Hugging Face.
        # O nome "DeepSeek-V4-Flash" não existe no HF; usamos o que existe.
        AIModel(AIProvider.HUGGINGFACE, "meta-llama/Llama-3.1-70B-Instruct", "Llama 3.1 70B"),
        AIModel(AIProvider.HUGGINGFACE, "deepseek-ai/DeepSeek-R1", "DeepSeek R1 (HF)"),
    ],
    AIProvider.LOCAL: [
        AIModel(AIProvider.LOCAL, "spacy-pt", "spaCy Português"),
    ],
}


def get_api_key(provider: AIProvider) -> Optional[str]:
    """Obtém a API key para um provider específico."""
    if provider == AIProvider.NVIDIA:
        return os.getenv("NVIDIA_API_KEY")
    elif provider == AIProvider.HUGGINGFACE:
        return os.getenv("HF_TOKEN")
    return None


class AIProviderClient:
    """Cliente simplificado para provedores de IA usando OpenAI nativo."""
    
    def __init__(self, provider: AIProvider, model: Optional[str] = None):
        self.provider = provider
        self.model = model or self._get_default_model()
        self.client = None
        self._initialize_client()
    
    def _get_default_model(self) -> str:
        """Retorna o modelo padrão para o provider."""
        if self.provider == AIProvider.NVIDIA:
            return "deepseek-ai/deepseek-v4-flash"
        elif self.provider == AIProvider.HUGGINGFACE:
            # DeepSeek-V4-Flash não está publicado no HF; usa Llama 3.1 como default.
            return "meta-llama/Llama-3.1-70B-Instruct"
        return "spacy-pt"
    
    def _initialize_client(self):
        """Inicializa o cliente do provider."""
        try:
            if self.provider == AIProvider.NVIDIA:
                from openai import OpenAI
                
                api_key = get_api_key(self.provider)
                if not api_key:
                    logger.warning("NVIDIA_API_KEY nao encontrada nas variaveis de ambiente")
                    print("[AVISO] NVIDIA_API_KEY nao encontrada no .env")
                else:
                    print(f"[OK] NVIDIA_API_KEY encontrada: {api_key[:10]}...")
                
                self.client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=api_key or "$NVIDIA_API_KEY"
                )
            elif self.provider == AIProvider.HUGGINGFACE:
                from openai import OpenAI
                
                api_key = get_api_key(self.provider)
                if not api_key:
                    logger.warning("HF_TOKEN nao encontrado nas variaveis de ambiente")
                    print("[AVISO] HF_TOKEN nao encontrado no .env")
                else:
                    print(f"[OK] HF_TOKEN encontrada: {api_key[:10]}...")
                
                self.client = OpenAI(
                    base_url="https://router.huggingface.co/v1",
                    api_key=api_key or "$HF_TOKEN"
                )
            else:
                self.client = None
                
        except ImportError as e:
            logger.error(f"Erro ao importar biblioteca do provider: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Verifica se o provider está disponível."""
        if self.provider == AIProvider.NVIDIA:
            return self.client is not None and get_api_key(self.provider) is not None
        elif self.provider == AIProvider.HUGGINGFACE:
            return self.client is not None and get_api_key(self.provider) is not None
        return False
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """Executa chat completion usando o provider.

        Retorna None em falha irrecuperável. Erros previsíveis (chave ausente,
        401, 429) são logados com detalhes suficientes para o usuário entender
        o que precisa corrigir (ex.: preencher a API key no .env).
        """
        api_key = get_api_key(self.provider)
        if not api_key:
            logger.error(
                f"Provider {self.provider.value} sem API key configurada. "
                f"Defina a variável de ambiente correspondente no .env."
            )
            return {
                "content": (
                    f"⚠️ Provedor '{self.provider.value}' sem API key configurada. "
                    f"Abra o arquivo .env e preencha a chave correspondente "
                    f"(NVIDIA_API_KEY ou HF_TOKEN)."
                ),
                "reasoning": None,
                "model": self.model,
                "provider": self.provider.value,
                "error": "missing_api_key",
            }

        if not self.is_available():
            logger.error(f"Provider {self.provider} não está disponível")
            return None

        max_retries = 3
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                if self.provider == AIProvider.NVIDIA:
                    completion = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=kwargs.get("temperature", 1),
                        top_p=kwargs.get("top_p", 0.95),
                        max_tokens=kwargs.get("max_tokens", 16384),
                        extra_body={"chat_template_kwargs":{"thinking":True,"reasoning_effort":"high"}},
                        stream=False
                    )

                    reasoning = getattr(completion.choices[0].message, "reasoning", None) or \
                               getattr(completion.choices[0].message, "reasoning_content", None)

                    content = completion.choices[0].message.content

                    return {
                        "content": content,
                        "reasoning": reasoning,
                        "model": self.model,
                        "provider": self.provider.value,
                    }
                elif self.provider == AIProvider.HUGGINGFACE:
                    completion = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=kwargs.get("max_tokens", 512),
                        stream=False
                    )

                    content = completion.choices[0].message.content

                    return {
                        "content": content,
                        "reasoning": None,
                        "model": self.model,
                        "provider": self.provider.value,
                    }

            except Exception as e:
                last_exception = e
                err_msg = str(e)
                # Se for erro 529 (Overloaded), 429 (Rate Limit) ou 503 (Unavailable), tenta novamente após um pequeno intervalo
                if any(code in err_msg for code in ["529", "429", "503", "overloaded", "temporarily"]):
                    if attempt < max_retries:
                        logger.warning(f"[RETRY {attempt}/{max_retries}] Servidor sobrecarregado (529/429). Aguardando 2s antes de tentar novamente...")
                        time.sleep(2)
                        continue

                err_type = type(e).__name__
                logger.error(f"Erro ao executar chat completion ({err_type}): {e}")
                return {
                    "content": (
                        f"⚠️ Falha na comunicação com a IA ({err_type}): {e}. "
                        f"Verifique sua conexão e a validade da API key no .env."
                    ),
                    "reasoning": None,
                    "model": self.model,
                    "provider": self.provider.value,
                    "error": err_type,
                }

        err_type = type(last_exception).__name__ if last_exception else "UnknownError"
        return {
            "content": f"⚠️ Falha na comunicação com a IA após {max_retries} tentativas ({err_type}): {last_exception}",
            "reasoning": None,
            "model": self.model,
            "provider": self.provider.value,
            "error": err_type,
        }

        return None


class AIManager:
    """Gerenciador simplificado de IA."""
    
    def __init__(self, default_provider: AIProvider = AIProvider.NVIDIA):
        self.default_provider = default_provider
        self.current_client = None
        self._initialize()
    
    def _initialize(self):
        """Inicializa o gerenciador."""
        self.current_client = AIProviderClient(self.default_provider)
    
    def get_client(self) -> Optional[AIProviderClient]:
        """Retorna o cliente atual."""
        return self.current_client
    
    def set_provider(self, provider: AIProvider, model: Optional[str] = None):
        """Define um provider específico."""
        self.current_client = AIProviderClient(provider, model)
    
    def analyze_text(self, text: str, task: str = "analysis", **kwargs) -> Optional[str]:
        """Analisa texto usando o provider atual."""
        if not self.current_client:
            logger.error("Nenhum provider inicializado")
            return None

        # Verifica especificamente se a API key existe antes de tentar chamar.
        # Sem isso, a GUI recebe apenas "Erro: Falha na comunicação com a IA."
        # que não ajuda o usuário a entender o problema real.
        api_key = get_api_key(self.current_client.provider)
        if not api_key:
            logger.error(
                f"API key ausente para {self.current_client.provider.value}. "
                f"Preencha no .env."
            )
            return (
                f"⚠️ Sem API key para '{self.current_client.provider.value}'. "
                f"Abra o arquivo .env e preencha a chave correspondente."
            )

        messages = [
            {"role": "system", "content": f"Você é um auditor especializado em {task}."},
            {"role": "user", "content": text}
        ]

        result = self.current_client.chat_completion(messages, **kwargs)

        if result:
            response = result.get("content", "")
            if result.get("reasoning"):
                response = f"## Reasoning\n{result['reasoning']}\n\n## Resposta\n{response}"
            return response

        return None


# Singleton global
_ai_manager = None

def get_ai_manager() -> AIManager:
    """Retorna a instância global do AIManager."""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIManager()
    return _ai_manager


def reset_ai_manager():
    """Reseta a instância global do AIManager."""
    global _ai_manager
    _ai_manager = None
