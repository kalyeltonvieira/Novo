# 🧠 IA Analisadora - "O Cérebro da Transparência"

Sistema completo para análise de documentos públicos com detecção de irregularidades, usando OCR, NLP, embeddings e graph database.

## 📋 Funcionalidades

- **Extração Universal**: Processa PDFs, imagens (OCR), HTML, planilhas (XLSX/CSV), XML, JSON e texto
- **NLP & Entidades**: Extrai pessoas, empresas, CNPJ, CPF, valores, datas, cargos, licitações, contratos, endereços e órgãos públicos
- **IA/LLM Integration**: Suporte a múltiplos provedores de IA (OpenAI GPT-4, Anthropic Claude, Google Gemini, Cohere) para análise avançada
- **Validação**: Valida dígitos verificadores de CNPJ e CPF
- **Correlação**: Liga entidades por CNPJ/CPF, co-ocorrência, similaridade nominal e relações societárias
- **Detecção de Anomalias**: 12 detectores incluindo superfaturamento, nepotismo, cartel, fracionamento, empresas fantasmas, conflito de interesses, pagamento sem licitação e prazo curto
- **Graph Database**: Base de conhecimento em NetworkX com consultas de vizinhança e caminhos
- **Relatórios**: HTML interativo com gráficos Plotly, exportação JSON e PDF (WeasyPrint)
- **GUI**: Interface gráfica moderna com CustomTkinter (dashboard, coleta, grafo, alertas, relatórios)
- **CLI**: Modo linha de comando para processamento em lote

## 🚀 Instalação

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Baixar modelo spaCy português
python -m spacy download pt_core_news_lg

# Ou usar o instalador integrado
python main.py --install
```

### Configuração de IA (Opcional)

Para usar modelos de IA avançados (OpenAI, Anthropic, Google, Cohere), configure as API keys no arquivo `.env`:

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o .env e adicione suas API keys
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
GOOGLE_API_KEY=your-google-api-key-here
COHERE_API_KEY=your-cohere-api-key-here

# Escolha o provedor padrão
AI_PROVIDER=openai
AI_MODEL=gpt-4-turbo-preview
```

**Provedores suportados:**
- **OpenAI**: GPT-4 Turbo, GPT-4, GPT-3.5 Turbo
- **Anthropic**: Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku
- **Google**: Gemini Pro, Gemini Pro Vision
- **Cohere**: Command, Command Light
- **OpenRouter**: Multi-provider (acesso a 100+ modelos incluindo Claude, GPT-4, Llama 3)
- **Groq**: Ultra-fast inference (Llama 3 70B, Mixtral 8x7B, Gemma)
- **Together AI**: Mistral, Llama 3, e outros modelos open-source
- **Mistral AI**: Mistral Large, Mistral Medium, Mistral 7B
- **Ollama**: Local self-hosted (Llama 3, Mistral, Code Llama)
- **Local**: spaCy (sem API, processamento local)

### Pré-requisitos do sistema

- **Tesseract OCR**: Necessário para OCR de imagens/PDFs escaneados
  - Windows: Baixe de https://github.com/UB-Mannheim/tesseract/wiki
  - Linux: `sudo apt install tesseract-ocr tesseract-ocr-por`
  - macOS: `brew install tesseract tesseract-lang`

- **Poppler**: Necessário para conversão de PDF para imagem
  - Windows: Baixe de https://github.com/oschwartz10612/poppler-windows
  - Linux: `sudo apt install poppler-utils`
  - macOS: `brew install poppler`

## 💻 Uso

### Interface Gráfica (padrão)
```bash
python main.py
```

### Linha de Comando
```bash
# Processar arquivo único
python main.py --cli documento.pdf

# Processar URL
python main.py --url https://exemplo.com/documento.html

# Processar pasta inteira
python main.py --pasta ./documentos

# Gerar relatório após processamento
python main.py --cli documento.pdf --report
```

### Usando IA para Análise Avançada

**Via GUI:**
1. Inicie a GUI: `python main.py`
2. Na barra superior, selecione o provedor de IA (OpenAI, Anthropic, Google, Cohere)
3. Marque a checkbox "Usar IA"
4. Processe os documentos normalmente

