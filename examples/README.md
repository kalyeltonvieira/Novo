# Exemplos de Uso - IA Analisadora

Este diretório contém exemplos de como usar a IA Analisadora.

## Exemplos Disponíveis

### 1. exemplo_basico.py
Demonstra o uso básico do pipeline completo de análise de documentos.

**Uso:**
```bash
python examples/exemplo_basico.py documento.pdf
python examples/exemplo_basico.py contrato.txt
```

**Funcionalidades:**
- Leitura e extração de entidades
- Correlação de entidades
- Detecção de anomalias
- Atualização da base de conhecimento
- Geração de relatórios HTML e JSON

### 2. exemplo_coleta_dados.py
Demonstra como coletar dados de diferentes fontes.

**Uso:**
```bash
python examples/exemplo_coleta_dados.py arquivo.pdf pasta/documentos
```

**Funcionalidades:**
- Coleta de arquivos locais
- Coleta de pastas inteiras
- Coleta de URLs
- Coleta de APIs
- Importação de planilhas (Excel/CSV)
- Coleta de diários oficiais
- Adição de texto direto

### 3. exemplo_gui.py
Demonstra como iniciar a interface gráfica.

**Uso:**
```bash
python examples/exemplo_gui.py
```

**Funcionalidades:**
- Interface gráfica moderna com CustomTkinter
- Dashboard interativo
- Visualização de grafo de relacionamentos
- Gerenciamento de alertas
- Geração de relatórios

## Outras Formas de Uso

### Via CLI (main.py)
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

### Via GUI (main.py)
```bash
# Inicia interface gráfica (padrão)
python main.py

# Ou explicitamente
python main.py --gui
```

## Pré-requisitos

Certifique-se de ter instalado as dependências:
```bash
pip install -r requirements.txt
python -m spacy download pt_core_news_lg
```

Para OCR, instale também:
- **Tesseract OCR**: https://github.com/UB-Mannheim/tesseract/wiki
- **Poppler**: https://github.com/oschwartz10612/poppler-windows

## Dica

Para executar os exemplos, navegue até o diretório raiz do projeto:
```bash
cd d:\Novo
python examples/exemplo_basico.py seu_arquivo.pdf
```
