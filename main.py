"""
IA Analisadora - "O Cérebro da Transparência"
==============================================
Sistema completo para análise de documentos públicos com:
- OCR + NLP + Embeddings
- Correlação de entidades (pessoas, empresas, contratos)
- Detecção de anomalias (superfaturamento, nepotismo, cartel, etc.)
- Graph Database como base de conhecimento
- Dashboards e relatórios

Fluxo: Entrada de Dados → Leitor Universal → Correlacionador →
       Detector de Anomalias → Base de Conhecimento → Reports
"""

import os
import sys
import argparse


def main():
    """Ponto de entrada principal da aplicação."""
    parser = argparse.ArgumentParser(
        description="IA Analisadora - Análise de Documentos Públicos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py                    # Inicia interface gráfica
  python main.py --gui              # Inicia interface gráfica
  python main.py --cli arquivo.pdf  # Processa arquivo via CLI
  python main.py --url https://...  # Processa URL via CLI
        """
    )

    parser.add_argument(
        "--gui", "-g",
        action="store_true",
        help="Inicia a interface gráfica (padrão - versão completa)"
    )

    parser.add_argument(
        "--minimal", "-m",
        action="store_true",
        help="Inicia a interface minimalista estilo ChatGPT/Linear"
    )

    parser.add_argument(
        "--cli", "-c",
        type=str,
        nargs="?",
        const="",
        help="Processa arquivo(s) via CLI (modo texto)"
    )

    parser.add_argument(
        "--url", "-u",
        type=str,
        help="Processa URL via CLI"
    )

    parser.add_argument(
        "--pasta", "-p",
        type=str,
        help="Processa todos documentos de uma pasta"
    )

    parser.add_argument(
        "--report", "-r",
        action="store_true",
        help="Gera relatório HTML após processamento"
    )

    parser.add_argument(
        "--install",
        action="store_true",
        help="Instala dependências do projeto"
    )

    args = parser.parse_args()

    if args.install:
        install_dependencies()
        return

    # Modo CLI
    if args.cli is not None or args.url or args.pasta:
        modo_cli(args)
        return

    # Modo GUI
    try:
        if args.minimal:
            from gui.app_minimalista import AuditorIaApp
            print("🧠 Iniciando Auditor IA - Interface Minimalista...")
            app = AuditorIaApp()
            app.iniciar()
        else:
            from gui.app import IAAnalisadoraApp
            print("🧠 Iniciando IA Analisadora - Cérebro da Transparência...")
            app = IAAnalisadoraApp()
            app.iniciar()
    except ImportError as e:
        print(f"[ERRO] Dependências da GUI não encontradas: {e}")
        print("\n🔧 Execute: python main.py --install")
        print("📦 Ou: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Falha ao iniciar GUI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def modo_cli(args):
    """Modo de linha de comando para processamento."""
    from core.leitor_universal import LeitorUniversal
    from core.correlacionador import Correlacionador
    from core.detector_anomalias import DetectorAnomalias
    from core.base_conhecimento import BaseConhecimento
    from core.camada_reports import CamadaReports
    from core.entrada_dados import ColetorDados

    leitor = LeitorUniversal()
    correlacionador = Correlacionador()
    detector = DetectorAnomalias()
    base = BaseConhecimento()
    reports = CamadaReports()

    documentos = []

    # Processa arquivo(s)
    if args.cli is not None:
        if args.cli:
            caminhos = [args.cli]
        else:
            print("📂 Digite o(s) caminho(s) do(s) arquivo(s) (separados por espaço):")
            caminhos = input().strip().split()
        
        for caminho in caminhos:
            if os.path.exists(caminho):
                print(f"📄 Processando: {caminho}")
                doc = leitor.processar_documento(caminho)
                if doc:
                    documentos.append(doc)
                    print(f"   ✅ {len(doc.entidades)} entidades extraídas")
                    if doc.resumo:
                        print(f"   📝 Resumo: {doc.resumo[:200]}...")
            else:
                print(f"❌ Arquivo não encontrado: {caminho}")

    # Processa URL
    if args.url:
        print(f"🌐 Processando URL: {args.url}")
        doc = leitor.processar_url(args.url)
        if doc:
            documentos.append(doc)
            print(f"   ✅ {len(doc.entidades)} entidades extraídas")

    # Processa pasta
    if args.pasta:
        coletor = ColetorDados()
        caminhos = coletor.coletar_pasta(args.pasta)
        print(f"📁 Encontrados {len(caminhos)} arquivos em {args.pasta}")
        for caminho in caminhos:
            print(f"   📄 Processando: {os.path.basename(caminho)}")
            doc = leitor.processar_documento(caminho)
            if doc:
                documentos.append(doc)

    if not documentos:
        print("❌ Nenhum documento processado.")
        return

    # Pipeline
    print(f"\n🔄 Correlacionando {len(documentos)} documentos...")
    relacionamentos = correlacionador.processar_documentos(documentos)
    print(f"   ✅ {len(relacionamentos)} relacionamentos encontrados")

    print("🔄 Detectando anomalias...")
    alertas = detector.processar(
        documentos,
        relacionamentos,
        correlacionador.pessoas,
        correlacionador.empresas,
    )
    print(f"   ⚠️ {len(alertas)} anomalias detectadas")

    # Base de conhecimento
    print("🔄 Atualizando base de conhecimento...")
    for doc in documentos:
        base.adicionar_entidades(doc.entidades)
    base.adicionar_relacionamentos(relacionamentos)
    base.adicionar_pessoas(correlacionador.pessoas)
    base.adicionar_empresas(correlacionador.empresas)
    base.adicionar_alertas(alertas)
    base.salvar()
    print("   ✅ Base de conhecimento salva")

    # Relatório
    if args.report or True:
        print("📊 Gerando relatório...")
        dados = reports.gerar_dashboard(documentos, alertas, relacionamentos, correlacionador.pessoas, correlacionador.empresas)
        caminho_html = reports.exportar_html(dados)
        caminho_json = reports.exportar_json(dados)
        print(f"   ✅ Relatório HTML: {caminho_html}")
        print(f"   ✅ Dados JSON: {caminho_json}")

    # Resumo
    print(f"\n{'='*50}")
    print(f"📊 RESUMO DA ANÁLISE")
    print(f"{'='*50}")
    print(f"📄 Documentos processados: {len(documentos)}")
    print(f"🏷️ Entidades extraídas: {sum(len(d.entidades) for d in documentos)}")
    print(f"🔗 Relacionamentos: {len(relacionamentos)}")
    print(f"⚠️ Anomalias detectadas: {len(alertas)}")
    for a in alertas[:5]:
        print(f"   • [{a.severidade.upper()}] {a.titulo}")
    if len(alertas) > 5:
        print(f"   ... e mais {len(alertas) - 5} alerta(s)")
    print(f"✅ Análise concluída!")


def install_dependencies():
    """Instala todas as dependências do projeto."""
    import subprocess
    import sys

    print("🔧 Instalando dependências...\n")
    
    # Lista de pacotes
    pacotes = [
        ("spacy", "pt_core_news_lg"),
        ("sentence-transformers", None),
    ]

    # Instala do requirements.txt
    print("📦 Instalando pacotes do requirements.txt...")
    result = subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    )
    
    if result == 0:
        print("✅ Pacotes base instalados!\n")

    # Instala modelo spaCy
    print("📦 Baixando modelo spaCy português...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "spacy", "download", "pt_core_news_lg"]
        )
        print("✅ Modelo spaCy instalado!")
    except subprocess.CalledProcessError:
        print("⚠️ Não foi possível baixar modelo spaCy. Tente manualmente:")
        print("   python -m spacy download pt_core_news_lg")

    print("\n🎯 Instalação concluída!")
    print("\n▶️ Para iniciar: python main.py")


if __name__ == "__main__":
    main()