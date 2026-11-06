# Sistema Multi-Agente

## Visão Geral

O sistema multi-agente da IA Analisadora é uma arquitetura de inteligência artificial distribuída que permite que diferentes especialistas colaborem para resolver tarefas complexas de auditoria e análise de documentos públicos.

## Arquitetura

### Componentes Principais

#### 1. BaseAgente (`base.py`)
Classe abstrata que define a interface comum para todos os agentes especialistas.

```python
class BaseAgente:
    def __init__(self, nome: str, descricao: str)
    def processar(self, tarefa: str) -> str
```

**Responsabilidades:**
- Definir contrato padrão para todos os agentes
- Garantir consistência na implementação de especialistas

#### 2. SupervisorRouter (`supervisor.py`)
Orquestrador que gerencia a comunicação entre o usuário e os agentes especialistas.

**Funcionalidades:**
- Roteamento dinâmico de tarefas
- Delegação automática para especialistas apropriados
- Loop de iteração com limite máximo (3 iterações)
- Extração de pensamentos (reasoning) do modelo
- Tratamento de erros e falhas de comunicação

**Fluxo de Trabalho:**
1. Recebe pergunta do usuário
2. Consulta IA para determinar se precisa delegar
3. Se sim, extrai JSON com agente e tarefa
4. Executa tarefa no especialista
5. Adiciona resultado ao contexto
6. Repete até resposta final ou limite de iterações

#### 3. Agentes Especialistas (`especialistas.py`)
Agentes especializados em tarefas específicas de auditoria.

##### NavegadorAgente
- **Função:** Navega em URLs e extrai dados de portais de transparência
- **Capacidades:**
  - Acesso a URLs específicas
  - Navegação completa de menus
  - Extração de dados estruturados
  - Integração com ExtratorPortalTransparencia

##### AnalistaAgente
- **Função:** Analisa documentos e extrai insights
- **Capacidades:**
  - Análise de documentos processados
  - Identificação de padrões
  - Sumarização de conteúdo
  - Geração de insights

##### CorrelacionadorAgente
- **Função:** Correlaciona entidades e identifica relacionamentos
- **Capacidades:**
  - Análise de grafo de entidades
  - Identificação de conexões ocultas
  - Mapeamento de redes de relacionamentos
  - Detecção de padrões de conexão

##### TimelineAuditor
- **Função:** Cria linhas do tempo de investigações
- **Capacidades:**
  - Extração de eventos datados
  - Ordenação cronológica
  - Visualização temporal
  - Identificação de padrões temporais

##### LaudoGenerator
- **Função:** Gera laudos técnicos de auditoria
- **Capacidades:**
  - Compilação de evidências
  - Geração de PDF
  - Formatação profissional
  - Inclusão de gráficos e tabelas

##### GeolocalizadorAgente
- **Função:** Mapeia endereços de empresas e pessoas
- **Capacidades:**
  - Geocodificação de endereços
  - Visualização em mapa
  - Análise geográfica
  - Identificação de clusters

## Integração com IA

O sistema utiliza provedores de IA configurados em `utils/ai_providers.py`:

- **NVIDIA:** DeepSeek V4 Flash (padrão)
- **HuggingFace:** Llama 3.1 70B e outros modelos
- **Local:** spaCy (sem API)

### Formato de Comunicação

**Delegação via JSON:**
```json
{
  "agente": "NomeDoAgente",
  "tarefa": "Instrução clara para o agente"
}
```

**Pensamentos (Reasoning):**
```
<thought>
Seu pensamento e raciocínio aqui...
</thought>
```

## Uso

### Via Código

```python
from core.agentes.supervisor import SupervisorRouter
from core.agentes.especialistas import NavegadorAgente, AnalistaAgente
from utils.ai_providers import get_ai_manager

# Inicializa gerenciador de IA
ai_manager = get_ai_manager()

# Cria especialistas
navegador = NavegadorAgente(navegador_automatizado)
analista = AnalistaAgente(correlacionador)

# Cria supervisor
supervisor = SupervisorRouter(ai_manager, [navegador, analista])

# Processa pergunta
resposta = supervisor.processar(
    "Analise o portal de transparência de https://transparencia.gov.br",
    contexto_historico=""
)
```

### Via GUI Minimalista

A interface minimalista (`gui/app_minimalista.py`) integra o sistema multi-agente automaticamente, permitindo conversas naturais com o supervisor.

## Configuração

### Limite de Iterações

O limite padrão é 3 iterações, configurável em `SupervisorRouter.max_iteracoes`.

### Callbacks

O supervisor suporta callbacks para atualização da UI:

```python
def callback_ui(mensagem):
    print(f"[UI] {mensagem}")

def callback_pensamento(pensamento):
    print(f"[Pensamento] {pensamento}")

supervisor.processar(
    pergunta,
    contexto,
    callback_ui=callback_ui,
    callback_pensamento=callback_pensamento
)
```

## Extensão

### Criando Novo Especialista

1. Herde de `BaseAgente`:
```python
from core.agentes.base import BaseAgente

class MeuEspecialista(BaseAgente):
    def __init__(self, dependencia):
        super().__init__(
            nome="MeuEspecialista",
            descricao="Descrição do que faz"
        )
        self.dependencia = dependencia
    
    def processar(self, tarefa: str) -> str:
        # Implementação
        return f"Resultado: {tarefa}"
```

2. Adicione ao Supervisor:
```python
supervisor = SupervisorRouter(ai_manager, [
    NavegadorAgente(navegador),
    AnalistaAgente(correlacionador),
    MeuEspecialista(dependencia)
])
```

## Testes

Testes unitários disponíveis em `tests/`:
- `test_agentes_base.py` - Testa classe base
- `test_agentes_supervisor.py` - Testa orquestrador
- `test_agentes_especialistas.py` - Testa especialistas

Executar testes:
```bash
python -m pytest tests/test_agentes_*.py -v
```

## Troubleshooting

### IA Indisponível
Se receber "Erro: Provedor de IA indisponível":
- Verifique se a API key está configurada no `.env`
- Confirme que o provedor está acessível
- Teste com provedor local: `AI_PROVIDER=local`

### Delegação Infinita
Se o supervisor entrar em loop:
- Reduza `max_iteracoes`
- Verifique se o prompt do sistema está claro
- Adicione mais contexto para evitar ambiguidade

### JSON Inválido
Se o JSON de delegação falhar:
- O supervisor ignora JSON inválido automaticamente
- Verifique logs para identificar o problema
- Ajuste o prompt do sistema se necessário

## Roadmap

- [ ] Adicionar mais especialistas (Financeiro, Legal, etc.)
- [ ] Implementar cache de resultados de agentes
- [ ] Adicionar paralelização de tarefas
- [ ] Melhorar tratamento de erros
- [ ] Adicionar métricas de performance
- [ ] Implementar aprendizado de feedback

## Referências

- Pattern: Multi-Agent System (MAS)
- Orquestração: Router Pattern
- Comunicação: JSON-based delegation