**Via Código:**
```python
from core.leitor_universal import LeitorUniversal
from core.detector_anomalias import DetectorAnomalias
from utils.ai_providers import AIProvider, get_ai_manager

# Configura provedor de IA
ai_manager = get_ai_manager()
ai_manager.set_provider(AIProvider.OPENAI)

# Usa IA na extração de entidades
leitor = LeitorUniversal(config={"use_ai": True})
documento = leitor.processar_documento("documento.pdf")

# Usa IA na detecção de anomalias
detector = DetectorAnomalias(config={"use_ai": True})
alertas = detector.processar([documento], [], {}, {})
```

**Exemplo de script:**
```bash
python examples/exemplo_ia_api.py documento.pdf openai
python examples/exemplo_ia_api.py documento.txt anthropic
```

## 🏗️ Arquitetura

```
Entrada de Dados → Leitor Universal → Correlacionador →
    Detector de Anomalias → Base de Conhecimento → Reports
```

### Estrutura do Projeto

```
.
├── main.py                 # Ponto de entrada (CLI/GUI)
├── requirements.txt        # Dependências
├── core/                   # Lógica principal
│   ├── entidades.py        # Modelos de dados (dataclasses)
│   ├── leitor_universal.py # Extração de documentos (OCR/NLP/regex)
│   ├── entrada_dados.py    # Coleta de fontes (arquivos/URL/APIs)
│   ├── correlacionador.py  # Correlação de entidades
│   ├── detector_anomalias.py # Detecção de irregularidades
│   ├── base_conhecimento.py  # Graph database (NetworkX)
│   └── camada_reports.py   # Geração de relatórios
├── gui/                    # Interface gráfica
│   └── app.py              # App CustomTkinter
├── utils/                  # Utilitários
│   ├── validadores.py      # Validação CNPJ/CPF
│   ├── monitoring.py       # Logging estruturado e métricas
│   ├── cache_manager.py    # Cache distribuído (Redis/local)
│   └── ai_providers.py     # Integração com provedores de IA
├── tests/                  # Testes unitários
│   ├── test_monitoring.py  # Testes de monitoring
│   └── test_cache_manager.py # Testes de cache
├── examples/               # Exemplos de uso
├── .github/workflows/      # CI/CD (GitHub Actions)
│   └── ci.yml              # Pipeline automatizado
└── data/                   # Dados gerados (relatórios, grafo, cache, logs)
```

## 🧪 Testes

```bash
# Executar todos os testes
python -m pytest tests/ -v

# Executar com coverage
python -m pytest tests/ --cov=core --cov=utils --cov-report=html

# Testes específicos
python -m pytest tests/test_leitor.py -v
python -m pytest tests/test_detector.py -v
python -m pytest tests/test_monitoring.py -v
python -m pytest tests/test_cache_manager.py -v
```

## � Monitoring e Logging Centralizado

O sistema possui logging estruturado e coleta de métricas:

### Logging Estruturado
- Logs em formato JSON para análise posterior (ELK, Splunk)
- Contexto adicional (user_id, request_id, etc.)
- Múltiplos handlers (console, arquivo)

### Métricas
- Contadores (increment)
- Gauges (valores atuais)
- Histogramas (distribuição de timings)
- Timers (medição de tempo)

### Configuração
```bash
# No .env
LOG_DIR=data/logs
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Uso
```python
from utils.monitoring import get_logger, get_metrics

logger = get_logger("meu_modulo")
logger.set_context(user_id="123")
logger.info("Processando documento", doc_id="abc")

