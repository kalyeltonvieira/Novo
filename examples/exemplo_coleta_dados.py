"""
Exemplo de Coleta de Dados - IA Analisadora
===========================================
Demonstra como coletar dados de diferentes fontes.
"""

from core.entrada_dados import ColetorDados
from core.leitor_universal import LeitorUniversal


def coletar_de_arquivo(caminho: str):
    """Coleta dados de um arquivo local."""
    print(f"📂 Coletando de arquivo: {caminho}")
    coletor = ColetorDados()
    caminho_coletado = coletor.coletar_arquivo(caminho)
    print(f"✅ Arquivo coletado: {caminho_coletado}")
    return caminho_coletado


def coletar_de_pasta(caminho_pasta: str):
    """Coleta todos os arquivos de uma pasta."""
    print(f"📁 Coletando de pasta: {caminho_pasta}")
    coletor = ColetorDados()
    arquivos = coletar.coletar_pasta(caminho_pasta)
    print(f"✅ {len(arquivos)} arquivos encontrados")
    for arquivo in arquivos[:5]:
        print(f"   - {arquivo}")
    if len(arquivos) > 5:
        print(f"   ... e mais {len(arquivos) - 5} arquivos")
    return arquivos


def coletar_de_url(url: str):
    """Coleta dados de uma URL."""
    print(f"🌐 Coletando de URL: {url}")
    coletor = ColetorDados()
    dados = coletor.coletar_url(url)
    if dados:
        print(f"✅ Dados coletados (status: {dados['status_code']})")
        print(f"   Content-Type: {dados['content_type']}")
        print(f"   Tamanho: {len(dados['conteudo'])} caracteres")
    else:
        print("❌ Falha ao coletar dados da URL")
    return dados


def coletar_de_api(url: str, params: dict = None):
    """Coleta dados de uma API."""
    print(f"🔌 Coletando de API: {url}")
    coletor = ColetorDados()
    dados = coletor.coletar_api(url, params=params)
    if dados:
        print(f"✅ Dados coletados da API")
        if isinstance(dados, list):
            print(f"   - {len(dados)} itens retornados")
        elif isinstance(dados, dict):
            print(f"   - Dicionário com {len(dados)} chaves")
    else:
        print("❌ Falha ao coletar dados da API")
    return dados


def coletar_texto_direto(texto: str, fonte: str = "manual"):
    """Adiciona texto diretamente."""
    print(f"📝 Adicionando texto direto")
    coletor = ColetorDados()
    dados = coletor.coletar_texto(texto, fonte)
    print(f"✅ Texto adicionado ({len(texto)} caracteres)")
    return dados


def coletar_de_planilha(caminho: str):
    """Importa dados de planilha Excel ou CSV."""
    print(f"📊 Importando planilha: {caminho}")
    coletor = ColetorDados()
    dados = coletor.importar_planilha(caminho)
    if dados:
        print(f"✅ Planilha importada")
        print(f"   - {len(dados)} linhas")
        if dados:
            print(f"   - Colunas: {list(dados[0].keys())}")
    else:
        print("❌ Falha ao importar planilha")
    return dados


def coletar_diario_oficial(url: str):
    """Coleta PDFs de diário oficial."""
    print(f"📰 Coletando diário oficial: {url}")
    coletor = ColetorDados()
    pdfs = coletor.coletar_diario_oficial(url)
    print(f"✅ {len(pdfs)} PDFs encontrados")
    for pdf in pdfs[:5]:
        print(f"   - {pdf}")
    if len(pdfs) > 5:
        print(f"   ... e mais {len(pdfs) - 5} PDFs")
    return pdfs


def processar_arquivos_coletados(arquivos: list):
    """Processa arquivos coletados com o Leitor Universal."""
    print(f"\n🔄 Processando {len(arquivos)} arquivos...")
    leitor = LeitorUniversal()
    documentos = []
    
    for arquivo in arquivos:
        print(f"   📄 {arquivo}")
        doc = leitor.processar_documento(arquivo)
        if doc:
            documentos.append(doc)
            print(f"      ✅ {len(doc.entidades)} entidades")
        else:
            print(f"      ❌ Falha ao processar")
    
    print(f"\n✅ {len(documentos)} documentos processados com sucesso")
    return documentos


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Exemplo de Coleta de Dados - IA Analisadora")
    print("=" * 60)
    
    # Exemplo 1: Coletar de arquivo
    if len(sys.argv) > 1:
        arquivo = sys.argv[1]
        coletar_de_arquivo(arquivo)
    
    # Exemplo 2: Coletar de pasta
    if len(sys.argv) > 2:
        pasta = sys.argv[2]
        arquivos = coletar_de_pasta(pasta)
        if arquivos:
            processar_arquivos_coletados(arquivos)
    
    # Exemplo 3: Coletar texto direto
    texto_exemplo = """
    Contrato Nº 123/2024
    Contratante: Prefeitura Municipal de São Paulo
    Contratada: Empresa XYZ LTDA, CNPJ 11.222.333/0001-81
    Valor: R$ 150.000,00
    Objeto: Serviços de limpeza
    """
    coletar_texto_direto(texto_exemplo, "exemplo_manual")
    
    print("\n" + "=" * 60)
    print("Exemplos concluídos!")
    print("=" * 60)
