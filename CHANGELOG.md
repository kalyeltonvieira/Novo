# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Sistema multi-agente com SupervisorRouter e agentes especialistas
- Agentes: NavegadorAgente, AgenteGrafo, AgenteDiarioOficial, AgentePayroll, AgenteGeospatial, AgenteExtrator, AgenteRelator, AgenteSancoes, AgenteBancario, AgenteSuperfaturamento, AgenteLinhaDoTempo
- Integração com NVIDIA API (DeepSeek V4 Flash)
- Integração com HuggingFace Inference API
- Navegador automatizado com Selenium para extração de portais de transparência
- Interface gráfica minimalista estilo ChatGPT/Linear
- Testes unitários para módulos de agentes e navegador
- Documentação do sistema multi-agente
- Guia de contribuição (CONTRIBUTING.md)
- Validação de configuração
- Exportação de dados em CSV e Excel
- Sistema de cache para embeddings e resultados de IA
- Configurações de linting (flake8), formatação (black, isort) e type checking (mypy)
- Coverage reports com pytest-cov
- Dockerfile para containerização
- GitHub Actions workflow para CI/CD
- Pre-commit hooks para scanning de secrets

### Changed
- Atualização de .env.example com novos provedores (NVIDIA, HuggingFace)
- Melhoria na arquitetura de provedores de IA
- Refatoração do sistema de roteamento multi-agente

### Fixed
- Correção de TODO/FIXME comments em navegador_automatizado.py
- Tratamento de erros em comunicação com IA
- Validação de chaves de API ausentes

### Security
- Melhoria na segurança de chaves de API (apenas em .env)
- Pre-commit hooks para detectar secrets expostos

## [1.0.0] - 2024-01-XX

### Added
- Sistema completo de análise de documentos públicos
- Extração universal (PDF, imagem, HTML, planilhas, XML, JSON, texto)
- NLP com spaCy para extração de entidades
- OCR com Tesseract para documentos escaneados
- Detecção de 12 tipos de anomalias
- Graph database com NetworkX
- Correlação de entidades (CNPJ/CPF, co-ocorrência, similaridade)
- Validação de CNPJ e CPF
- Relatórios HTML interativos com Plotly
- Exportação JSON e PDF (WeasyPrint)
- Interface gráfica com CustomTkinter
- CLI para processamento em lote
- Integração com múltiplos provedores de IA (OpenAI, Anthropic, Google, Cohere, OpenRouter, Groq, Together AI, Mistral AI, Ollama)
- Testes unitários para core modules
- Documentação completa em README.md

## [0.1.0] - 2023-XX-XX

### Added
- MVP do sistema de análise de documentos
- Extração básica de entidades
- Detecção simples de anomalias
- Interface gráfica inicial