metrics = get_metrics()
metrics.increment("documentos_processados")
metrics.record_timing("tempo_processamento", 1.5)
```

## � Tipos de Anomalias Detectadas

| Tipo | Descrição |
|------|-----------|
| Superfaturamento | Valores pagos muito acima da média |
| Nepotismo | Parentes de agentes públicos contratados |
| Cartel | Empresas com padrão suspeito em licitações |
| Fracionamento | Compras fracionadas para evitar licitação |
| Empresa Fantasma | Empresas com características suspeitas |
| Conflito de Interesses | Agente público sócio de empresa contratada |
| Pagamento sem Licitação | Valores altos sem processo licitatório |
| Prazo Curto | Contratos com prazos suspeitosamente curtos |
| Empresa Recém-Criada | Empresas novas com contratos públicos |
| Sócio Repetido | Mesma pessoa como sócia de múltiplas empresas |
| Valor Acima da Média | Valores individuais acima da média |
| Suspeita de Fraude | Múltiplos indicadores combinados |

## 🏛️ APIs Governamentais Integradas (60+)

O sistema integra com **todas as APIs governamentais brasileiras** públicas:

### Transparência e Contratações (15 APIs)
- **PNCP** - Portal Nacional de Contratações Públicas (todas licitações do Brasil)
- **CGU** - Despesas, Transferências, Servidores, CEIS, CNEP, CEAFIM, Benefícios
- **Comprasnet/SIASG** - Compras governamentais federais
- **TCU** - Acórdãos, Contas Irregulares, Processos

### Dados Cadastrais (6 APIs)
- **Receita Federal** - CNPJ completo (sócios, capital, situação)
- **Correios** - Consulta CEP
- **IBGE** - Municípios, Estados, População

### Cache Distribuído para APIs Governamentais

O sistema inclui cache inteligente para APIs governamentais com TTLs diferenciados:
- **Dados cadastrais** (CNPJ): 24h de cache
- **Licitações/Contratos**: 1h de cache
- **Dados financeiros**: 30min de cache
- **Dados em tempo real**: 5min de cache

Para habilitar cache distribuído com Redis:
```bash
# No .env
USE_REDIS=true
REDIS_URL=redis://localhost:6379/0
```

O cache reduz significativamente chamadas às APIs e melhora performance.

### Legislativo (9 APIs)
- **Câmara dos Deputados** - Deputados, Proposições, Votações, Despesas, Frentes, Eventos
- **Senado Federal** - Senadores, Matérias, Votações

### Eleições (3 APIs)
- **TSE** - Candidatos, Doações de campanha, Prestação de contas

### Financeiro (8 APIs)
- **BACEN** - Câmbio, SELIC, Dívida pública, Inadimplência
- **SICONFI** - Receitas/Despesas municipais, Relatório de Gestão Fiscal
- **BNDES** - Financiamentos

### COAF / Lavagem de Dinheiro (10 APIs) ⭐
- **COAF/UIF** - Lista de sanções, Comunicações de operações suspeitas, PLOA
- **BACEN COAF** - Comunicações via BACEN
- **COIF** - Operações de câmbio
- **SCR** - Operações de crédito
- **SISBAF** - Inadimplência bancária

### Reguladoras (7 APIs)
- **ANATEL, ANP, ANEEL, ANTT, ANS, ANA** - Concessões e preços

### Judicial (3 APIs)
- **CNJ DataJud, STF, JusBrasil** - Processos judiciais

### Social/Saúde/Educação (8 APIs)
- **DATASUS, INEP, IBAMA, INMET, EMBRAPA** - Dados sociais e ambientais

### Diários Oficiais (2 APIs)
- **DOU/DOE** - Diários Oficiais via Querido Diário

### Painel de Preços (2 APIs)
- **Painel de Preços do Governo Federal**

## 🚀 CI/CD Automatizado

O projeto possui pipeline CI/CD completo com GitHub Actions:

### Features
- **Execução semanal agendada** (cron)
- **Matrix de versões Python** (3.10, 3.11, 3.12)
- **Linting**: flake8, black, isort
- **Type checking**: mypy
- **Security scanning**: bandit, safety, pip-audit
- **Docker build e scan**: Trivy
- **Test coverage**: Upload para Codecov

### Workflow
```yaml
# .github/workflows/ci.yml
on:
  push:
    branches: [main, develop]
  pull_request:
  schedule:
    - cron: '0 0 * * 0'  # Semanal
```

## 🔧 Configuração Avançada

### Variáveis de Ambiente

```bash
# Diretórios
DATA_DIR=data
REPORTS_DIR=data/reports
LOG_DIR=data/logs
KNOWLEDGE_DB=data/conhecimento

# Cache Distribuído
USE_REDIS=false
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO

# OCR
TESSERACT_CMD=tesseract
OCR_DPI=300
OCR_LANG=por

