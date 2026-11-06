# Documentação do Projeto IA Analisadora

## Visão Geral

Sistema completo para análise de documentos públicos com detecção de irregularidades, usando OCR, NLP, embeddings, graph database e multi-agentes com IA.

## Arquitetura

```
                    ┌─────────────┐
                    │   Frontend  │
                    │  Next.js    │
                    │  :3000      │
                    └──────┬──────┘
                           │ HTTP REST
                    ┌──────▼──────┐
                    │   API       │
                    │  FastAPI    │
                    │  :8000      │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐ ┌─────▼─────┐ ┌────▼────────┐
     │    Core    │ │   GUI     │ │   Utils     │
     │  Pipeline  │ │CustomTkinter│ │ AI, Cache  │
     └────────────┘ └───────────┘ └─────────────┘
```

### Pipeline Core

```
Entrada de Dados → Leitor Universal → Correlacionador →
    Detector de Anomalias → Base de Conhecimento → Reports
```

## Estrutura do Projeto

```
.
├── main.py                 # Ponto de entrada (CLI/GUI)
├── api/                    # API REST FastAPI
│   ├── main.py            # Configuração e rotas
│   └── routes/            # Endpoints
│       ├── dashboard.py   # Dashboard e métricas
│       ├── documentos.py  # CRUD de documentos
│       ├── chat.py        # Chat multi-agente
│       ├── navegador.py   # Navegador Selenium
│       └── relatorios.py  # Geração de relatórios
├── core/                   # Lógica principal
│   ├── entidades.py        # Modelos de dados
│   ├── leitor_universal.py # Extração de documentos
│   ├── entrada_dados.py    # Coleta de fontes
│   ├── correlacionador.py  # Correlação de entidades
│   ├── detector_anomalias.py # Detecção de irregularidades
│   ├── base_conhecimento.py  # Graph database
│   ├── camada_reports.py   # Geração de relatórios
│   ├── navegador_automatizado.py # Selenium
│   └── agentes/            # Sistema multi-agente
│       ├── base.py         # Classe base
│       ├── supervisor.py   # Roteador de agentes
│       └── especialistas.py # Agentes especialistas
├── gui/                    # Interface gráfica
│   ├── app.py              # App completo
│   ├── app_minimalista.py  # App minimalista
│   └── configuracoes.py    # Tela de configurações
├── frontend/               # Frontend Next.js
│   └── src/app/            # Páginas e componentes
├── utils/                  # Utilitários
│   ├── ai_providers.py     # Provedores de IA
│   ├── validadores.py      # Validação CNPJ/CPF
│   ├── cache_manager.py    # Sistema de cache
│   ├── data_export.py      # Exportação CSV/Excel
│   ├── config_validator.py # Validação de config
│   └── logging_config.py   # Configuração de logging
├── tests/                  # Testes
├── examples/               # Exemplos de uso
├── docs/                   # Documentação
└── data/                   # Dados gerados
```

## Instalação

### Requisitos

- Python 3.8+
- Node.js 18+ (para frontend)
- Tesseract OCR (para OCR)
- Poppler (para PDF)

### Passos

```bash
# Backend
pip install -r requirements.txt
python -m spacy download pt_core_news_lg
python main.py --install

# Frontend
cd frontend
npm install

# Configuração
cp .env.example .env
cp config.example.json config.json
# Edite .env com suas chaves de API
```

## Execução

### Desenvolvimento

```bash
# Backend + Frontend (Windows)
start_web.bat

# Apenas Backend
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Apenas Frontend
cd frontend && npm run dev

# GUI Desktop
python main.py
python main.py --minimal  # Versão minimalista
```

### Produção

```bash
# Docker
docker-compose up -d
```

## API Endpoints

### Health Check
- `GET /` - Status da API
- `GET /health` - Health check completo

### Dashboard
- `GET /api/dashboard/` - Resumo do dashboard

### Documentos
- `GET /api/documentos/` - Listar documentos
- `GET /api/documentos/{id}` - Detalhes do documento
- `POST /api/documentos/upload` - Upload de documento
- `DELETE /api/documentos/{id}` - Remover documento
- `DELETE /api/documentos/` - Limpar todos

### Chat
- `GET /api/chat/historico` - Histórico de conversas
- `POST /api/chat/` - Enviar mensagem

### Navegador
- `GET /api/navegador/status` - Status do navegador
- `POST /api/navegador/navegar` - Navegar para URL
- `GET /api/navegador/screenshot` - Captura de tela

### Relatórios
- `GET /api/relatorios/` - Listar relatórios
- `POST /api/relatorios/gerar` - Gerar relatório
- `GET /api/relatorios/exportar/{formato}` - Exportar dados

## Sistema Multi-Agente

O sistema possui 10 agentes especialistas orquestrados pelo Supervisor:

| Agente | Função |
|--------|--------|
| Navegador | Navega em URLs e extrai conteúdo |
| GrafoSocietario | Gera visualização de relacionamentos |
| GazetteAuditor | Processa Diários Oficiais |
| PayrollAuditor | Analisa folhas de pagamento |
| GeospatialAuditor | Mapeia endereços |
| InvoiceParser | Extrai dados de notas fiscais |
| ReporterAuditor | Gera laudos PDF |
| SanctionAuditor | Verifica sanções |
| BankingAuditor | Analisa extratos bancários |
| TimelineAuditor | Cria linha do tempo |

## Provedores de IA

| Provedor | API Key | Modelos |
|----------|---------|---------|
| NVIDIA | NVIDIA_API_KEY | DeepSeek V4 Flash, DeepSeek R1 |
| HuggingFace | HF_TOKEN | Llama 3.1 70B, DeepSeek R1 |
| Local | - | spaCy pt_core_news_lg |

## Testes

```bash
# Todos os testes
python -m pytest tests/ -v

# Com coverage
python -m pytest tests/ --cov=core --cov=utils --cov=api --cov-report=html

# Testes específicos
python -m pytest tests/test_api_routes.py -v