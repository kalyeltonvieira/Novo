# Contribuindo para IA Analisadora

Obrigado por se interessar em contribuir com a IA Analisadora! Este documento guia você através do processo de contribuição.

## Código de Conduta

- Seja respeitoso e inclusivo
- Foque no que é melhor para a comunidade
- Aceite construtivamente críticas e feedback
- Mostre empatia com outros contribuidores

## Como Contribuir

### Reportando Bugs

Antes de reportar um bug, verifique se já não foi reportado nos [issues](https://github.com/seu-repositorio/ia-analisadora/issues).

Ao reportar um bug, inclua:
- Título descritivo
- Descrição detalhada do problema
- Passos para reproduzir
- Comportamento esperado vs. comportamento atual
- Ambiente (SO, versão Python, etc.)
- Logs relevantes

### Sugerindo Funcionalidades

1. Verifique se a funcionalidade já foi solicitada
2. Abra uma issue com a tag `enhancement`
3. Descreva claramente a funcionalidade proposta
4. Explique o caso de uso e benefícios

### Pull Requests

#### Processo

1. **Fork** o repositório
2. **Clone** seu fork: `git clone https://github.com/seu-usuario/ia-analisadora.git`
3. **Crie uma branch**: `git checkout -b feature/nova-funcionalidade`
4. **Faça suas alterações**
5. **Commit** suas alterações: `git commit -m 'Add nova funcionalidade'`
6. **Push** para a branch: `git push origin feature/nova-funcionalidade`
7. Abra um **Pull Request**

#### Convenções de Commit

Use mensagens de commit claras e descritivas:

```
feat: adicionar nova funcionalidade de exportação CSV
fix: corrigir bug na extração de CNPJ
docs: atualizar README com instruções de instalação
test: adicionar testes para o módulo de agentes
refactor: otimizar leitura de PDFs
```

#### Padrões de Código

- **Python:** Siga PEP 8
- **Type Hints:** Use type hints em funções e classes
- **Docstrings:** Use docstrings estilo Google ou NumPy
- **Nomes:** Use nomes descritivos em inglês para código, português para comentários

#### Formatação

O projeto usa:
- **Black** para formatação de código
- **isort** para ordenação de imports
- **flake8** para linting

Execute antes de commitar:
```bash
black .
isort .
flake8 .
```

### Testes

#### Executando Testes

```bash
# Executar todos os testes
python -m pytest tests/ -v

# Executar com coverage
python -m pytest tests/ --cov=core --cov=utils --cov-report=html

# Executar testes específicos
python -m pytest tests/test_leitor.py -v
```

#### Escrevendo Testes

- Testes unitários devem ser independentes
- Use fixtures do pytest para setup
- Mock dependências externas
- Mantenha testes rápidos

### Documentação

#### Código

Adicione docstrings a todas as funções e classes públicas:

```python
def processar_documento(caminho: str) -> Documento:
    """Processa um documento e extrai entidades.
    
    Args:
        caminho: Caminho do arquivo a ser processado.
        
    Returns:
        Documento processado com entidades extraídas.
        
    Raises:
        FileNotFoundError: Se o arquivo não existir.
    """
```

#### README

Atualize o README.md se sua alteração afeta:
- Instalação
- Configuração
- Uso
- API

## Estrutura do Projeto

```
.
├── core/              # Lógica principal
├── gui/               # Interface gráfica
├── utils/             # Utilitários
├── tests/             # Testes
├── examples/          # Exemplos de uso
└── docs/              # Documentação adicional
```

## Desenvolvimento

### Ambiente de Desenvolvimento

```bash
# Clonar repositório
git clone https://github.com/seu-repositorio/ia-analisadora.git
cd ia-analisadora

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Instalar modelo spaCy
python -m spacy download pt_core_news_lg

# Instalar dependências de desenvolvimento
pip install black isort flake8 pytest pytest-cov mypy
```

### Configuração

```bash
# Copiar arquivo de exemplo
cp .env.example .env
cp config.example.json config.json

# Editar .env com suas chaves de API
```

### Branches

- `main`: Branch de produção
- `develop`: Branch de desenvolvimento
- `feature/*`: Branches para novas funcionalidades
- `fix/*`: Branches para correções de bugs
- `docs/*`: Branches para documentação

### Review de Código

Todos os PRs passam por review. Ao revisar:
- Verifique se o código segue os padrões
- Teste as alterações se possível
- Verifique se há testes adequados
- Confirme que a documentação foi atualizada

## Release Process

1. Atualize `CHANGELOG.md`
2. Atualize versão em `__init__.py` se necessário
3. Crie tag git: `git tag v1.0.0`
4. Push da tag: `git push origin v1.0.0`
5. Crie release no GitHub

## Comunidade

- **Issues:** Use para bugs e funcionalidades
- **Discussions:** Use para perguntas e discussões
- **Pull Requests:** Use para contribuições de código

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a mesma licença do projeto.

## Suporte

Para dúvidas:
- Abra uma issue com a tag `question`
- Verifique a documentação em `docs/`
- Consulte os exemplos em `examples/`

## Agradecimentos

Obrigado a todos os contribuidores que tornam este projeto melhor!
