"""
Validador de Configuração
==========================
Valida configurações do projeto e chaves de API.
"""

import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("ia_analisadora.config_validator")


@dataclass
class ValidationResult:
    """Resultado da validação."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigValidator:
    """Validador de configurações do projeto."""
    
    REQUIRED_ENV_VARS = {
        'DATA_DIR': 'Diretório de dados',
        'REPORTS_DIR': 'Diretório de relatórios',
        'KNOWLEDGE_DB': 'Caminho da base de conhecimento',
    }
    
    OPTIONAL_ENV_VARS = {
        'TESSERACT_CMD': 'Comando Tesseract OCR',
        'OCR_DPI': 'DPI para OCR',
        'OCR_LANG': 'Idioma OCR',
        'SPACY_MODEL': 'Modelo spaCy',
        'EMBEDDING_MODEL': 'Modelo de embeddings',
        'REQUEST_TIMEOUT': 'Timeout de requisições',
        'VERIFY_SSL': 'Verificação SSL',
        'LIMITE_SUPERFATURAMENTO_DESVIOS': 'Limite de desvios para superfaturamento',
        'LIMITE_EMPRESA_NOVA_DIAS': 'Limite de dias para empresa nova',
        'LIMITE_FRACIONAMENTO_DIAS': 'Limite de dias para fracionamento',
        'LIMITE_FRACIONAMENTO_VALOR': 'Limite de valor para fracionamento',
        'LIMITE_CAPITAL_SOCIAL_MINIMO': 'Limite mínimo de capital social',
        'LOG_LEVEL': 'Nível de log',
    }
    
    AI_PROVIDERS = {
        'nvidia': 'NVIDIA_API_KEY',
        'huggingface': 'HF_TOKEN',
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'google': 'GOOGLE_API_KEY',
        'cohere': 'COHERE_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY',
        'groq': 'GROQ_API_KEY',
        'together': 'TOGETHER_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_all(self) -> ValidationResult:
        """Executa todas as validações."""
        self.errors = []
        self.warnings = []
        
        self._validate_required_env_vars()
        self._validate_ai_config()
        self._validate_directories()
        self._validate_numeric_configs()
        
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
    
    def _validate_required_env_vars(self):
        """Valida variáveis de ambiente obrigatórias."""
        for var, description in self.REQUIRED_ENV_VARS.items():
            value = os.getenv(var)
            if not value:
                self.errors.append(f"Variável obrigatória não definida: {var} ({description})")
            else:
                logger.debug(f"✓ {var} = {value}")
    
    def _validate_ai_config(self):
        """Valida configuração de IA."""
        provider = os.getenv('AI_PROVIDER', 'local')
        
        if provider == 'local':
            self.warnings.append("Usando provedor local (spaCy) - funcionalidades de IA avançadas estarão limitadas")
            return
        
        if provider not in self.AI_PROVIDERS:
            self.errors.append(f"Provedor de IA inválido: {provider}. Opções: {', '.join(self.AI_PROVIDERS.keys())}")
            return
        
        api_key_var = self.AI_PROVIDERS[provider]
        api_key = os.getenv(api_key_var)
        
        if not api_key:
            self.errors.append(f"Chave de API não definida para provedor '{provider}': {api_key_var}")
        elif api_key.startswith(('sk-', 'nvapi-', 'hf-', 'gsk-')):
            logger.debug(f"✓ {api_key_var} configurada")
        else:
            self.warnings.append(f"Chave de API {api_key_var} pode estar em formato inválido")
    
    def _validate_directories(self):
        """Valida se diretórios existem ou podem ser criados."""
        directories = [
            os.getenv('DATA_DIR', 'data'),
            os.getenv('REPORTS_DIR', 'data/reports'),
            os.path.join('data', 'conhecimento'),
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.debug(f"✓ Diretório criado: {directory}")
                except Exception as e:
                    self.errors.append(f"Não foi possível criar diretório {directory}: {e}")
            else:
                logger.debug(f"✓ Diretório existe: {directory}")
    
    def _validate_numeric_configs(self):
        """Valida configurações numéricas."""
        numeric_configs = {
            'OCR_DPI': int,
            'REQUEST_TIMEOUT': int,
            'LIMITE_SUPERFATURAMENTO_DESVIOS': float,
            'LIMITE_EMPRESA_NOVA_DIAS': int,
            'LIMITE_FRACIONAMENTO_DIAS': int,
            'LIMITE_FRACIONAMENTO_VALOR': float,
            'LIMITE_CAPITAL_SOCIAL_MINIMO': float,
        }
        
        for var, expected_type in numeric_configs.items():
            value = os.getenv(var)
            if value:
                try:
                    expected_type(value)
                    logger.debug(f"✓ {var} = {value}")
                except (ValueError, TypeError):
                    self.errors.append(f"Valor inválido para {var}: {value} (esperado: {expected_type.__name__})")
    
    def validate_ai_provider(self, provider: str) -> ValidationResult:
        """Valida um provedor de IA específico."""
        self.errors = []
        self.warnings = []
        
        if provider not in self.AI_PROVIDERS and provider != 'local':
            self.errors.append(f"Provedor inválido: {provider}")
            return ValidationResult(is_valid=False, errors=self.errors, warnings=self.warnings)
        
        if provider != 'local':
            api_key_var = self.AI_PROVIDERS[provider]
            if not os.getenv(api_key_var):
                self.errors.append(f"Chave de API não definida: {api_key_var}")
        
        return ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings
        )
    
    def get_config_summary(self) -> Dict[str, str]:
        """Retorna resumo da configuração atual."""
        return {
            'ai_provider': os.getenv('AI_PROVIDER', 'local'),
            'ai_model': os.getenv('AI_MODEL', 'spacy-pt'),
            'data_dir': os.getenv('DATA_DIR', 'data'),
            'reports_dir': os.getenv('REPORTS_DIR', 'data/reports'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'spacy_model': os.getenv('SPACY_MODEL', 'pt_core_news_lg'),
        }


def validate_config() -> ValidationResult:
    """Função conveniente para validar configuração."""
    validator = ConfigValidator()
    return validator.validate_all()


def validate_ai_provider(provider: str) -> ValidationResult:
    """Função conveniente para validar provedor de IA."""
    validator = ConfigValidator()
    return validator.validate_ai_provider(provider)


if __name__ == "__main__":
    # Teste de validação
    result = validate_config()
    
    print("=== Validação de Configuração ===")
    print(f"Status: {'✓ VÁLIDA' if result.is_valid else '✗ INVÁLIDA'}")
    
    if result.errors:
        print("\nErros:")
        for error in result.errors:
            print(f"  ✗ {error}")
    
    if result.warnings:
        print("\nAvisos:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
    
    if result.is_valid:
        print("\n✓ Configuração validada com sucesso!")