# NLP
SPACY_MODEL=pt_core_news_lg
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Detecção de Anomalias
LIMITE_SUPERFATURAMENTO_DESVIOS=3.0
LIMITE_EMPRESA_NOVA_DIAS=180
LIMITE_FRACIONAMENTO_DIAS=30
```

## 🕷️ Sistema Multi-Agente (14 Agentes)

### Agentes Básicos (10)
| Agente | Função |
|--------|--------|
| Navegador | Navega em URLs e extrai conteúdo |
| GrafoSocietario | Gera visualização de relacionamentos |
| GazetteAuditor | Processa Diários Oficiais |
| PayrollAuditor | Analisa folhas de pagamento |
| GeospatialAuditor | Mapeia endereços (folium) |
| InvoiceParser | Extrai dados de notas fiscais |
| ReporterAuditor | Gera laudos PDF |
| SanctionAuditor | Verifica sanções CEIS/CNEP |
| BankingAuditor | Analisa extratos bancários (smurfing) |
| TimelineAuditor | Cria linha do tempo de eventos |

### Agentes Avançados (4) ⭐
| Agente | Função |
|--------|--------|
| **CrawlerProfundo** | Crawl com paginação automática (até 50 páginas por seção) |
| **PDFDownloader** | Baixa e processa PDFs de portais com OCR |
| **CNPJValidator** | Consulta Receita Federal + CEIS + CNEP + CEAFIM + COAF + IBAMA |
| **CrossPortal** | Cruza dados entre PNCP + CGU + TCU + COAF |

## 🤖 Integração com IA/LLM

O sistema suporta múltiplos provedores de IA para análise avançada:

### Provedores Suportados

| Provedor | Modelos | Uso |
|----------|---------|-----|
| OpenAI | GPT-4 Turbo, GPT-4, GPT-3.5 Turbo | Extração de entidades, detecção de anomalias |
| Anthropic | Claude 3 Opus, Sonnet, Haiku | Análise contextual, sumarização |
| Google | Gemini Pro, Gemini Pro Vision | Processamento multimodal |
| Cohere | Command, Command Light | Geração de texto |
| OpenRouter | 100+ modelos (Claude, GPT-4, Llama 3) | Multi-provider, acesso a todos |
| Groq | Llama 3 70B, Mixtral 8x7B, Gemma | Ultra-fast inference |
| Together AI | Mistral, Llama 3, open-source | Modelos open-source otimizados |
| Mistral AI | Mistral Large, Medium, 7B | Modelos Mistral oficiais |
| Ollama | Llama 3, Mistral, Code Llama | Local self-hosted, offline |
| Local | spaCy (pt_core_news_lg) | Processamento local sem API |

### Funcionalidades com IA

- **Extração Avançada de Entidades**: LLMs podem identificar entidades complexas e contextuais que regex e spaCy podem perder
- **Detecção de Anomalias Contextual**: Análise de padrões sutis e combinações de indicadores
- **Sumarização Inteligente**: Resumos automáticos de documentos longos
- **Classificação de Documentos**: Categorização automática por tipo

### Comparação: Local vs IA

| Recurso | Local (spaCy) | IA (LLM) |
|---------|---------------|----------|
| Custo | Gratuito | Custo por API |
| Velocidade | Rápido | Mais lento |
| Privacidade | 100% local | Dados enviados para API |
| Precisão | Boa para entidades padrão | Melhor para contexto complexo |
| Offline | Sim | Não |

## 🔐 Configuração segura de chaves

**Regra de ouro:** chaves de API NUNCA vão para `config.json` ou para
qualquer arquivo versionado. Elas vivem **apenas** em `.env` (já está no
`.gitignore`).

- **Onde ficam as chaves:** `.env` → variáveis `NVIDIA_API_KEY`, `HF_TOKEN`,
  `OPENAI_API_KEY`, etc. Use `.env.example` como gabarito.
- **Onde ficam as preferências** (idioma, tema, provedor, modelo):
  `config.json` (gitignored). Use `config.example.json` como gabarito.
- **Pela GUI:** ao colar a NVIDIA API Key em Configurações → Geral, ela
  é gravada **no `.env`**, não no `config.json`.
- **Revogação:** se você já tinha chaves expostas em `config.json`,
  **revogue-as no site do provedor** (NVIDIA, HuggingFace, etc.) e gere
  novas. Apenas apagar do arquivo não invalida a chave antiga.

```bash
# Setup seguro do zero
cp .env.example .env
cp config.example.json config.json
# edite .env e cole suas chaves reais
```

## 📄 Licença

Projeto de código aberto para análise de transparência pública.